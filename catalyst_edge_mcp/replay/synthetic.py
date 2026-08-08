"""Deterministic production-shaped synthetic replay input for engineering proof only."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from typing import Any

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.replay.contracts import MODEL_EVIDENCE_FAMILIES

SOURCE_ID = "synthetic_fixture"
PROVENANCE = "synthetic_only"
CLASSES = ("bearish", "neutral", "bullish")


def build_synthetic_spec() -> dict[str, Any]:
    """Build the frozen 2018-2025 engineering corpus through the replay spec contract."""
    sessions = _sessions(date(2018, 1, 2), date(2025, 12, 31))
    spec: dict[str, Any] = {
        "schema_version": 1,
        "provenance": PROVENANCE,
        "code_sha256": _digest("synthetic-generator-v1"),
        "config_sha256": _digest("synthetic-config-2018-2025-v1"),
        "rights": [
            {
                "source_id": SOURCE_ID,
                "agreement_id": "synthetic-fixture-no-external-data",
                "training_allowed": True,
                "artifact_distribution_allowed": True,
                "aggregate_reporting_allowed": True,
                "post_termination_artifact_allowed": True,
                "raw_deletion_required": False,
                "rights_text_sha256": _digest("synthetic-fixture-rights-v1"),
            }
        ],
        "calendar": [_text(session) for session in sessions],
        "observations": [],
        "cases": [],
        "prices": [],
        "actions": [],
        "terminal_outcomes": [],
    }
    session_index = {session.date(): index for index, session in enumerate(sessions)}
    families = tuple(sorted(MODEL_EVIDENCE_FAMILIES))
    directions = {"bearish": "bearish", "neutral": "neutral", "bullish": "bullish"}
    returns = {"bearish": "0.9500000000", "neutral": "1.0000000000", "bullish": "1.0500000000"}

    for year in range(2018, 2026):
        for class_index, label in enumerate(CLASSES):
            for sample in range(2):
                evaluation_date = date(year, 6, 4 + class_index * 7 + sample * 2)
                while evaluation_date.weekday() >= 5:
                    evaluation_date += timedelta(days=1)
                security_id = f"syn_{year}_{label}_{sample}"
                event_group_id = f"syn_event_{year}_{label}_{sample}"
                stable_record_id = f"observation_{year}_{label}_{sample}"
                observed_at = datetime.combine(evaluation_date, time(12), tzinfo=UTC)
                evaluation_at = observed_at + timedelta(hours=1)
                family = families[(year + class_index + sample) % len(families)]
                first = _observation(
                    security_id,
                    event_group_id,
                    stable_record_id,
                    family,
                    directions[label],
                    observed_at,
                    version="original",
                )
                observations = [first]
                if sample == 1 and year % 2 == 0:
                    observations.append(
                        _observation(
                            security_id,
                            event_group_id,
                            stable_record_id,
                            family,
                            directions[label],
                            observed_at + timedelta(minutes=10),
                            version="amendment",
                        )
                    )
                spec["observations"].extend(observations)
                spec["cases"].append(
                    {
                        "security_id": security_id,
                        "event_group_id": event_group_id,
                        "evaluation_at": _text(evaluation_at),
                        "case_type": "control" if sample == 1 else "catalyst",
                        "observation_refs": [_reference(row) for row in observations],
                    }
                )
                entry_index = session_index[evaluation_date]
                entry, exit_session = sessions[entry_index], sessions[entry_index + 4]
                _add_price(spec, security_id, entry, "1.0000000000", "1.0000000000")
                _add_price(spec, "SPY", entry, "1.0000000000", "1.0000000000")
                _add_price(spec, "SPY", exit_session, "1.0000000000", "1.0000000000")
                terminal = _terminal_case(year, label, sample)
                if terminal:
                    status, factor = terminal
                    spec["terminal_outcomes"].append(
                        {
                            "source_id": SOURCE_ID,
                            "security_id": security_id,
                            "stable_record_id": f"terminal_{security_id}",
                            "version_sha256": _digest(f"terminal:{security_id}:{status}"),
                            "effective_at": _text(exit_session),
                            "status": status,
                            "total_return_factor": factor,
                        }
                    )
                else:
                    _add_price(spec, security_id, exit_session, "1.0000000000", returns[label])

    spec["actions"].extend(
        [
            _action("syn_2018_neutral_0", "split_2018", "split", date(2018, 7, 2), ratio="2"),
            _action(
                "syn_2020_bullish_0", "dividend_2020", "cash_dividend", date(2020, 7, 2), amount="1"
            ),
            _action(
                "syn_2019_bearish_0", "reuse_end", "ticker_end", date(2020, 1, 2), ticker="REUSE"
            ),
            _action(
                "syn_2021_bullish_0",
                "reuse_start",
                "ticker_start",
                date(2021, 1, 4),
                ticker="REUSE",
            ),
        ]
    )
    for name, when in (
        ("cross_fold", datetime(2021, 12, 30, 13, tzinfo=UTC)),
        ("fold_embargo", datetime(2022, 1, 3, 13, tzinfo=UTC)),
        ("insufficient_forward", datetime(2025, 12, 31, 13, tzinfo=UTC)),
    ):
        _add_exclusion_case(spec, name, when)
    return spec


def _sessions(start: date, end: date) -> list[datetime]:
    output = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            output.append(datetime.combine(current, time(14, 30), tzinfo=UTC))
        current += timedelta(days=1)
    return output


def _observation(
    security_id: str,
    event_group_id: str,
    stable_record_id: str,
    family: str,
    direction: str,
    observed_at: datetime,
    *,
    version: str,
) -> dict[str, Any]:
    version_sha256 = _digest(f"{security_id}:{stable_record_id}:{version}")
    return {
        "source_id": SOURCE_ID,
        "security_id": security_id,
        "stable_record_id": stable_record_id,
        "version_sha256": version_sha256,
        "event_group_id": event_group_id,
        "accepted_or_published_at": _text(observed_at),
        "historically_available_at": _text(observed_at + timedelta(minutes=1)),
        "reconstructed_at": "2026-08-08T12:00:00.000000Z",
        "availability_proof_type": "provider_point_in_time_record",
        "availability_proof_reference": f"synthetic:{stable_record_id}:{version}",
        "evidence_snapshot": {
            "family": family,
            "direction": direction,
            "strength": "0.8500000000",
            "confidence": "0.8000000000",
            "source_quality": "0.9000000000",
            "timestamp": _text(observed_at),
        },
    }


def _add_exclusion_case(spec: dict[str, Any], name: str, evaluation_at: datetime) -> None:
    security_id = f"syn_excluded_{name}"
    stable_record_id = f"observation_excluded_{name}"
    observed_at = evaluation_at - timedelta(hours=1)
    observation = _observation(
        security_id,
        f"syn_event_excluded_{name}",
        stable_record_id,
        "filings_news",
        "neutral",
        observed_at,
        version="original",
    )
    spec["observations"].append(observation)
    spec["cases"].append(
        {
            "security_id": security_id,
            "event_group_id": f"syn_event_excluded_{name}",
            "evaluation_at": _text(evaluation_at),
            "case_type": "audit",
            "observation_refs": [_reference(observation)],
        }
    )


def _add_price(
    spec: dict[str, Any],
    security_id: str,
    session: datetime,
    open_factor: str,
    close_factor: str,
) -> None:
    stable_record_id = f"price_{security_id}_{session.date().isoformat()}"
    if any(
        row["security_id"] == security_id and row["session_open_at"] == _text(session)
        for row in spec["prices"]
    ):
        return
    spec["prices"].append(
        {
            "source_id": SOURCE_ID,
            "security_id": security_id,
            "stable_record_id": stable_record_id,
            "version_sha256": _digest(stable_record_id),
            "session_open_at": _text(session),
            "open_total_return_factor": open_factor,
            "close_total_return_factor": close_factor,
        }
    )


def _action(
    security_id: str,
    stable_record_id: str,
    action_type: str,
    effective: date,
    **details: str,
) -> dict[str, Any]:
    return {
        "source_id": SOURCE_ID,
        "security_id": security_id,
        "stable_record_id": stable_record_id,
        "version_sha256": _digest(f"action:{stable_record_id}"),
        "effective_at": _text(datetime.combine(effective, time(14, 30), tzinfo=UTC)),
        "action_type": action_type,
        **details,
    }


def _terminal_case(year: int, label: str, sample: int) -> tuple[str, str] | None:
    return {
        (2018, "bearish", 0): ("bankrupt", "0.0000000000"),
        (2019, "bearish", 0): ("delisted", "0.8000000000"),
        (2020, "bullish", 0): ("acquired", "1.0500000000"),
        (2021, "neutral", 0): ("inactive", "1.0000000000"),
    }.get((year, label, sample))


def _reference(observation: dict[str, Any]) -> str:
    return ":".join(
        (
            str(observation["source_id"]),
            str(observation["stable_record_id"]),
            str(observation["version_sha256"]),
        )
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _text(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
