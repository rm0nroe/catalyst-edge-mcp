"""Minimal immutable replay, labeling, and partition contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from catalyst_edge_mcp.compat import UTC

ALLOWED_PROOFS = {
    "sec_acceptance",
    "prospective_collector_receipt",
    "contemporaneous_archive_capture",
    "provider_point_in_time_record",
}
REQUIRED_RIGHTS = (
    "training_allowed",
    "artifact_distribution_allowed",
    "aggregate_reporting_allowed",
    "post_termination_artifact_allowed",
)
MODEL_EVIDENCE_FAMILIES = {
    "filings_news",
    "insider_trading",
    "options_flow",
    "social",
    "technical",
}
MODEL_DIRECTIONS = {"bearish", "neutral", "bullish"}
PROVENANCE_VALUES = {"synthetic_only", "rights_cleared_market"}


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def canonical_jsonl(records: list[dict[str, Any]]) -> bytes:
    identities = [(record["record_type"], record["record_id"]) for record in records]
    if len(set(identities)) != len(identities):
        raise ValueError("canonical records contain duplicate identities")
    ordered = sorted(records, key=lambda record: (record["record_type"], record["record_id"]))
    return b"".join(canonical_json(record) for record in ordered)


def stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{hashlib.sha256(chr(31).join(parts).encode()).hexdigest()}"


def observation_ids(observation: dict[str, Any]) -> tuple[str, str]:
    key = stable_id(
        "cek",
        str(observation["source_id"]),
        str(observation["security_id"]),
        str(observation["stable_record_id"]),
    )
    return key, stable_id("ceo", key, str(observation["version_sha256"]))


def normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if set(spec) != {
        "schema_version",
        "provenance",
        "code_sha256",
        "config_sha256",
        "rights",
        "calendar",
        "observations",
        "cases",
        "prices",
        "actions",
        "terminal_outcomes",
    }:
        raise ValueError("replay specification has an invalid top-level schema")
    if spec["schema_version"] != 1:
        raise ValueError("replay specification schema_version is unsupported")
    if spec["provenance"] not in PROVENANCE_VALUES:
        raise ValueError("replay specification provenance is invalid")
    normalized = dict(spec)
    normalized["rights"] = sorted(spec["rights"], key=lambda row: row["source_id"])
    normalized["calendar"] = sorted(spec["calendar"])
    normalized["observations"] = sorted(
        spec["observations"],
        key=lambda row: (row["source_id"], row["stable_record_id"], row["version_sha256"]),
    )
    normalized["cases"] = sorted(
        ({**row, "observation_refs": sorted(row["observation_refs"])} for row in spec["cases"]),
        key=lambda row: (row["evaluation_at"], row["security_id"], row["event_group_id"]),
    )
    normalized["prices"] = sorted(
        spec["prices"], key=lambda row: (row["security_id"], row["session_open_at"])
    )
    normalized["actions"] = sorted(
        spec["actions"],
        key=lambda row: (
            row["source_id"],
            row["security_id"],
            row["stable_record_id"],
            row["version_sha256"],
        ),
    )
    normalized["terminal_outcomes"] = sorted(
        spec["terminal_outcomes"],
        key=lambda row: (
            row["source_id"],
            row["security_id"],
            row["stable_record_id"],
            row["version_sha256"],
            row["effective_at"],
        ),
    )
    return normalized


def dataset_version(spec: dict[str, Any]) -> str:
    return f"ced_{hashlib.sha256(canonical_json(normalize_spec(spec))).hexdigest()}"


def build_dataset(spec: dict[str, Any]) -> tuple[str, bytes, dict[str, Any]]:
    normalized = normalize_spec(spec)
    _sha256(normalized["code_sha256"], "code_sha256")
    _sha256(normalized["config_sha256"], "config_sha256")
    rights = {row["source_id"]: row for row in normalized["rights"]}
    if len(rights) != len(normalized["rights"]):
        raise ValueError("rights manifests contain duplicate source IDs")
    _validate_rights(rights)
    sessions = [_timestamp(value) for value in normalized["calendar"]]
    if sessions != sorted(set(sessions)):
        raise ValueError("calendar sessions must be unique and ordered")

    observations: dict[str, dict[str, Any]] = {}
    observation_records: list[dict[str, Any]] = []
    records = _rights_records(normalized["rights"])
    for row in normalized["observations"]:
        _require_source_rights(rights, row["source_id"])
        _sha256(row["version_sha256"], "observation version_sha256")
        proof_type = row["availability_proof_type"]
        if proof_type not in ALLOWED_PROOFS:
            raise ValueError(f"observation {row['stable_record_id']} has an invalid proof type")
        accepted = _timestamp(row["accepted_or_published_at"])
        available = _timestamp(row["historically_available_at"])
        reconstructed = _timestamp(row["reconstructed_at"])
        eligibility = max(accepted, available)
        evidence_snapshot = _evidence_snapshot(row)
        key, identifier = observation_ids(row)
        reference = f"{row['source_id']}:{row['stable_record_id']}:{row['version_sha256']}"
        if reference in observations:
            raise ValueError(f"duplicate observation reference {reference}")
        observations[reference] = {
            **row,
            "observation_key": key,
            "observation_id": identifier,
            "eligibility_at": _timestamp_text(eligibility),
            "evidence_snapshot": evidence_snapshot,
        }
        observation_records.append(
            {
                "record_type": "observation",
                "record_id": identifier,
                "observation_key": key,
                "source_id": row["source_id"],
                "security_id": row["security_id"],
                "stable_record_id": row["stable_record_id"],
                "version_sha256": row["version_sha256"],
                "event_group_id": row["event_group_id"],
                "accepted_or_published_at": _timestamp_text(accepted),
                "historically_available_at": _timestamp_text(available),
                "eligibility_at": _timestamp_text(eligibility),
                "reconstructed_at": _timestamp_text(reconstructed),
                "availability_proof_type": proof_type,
                "availability_proof_reference": row["availability_proof_reference"],
                "evidence_snapshot": evidence_snapshot,
                "correction_of_observation_id": None,
            }
        )
    records.extend(_add_correction_lineage(observation_records))

    prices, price_records = _price_index(normalized["prices"], rights)
    terminals = _terminal_index(normalized["terminal_outcomes"], rights)
    records.extend(price_records)
    actions = _action_records(normalized["actions"], rights)
    records.extend(actions)
    records.extend(_terminal_records(normalized["terminal_outcomes"]))

    cases = normalized["cases"]
    _validate_group_isolation(cases)
    exclusions: list[dict[str, Any]] = []
    labels = 0
    for case in cases:
        try:
            case_observations = [observations[reference] for reference in case["observation_refs"]]
        except KeyError as exc:
            raise ValueError(f"evaluation references unknown observation {exc.args[0]}") from exc
        if not case_observations:
            raise ValueError(f"evaluation {case['security_id']} has no observations")
        if any(row["security_id"] != case["security_id"] for row in case_observations):
            raise ValueError(f"evaluation {case['security_id']} crosses security identities")
        if any(row["event_group_id"] != case["event_group_id"] for row in case_observations):
            raise ValueError(f"evaluation {case['security_id']} crosses event groups")
        case_observations = _latest_observation_versions(case_observations)
        evaluation_at = _timestamp(case["evaluation_at"])
        eligibility = max(_timestamp(row["eligibility_at"]) for row in case_observations)
        if eligibility > evaluation_at or any(
            _timestamp(row["evidence_snapshot"]["timestamp"]) > evaluation_at
            for row in case_observations
        ):
            raise ValueError(f"evaluation {case['security_id']} contains future evidence")
        entry_index = _entry_session_index(sessions, eligibility)
        fold = _fold(evaluation_at)
        reason = _partition_exclusion(sessions, entry_index, fold, horizon=5)
        evaluation_id = stable_id(
            "cee",
            dataset_version(normalized),
            case["security_id"],
            _timestamp_text(evaluation_at),
            "trained_softmax",
        )
        records.append(
            {
                "record_type": "evaluation",
                "record_id": evaluation_id,
                "security_id": case["security_id"],
                "event_group_id": case["event_group_id"],
                "evaluation_at": _timestamp_text(evaluation_at),
                "eligibility_at": _timestamp_text(eligibility),
                "entry_session_open_at": _timestamp_text(sessions[entry_index]),
                "fold": fold,
                "case_type": case.get("case_type", "catalyst"),
                "observation_ids": sorted(row["observation_id"] for row in case_observations),
            }
        )
        if reason:
            exclusion_id = stable_id("cex", evaluation_id, reason)
            exclusion = {
                "record_type": "exclusion",
                "record_id": exclusion_id,
                "evaluation_id": evaluation_id,
                "reason": reason,
            }
            exclusions.append(exclusion)
            records.append(exclusion)
            continue
        label = _label(case, evaluation_id, sessions, entry_index, prices, terminals)
        records.append(label)
        labels += 1

    version = dataset_version(normalized)
    records = [{**record, "provenance": normalized["provenance"]} for record in records]
    payload = canonical_jsonl(records)
    manifest = {
        "schema_version": 1,
        "provenance": normalized["provenance"],
        "dataset_version": version,
        "canonical_sha256": hashlib.sha256(payload).hexdigest(),
        "records": len(records),
        "labels": labels,
        "exclusions": len(exclusions),
        "code_sha256": normalized["code_sha256"],
        "config_sha256": normalized["config_sha256"],
        "rights_sha256": hashlib.sha256(canonical_json(normalized["rights"])).hexdigest(),
    }
    return version, payload, manifest


def _evidence_snapshot(row: dict[str, Any]) -> dict[str, str]:
    snapshot = row.get("evidence_snapshot")
    required = {
        "family",
        "direction",
        "strength",
        "confidence",
        "source_quality",
        "timestamp",
    }
    if not isinstance(snapshot, dict) or set(snapshot) != required:
        raise ValueError(f"observation {row['stable_record_id']} has an invalid evidence snapshot")
    if snapshot["family"] not in MODEL_EVIDENCE_FAMILIES:
        raise ValueError(f"observation {row['stable_record_id']} has an invalid evidence family")
    if snapshot["direction"] not in MODEL_DIRECTIONS:
        raise ValueError(f"observation {row['stable_record_id']} has an invalid direction")
    return {
        "family": snapshot["family"],
        "direction": snapshot["direction"],
        "strength": _bounded_decimal_text(snapshot["strength"], "strength"),
        "confidence": _bounded_decimal_text(snapshot["confidence"], "confidence"),
        "source_quality": _bounded_decimal_text(snapshot["source_quality"], "source_quality"),
        "timestamp": _timestamp_text(_timestamp(snapshot["timestamp"])),
    }


def _bounded_decimal_text(value: object, name: str) -> str:
    parsed = _decimal(value, 10)
    if not Decimal(0) <= parsed <= Decimal(1):
        raise ValueError(f"evidence {name} must be between zero and one")
    return _decimal_text(parsed, 10)


def _add_correction_lineage(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["observation_key"], []).append(record)
    output: list[dict[str, Any]] = []
    for values in grouped.values():
        ordered = sorted(values, key=lambda row: (row["eligibility_at"], row["record_id"]))
        if len({row["eligibility_at"] for row in ordered}) != len(ordered):
            raise ValueError("observation corrections require distinct eligibility timestamps")
        previous = None
        for record in ordered:
            record["correction_of_observation_id"] = previous
            output.append(record)
            previous = record["record_id"]
    return output


def _latest_observation_versions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        current = latest.get(row["observation_key"])
        if current is None or (row["eligibility_at"], row["observation_id"]) > (
            current["eligibility_at"],
            current["observation_id"],
        ):
            latest[row["observation_key"]] = row
    return sorted(latest.values(), key=lambda row: row["observation_id"])


def _validate_rights(rights: dict[str, dict[str, Any]]) -> None:
    for source_id, row in rights.items():
        if any(row.get(field) is not True for field in REQUIRED_RIGHTS):
            raise ValueError(f"source {source_id} lacks required model/replay rights")
        _sha256(row.get("rights_text_sha256"), f"source {source_id} rights_text_sha256")


def _rights_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_type": "rights",
            "record_id": stable_id(
                "cer", row["source_id"], row["agreement_id"], row["rights_text_sha256"]
            ),
            **row,
        }
        for row in rows
    ]


def _require_source_rights(rights: dict[str, dict[str, Any]], source_id: str) -> None:
    if source_id not in rights:
        raise ValueError(f"source {source_id} has no rights manifest")


def _price_index(
    rows: list[dict[str, Any]], rights: dict[str, dict[str, Any]]
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    records = []
    for row in rows:
        _require_source_rights(rights, row["source_id"])
        _sha256(row["version_sha256"], "price version_sha256")
        key = (row["security_id"], _timestamp_text(_timestamp(row["session_open_at"])))
        if key in output:
            raise ValueError(f"duplicate price point {key}")
        entry = _decimal(row["open_total_return_factor"], 10)
        close = _decimal(row["close_total_return_factor"], 10)
        if entry <= 0 or close <= 0:
            raise ValueError(f"price factors must be positive for {key}")
        output[key] = {**row, "open": entry, "close": close}
        records.append(
            {
                "record_type": "price",
                "record_id": stable_id(
                    "cep",
                    row["source_id"],
                    row["security_id"],
                    key[1],
                    row["version_sha256"],
                ),
                "source_id": row["source_id"],
                "security_id": row["security_id"],
                "stable_record_id": row["stable_record_id"],
                "version_sha256": row["version_sha256"],
                "session_open_at": key[1],
                "open_total_return_factor": _decimal_text(entry, 10),
                "close_total_return_factor": _decimal_text(close, 10),
            }
        )
    return output, records


def _terminal_index(
    rows: list[dict[str, Any]], rights: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        _require_source_rights(rights, row["source_id"])
        _sha256(row["version_sha256"], "terminal version_sha256")
        value = _decimal(row["total_return_factor"], 10)
        if value < 0:
            raise ValueError("terminal total-return factor cannot be negative")
        output.setdefault(row["security_id"], []).append(
            {**row, "effective": _timestamp(row["effective_at"]), "factor": value}
        )
    for values in output.values():
        values.sort(key=lambda row: row["effective"])
    return output


def _action_records(
    rows: list[dict[str, Any]], rights: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    records = []
    for row in rows:
        _require_source_rights(rights, row["source_id"])
        _sha256(row["version_sha256"], "action version_sha256")
        identifier = stable_id(
            "cea",
            row["source_id"],
            row["security_id"],
            row["stable_record_id"],
            row["version_sha256"],
        )
        records.append(
            {
                "record_type": "action",
                "record_id": identifier,
                **row,
            }
        )
    return records


def _terminal_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_type": "terminal_outcome",
            "record_id": stable_id(
                "cet",
                row["source_id"],
                row["security_id"],
                row["stable_record_id"],
                row["version_sha256"],
            ),
            **row,
        }
        for row in rows
    ]


def _validate_group_isolation(cases: list[dict[str, Any]]) -> None:
    folds: dict[str, set[str]] = {}
    for case in cases:
        folds.setdefault(case["event_group_id"], set()).add(
            _fold(_timestamp(case["evaluation_at"]))
        )
    crossing = sorted(group for group, values in folds.items() if len(values) > 1)
    if crossing:
        raise ValueError(f"event groups cross folds: {', '.join(crossing)}")


def _partition_exclusion(
    sessions: list[datetime], entry_index: int, fold: str, *, horizon: int
) -> str | None:
    exit_index = entry_index + horizon - 1
    if exit_index >= len(sessions):
        return "insufficient_forward_sessions"
    if _fold(sessions[exit_index]) != fold:
        return "label_window_crosses_fold"
    if fold in {"validation", "untouched_test"}:
        fold_sessions = [index for index, session in enumerate(sessions) if _fold(session) == fold]
        if entry_index in fold_sessions[:5]:
            return "fold_embargo"
    return None


def _label(
    case: dict[str, Any],
    evaluation_id: str,
    sessions: list[datetime],
    entry_index: int,
    prices: dict[tuple[str, str], dict[str, Any]],
    terminals: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    exit_index = entry_index + 4
    entry_session = _timestamp_text(sessions[entry_index])
    exit_session = _timestamp_text(sessions[exit_index])
    stock_entry = prices.get((case["security_id"], entry_session))
    spy_entry = prices.get(("SPY", entry_session))
    spy_exit = prices.get(("SPY", exit_session))
    if not stock_entry or not spy_entry or not spy_exit:
        raise ValueError(f"evaluation {evaluation_id} lacks stock/SPY price factors")
    stock_exit = prices.get((case["security_id"], exit_session))
    terminal = next(
        (
            row
            for row in terminals.get(case["security_id"], [])
            if sessions[entry_index] <= row["effective"] <= sessions[exit_index] + timedelta(days=1)
        ),
        None,
    )
    if terminal:
        stock_exit_factor = terminal["factor"]
        terminal_status = terminal["status"]
    elif stock_exit:
        stock_exit_factor = stock_exit["close"]
        terminal_status = None
    else:
        raise ValueError(f"evaluation {evaluation_id} lacks exit price or terminal outcome")
    stock_return = _return(stock_entry["open"], stock_exit_factor)
    spy_return = _return(spy_entry["open"], spy_exit["close"])
    relative = _decimal(stock_return - spy_return, 10)
    label_class = (
        "bearish"
        if relative <= Decimal("-0.02")
        else "bullish"
        if relative >= Decimal("0.02")
        else "neutral"
    )
    label_id = stable_id("cel", evaluation_id, "5", "gross_v1")
    return {
        "record_type": "label",
        "record_id": label_id,
        "evaluation_id": evaluation_id,
        "horizon_sessions": 5,
        "entry_session_open_at": entry_session,
        "exit_session_open_at": exit_session,
        "stock_total_return": _decimal_text(stock_return, 10),
        "spy_total_return": _decimal_text(spy_return, 10),
        "spy_relative_total_return": _decimal_text(relative, 10),
        "class": label_class,
        "terminal_status": terminal_status,
    }


def _return(entry: Decimal, exit_value: Decimal) -> Decimal:
    return _decimal(exit_value / entry - 1, 10)


def _entry_session_index(sessions: list[datetime], eligibility: datetime) -> int:
    tradable_at = eligibility + timedelta(minutes=15)
    try:
        return next(index for index, session in enumerate(sessions) if session >= tradable_at)
    except StopIteration as exc:
        raise ValueError("calendar has no entry session after eligibility") from exc


def _fold(value: datetime) -> str:
    if value < datetime(2022, 1, 1, tzinfo=UTC):
        return "training"
    if value < datetime(2024, 1, 1, tzinfo=UTC):
        return "validation"
    if value < datetime(2026, 1, 1, tzinfo=UTC):
        return "untouched_test"
    raise ValueError("evaluation timestamp is outside the frozen period")


def _timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include an offset")
    return parsed.astimezone(UTC)


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _decimal(value: object, places: int) -> Decimal:
    quantum = Decimal(1).scaleb(-places)
    return Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_EVEN)


def _decimal_text(value: Decimal, places: int) -> str:
    return format(_decimal(value, places), f".{places}f")


def _sha256(value: object, name: str) -> str:
    text = str(value)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return text
