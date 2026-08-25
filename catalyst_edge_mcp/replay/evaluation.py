"""Fail-closed provider-neutral evaluation records for ``trained_softmax``."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.replay.contracts import canonical_json, canonical_jsonl, stable_id
from catalyst_edge_mcp.replay.model import (
    CLASSES,
    ModelRow,
    _metrics,
    canonical_model_rows,
    load_artifact,
)

ATTEMPT_KINDS = {"model", "weight", "threshold", "horizon", "subgroup"}
ATTEMPT_STATUSES = {"completed", "failed", "rejected"}


@dataclass(frozen=True, slots=True)
class EconomicCase:
    evaluation_id: str
    security_cluster: str
    date_block: str
    concentration_group: str
    case_spy_relative_return: float
    control_spy_relative_return: float
    calendar_days: int
    walk_forward_fold: str


def build_attempt_ledger(attempts: list[dict[str, object]]) -> bytes:
    """Freeze every attempted search as content-addressed canonical records."""
    records = []
    required = {
        "attempted_at",
        "kind",
        "candidate",
        "parameters_sha256",
        "result_sha256",
        "status",
    }
    for attempt in attempts:
        if set(attempt) != required:
            raise ValueError("model attempt has an invalid schema")
        attempted_at = _timestamp_text(_timestamp(attempt["attempted_at"]))
        kind = str(attempt["kind"])
        status = str(attempt["status"])
        candidate = str(attempt["candidate"])
        if kind not in ATTEMPT_KINDS or status not in ATTEMPT_STATUSES or not candidate:
            raise ValueError("model attempt values are invalid")
        parameters_sha256 = _sha256(attempt["parameters_sha256"], "parameters_sha256")
        result_sha256 = _sha256(attempt["result_sha256"], "result_sha256")
        record = {
            "record_type": "model_attempt",
            "attempted_at": attempted_at,
            "kind": kind,
            "candidate": candidate,
            "parameters_sha256": parameters_sha256,
            "result_sha256": result_sha256,
            "status": status,
        }
        record["record_id"] = stable_id("cma", hashlib.sha256(canonical_json(record)).hexdigest())
        records.append(record)
    if len({record["record_id"] for record in records}) != len(records):
        raise ValueError("model attempt ledger contains duplicates")
    return canonical_jsonl(records)


def freeze_untouched_unseal(
    artifact_data: bytes,
    rows: list[ModelRow],
    *,
    opened_at: datetime,
    owner: str,
) -> bytes:
    """Bind the sole untouched-test opening to exact artifact and row bytes."""
    artifact = load_artifact(artifact_data, require_stage_b=False)
    if not owner.strip():
        raise ValueError("untouched-test unseal owner is required")
    _require_untouched_rows(rows)
    row_sha256 = hashlib.sha256(canonical_model_rows(rows)).hexdigest()
    body = {
        "schema_version": 1,
        "record_type": "untouched_test_unseal",
        "artifact_id": artifact.artifact_id,
        "provenance": artifact.provenance,
        "artifact_sha256": hashlib.sha256(artifact_data).hexdigest(),
        "untouched_rows_sha256": row_sha256,
        "opened_at": _timestamp_text(_timestamp(opened_at)),
        "owner": owner.strip(),
        "frozen_hashes": artifact.frozen_hashes,
        "candidates_sha256": hashlib.sha256(
            canonical_json(artifact.report.get("candidates"))
        ).hexdigest(),
        "baselines_sha256": hashlib.sha256(
            canonical_json(artifact.report.get("baselines"))
        ).hexdigest(),
    }
    body["record_id"] = stable_id("ceu", hashlib.sha256(canonical_json(body)).hexdigest())
    return canonical_json(body)


def evaluate_untouched_test(
    artifact_data: bytes,
    rows: list[ModelRow],
    economic_cases: list[EconomicCase],
    unseal_data: bytes,
    *,
    bootstrap_iterations: int = 2_000,
    bootstrap_seed: int = 17,
) -> bytes:
    """Report the frozen holdout without promoting synthetic evidence or claims."""
    if bootstrap_iterations < 100:
        raise ValueError("bootstrap_iterations must be at least 100")
    artifact = load_artifact(artifact_data, require_stage_b=False)
    _require_untouched_rows(rows)
    _validate_unseal(unseal_data, artifact_data, rows)
    rows_by_id = {row.evaluation_id: row for row in rows}
    cases_by_id = {case.evaluation_id: case for case in economic_cases}
    if len(cases_by_id) != len(economic_cases) or set(cases_by_id) != set(rows_by_id):
        raise ValueError("economic cases must map one-to-one to untouched rows")
    _validate_economic_cases(economic_cases)

    ordered_rows = sorted(rows, key=lambda row: (row.evaluated_at, row.evaluation_id))
    labels = [CLASSES.index(row.label) for row in ordered_rows]
    probabilities = [artifact.probabilities(row.features) for row in ordered_rows]
    predictions = [artifact.predict(row.features) for row in ordered_rows]
    prior_record = artifact.report.get("training_class_prior")
    if not isinstance(prior_record, dict) or set(prior_record) != set(CLASSES):
        raise ValueError("artifact lacks frozen training class prior")
    prior = tuple(float(prior_record[name]) for name in CLASSES)
    majority = max(range(3), key=prior.__getitem__)
    untouched = {
        "trained_softmax": _metrics(probabilities, labels, provenance=artifact.provenance),
        "majority_class": _metrics(
            [tuple(1.0 if index == majority else 0.0 for index in range(3))] * len(ordered_rows),
            labels,
            probability_floor=1e-12,
            provenance=artifact.provenance,
        ),
        "training_class_prior": _metrics(
            [prior] * len(ordered_rows), labels, provenance=artifact.provenance
        ),
        "deterministic_v1": _metrics(
            [
                tuple(
                    1.0 if index == CLASSES.index(row.deterministic_class) else 0.0
                    for index in range(3)
                )
                for row in ordered_rows
            ],
            labels,
            probability_floor=1e-12,
            provenance=artifact.provenance,
        ),
    }
    prediction_by_id = dict(
        zip((row.evaluation_id for row in ordered_rows), predictions, strict=True)
    )
    economic = _economic_proof(
        economic_cases,
        prediction_by_id,
        provenance=artifact.provenance,
        iterations=bootstrap_iterations,
        seed=bootstrap_seed,
    )
    selected = next(
        item for item in artifact.report["candidates"] if float(item["l2"]) == artifact.selected_l2
    )
    gates = {
        "stage_b_passed": artifact.stage_b_passed,
        "minimum_untouched_rows": len(rows) >= 250,
        "calibration_improved_two_folds": int(selected.get("calibration_improvement_folds", 0))
        >= 2,
        "primary_ci_above_zero": economic["bootstrap_95_ci"][0] is not None
        and economic["bootstrap_95_ci"][0] > 0,
        "monotonic_score_bands": economic["monotonic_score_bands"],
        "walk_forward_stable": economic["walk_forward_stable"],
        "concentration_clear": not economic["concentration"]["material"],
    }
    result = {
        "schema_version": 1,
        "record_type": "untouched_test_evaluation",
        "artifact_id": artifact.artifact_id,
        "provenance": artifact.provenance,
        "all_candidates_validation": artifact.report["candidates"],
        "validation_baselines": artifact.report["baselines"],
        "untouched_test": untouched,
        "economic_20_session": economic,
        "predictive_gates": gates,
        "predictive_claim": (
            "demonstrated predictive edge"
            if artifact.provenance == "rights_cleared_market"
            and all(value for name, value in gates.items() if name != "stage_b_passed")
            else "backtested; no demonstrated predictive edge"
        ),
    }
    result["record_id"] = stable_id("cetv", hashlib.sha256(canonical_json(result)).hexdigest())
    return canonical_json(result)


def _economic_proof(
    cases: list[EconomicCase],
    predictions: dict[str, dict[str, object]],
    *,
    provenance: str,
    iterations: int,
    seed: int,
) -> dict[str, object]:
    scored = [(case, int(predictions[case.evaluation_id]["score"])) for case in cases]
    high = [(case, score) for case, score in scored if score >= 70]
    differences = [
        (case, case.case_spy_relative_return - case.control_spy_relative_return) for case, _ in high
    ]
    scenarios = {
        "base": _cost_scenario(high, half_spread_bps=5, slippage_bps=5, borrow_rate=0.03),
        "stressed": _cost_scenario(high, half_spread_bps=15, slippage_bps=15, borrow_rate=0.10),
    }
    ci = (
        _two_way_cluster_bootstrap(differences, iterations=iterations, seed=seed)
        if differences
        else (None, None)
    )
    bands: dict[str, list[float]] = {"0_49": [], "50_69": [], "70_100": []}
    for case, score in scored:
        name = "0_49" if score < 50 else "50_69" if score < 70 else "70_100"
        bands[name].append(case.case_spy_relative_return - case.control_spy_relative_return)
    band_means = {name: _mean(values) if values else None for name, values in bands.items()}
    monotonic = all(value is not None for value in band_means.values()) and (
        band_means["0_49"] <= band_means["50_69"] <= band_means["70_100"]
    )
    fold_values: dict[str, list[float]] = {}
    for case, value in differences:
        fold_values.setdefault(case.walk_forward_fold, []).append(value)
    walk_forward = {name: _mean(values) for name, values in sorted(fold_values.items())}
    concentration = _concentration([case for case, _ in high])
    return {
        "provenance": provenance,
        "high_bucket": "score >= 70",
        "high_bucket_cases": len(high),
        "primary_mean_difference": (
            round(_mean([value for _, value in differences]), 12) if differences else None
        ),
        "bootstrap_method": "security-clustered/date-block",
        "bootstrap_iterations": iterations,
        "bootstrap_seed": seed,
        "bootstrap_95_ci": [round(value, 12) if value is not None else None for value in ci],
        "cost_scenarios": scenarios,
        "score_band_means": band_means,
        "monotonic_score_bands": monotonic,
        "walk_forward_means": walk_forward,
        "walk_forward_stable": len(walk_forward) >= 2
        and all(value > 0 for value in walk_forward.values()),
        "concentration": concentration,
    }


def _cost_scenario(
    values: list[tuple[EconomicCase, int]],
    *,
    half_spread_bps: int,
    slippage_bps: int,
    borrow_rate: float,
) -> dict[str, object]:
    case_net = []
    control_net = []
    for case, score in values:
        sign = -1 if score <= 45 else 1
        cost = 2 * (half_spread_bps + slippage_bps) / 10_000
        if sign < 0:
            cost += borrow_rate * case.calendar_days / 365
        case_net.append(sign * case.case_spy_relative_return - cost)
        control_net.append(sign * case.control_spy_relative_return - cost)
    return {
        "half_spread_bps_per_side": half_spread_bps,
        "slippage_bps_per_side": slippage_bps,
        "annual_borrow_rate": borrow_rate,
        "mean_case_net": round(_mean(case_net), 12) if case_net else None,
        "mean_control_net": round(_mean(control_net), 12) if control_net else None,
        "mean_difference": (round(_mean(case_net) - _mean(control_net), 12) if case_net else None),
    }


def _two_way_cluster_bootstrap(
    values: list[tuple[EconomicCase, float]], *, iterations: int, seed: int
) -> tuple[float, float]:
    securities = sorted({case.security_cluster for case, _ in values})
    dates = sorted({case.date_block for case, _ in values})
    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        security_weights = Counter(rng.choices(securities, k=len(securities)))
        date_weights = Counter(rng.choices(dates, k=len(dates)))
        weighted = [
            (value, security_weights[case.security_cluster] * date_weights[case.date_block])
            for case, value in values
        ]
        total_weight = sum(weight for _, weight in weighted)
        if total_weight:
            estimates.append(sum(value * weight for value, weight in weighted) / total_weight)
    if not estimates:
        raise ValueError("cluster bootstrap produced no samples")
    estimates.sort()
    return (_percentile(estimates, 0.025), _percentile(estimates, 0.975))


def _concentration(cases: list[EconomicCase]) -> dict[str, object]:
    total = len(cases)
    if not total:
        return {
            "max_security_share": None,
            "security_hhi": None,
            "max_date_block_share": None,
            "date_block_hhi": None,
            "max_group_share": None,
            "group_hhi": None,
            "material": True,
        }

    def shares(values: list[str]) -> tuple[float, float]:
        counts = Counter(values)
        fractions = [count / total for count in counts.values()]
        return max(fractions), sum(value * value for value in fractions)

    security_max, security_hhi = shares([case.security_cluster for case in cases])
    date_max, date_hhi = shares([case.date_block for case in cases])
    group_max, group_hhi = shares([case.concentration_group for case in cases])
    return {
        "max_security_share": round(security_max, 12),
        "security_hhi": round(security_hhi, 12),
        "max_date_block_share": round(date_max, 12),
        "date_block_hhi": round(date_hhi, 12),
        "max_group_share": round(group_max, 12),
        "group_hhi": round(group_hhi, 12),
        "material": security_max > 0.25 or date_max > 0.35 or group_max > 0.40,
    }


def _validate_unseal(data: bytes, artifact_data: bytes, rows: list[ModelRow]) -> None:
    try:
        record = json.loads(data)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("untouched-test unseal is invalid JSON") from exc
    artifact = load_artifact(artifact_data, require_stage_b=False)
    expected = {
        "schema_version",
        "record_type",
        "record_id",
        "artifact_id",
        "provenance",
        "artifact_sha256",
        "untouched_rows_sha256",
        "opened_at",
        "owner",
        "frozen_hashes",
        "candidates_sha256",
        "baselines_sha256",
    }
    if not isinstance(record, dict) or set(record) != expected:
        raise ValueError("untouched-test unseal has an invalid schema")
    if (
        record["artifact_id"] != artifact.artifact_id
        or record["provenance"] != artifact.provenance
        or record["artifact_sha256"] != hashlib.sha256(artifact_data).hexdigest()
    ):
        raise ValueError("untouched-test unseal artifact does not match")
    if record["untouched_rows_sha256"] != hashlib.sha256(canonical_model_rows(rows)).hexdigest():
        raise ValueError("untouched-test unseal rows do not match")
    if (
        record["frozen_hashes"] != artifact.frozen_hashes
        or record["candidates_sha256"]
        != hashlib.sha256(canonical_json(artifact.report.get("candidates"))).hexdigest()
        or record["baselines_sha256"]
        != hashlib.sha256(canonical_json(artifact.report.get("baselines"))).hexdigest()
    ):
        raise ValueError("untouched-test unseal frozen evidence does not match")
    body = {key: value for key, value in record.items() if key != "record_id"}
    expected_id = stable_id("ceu", hashlib.sha256(canonical_json(body)).hexdigest())
    if record["record_id"] != expected_id:
        raise ValueError("untouched-test unseal ID does not match")


def _require_untouched_rows(rows: list[ModelRow]) -> None:
    if not rows or any(row.evaluated_at.astimezone(UTC).year not in {2024, 2025} for row in rows):
        raise ValueError("untouched-test rows must be within 2024-2025")
    if {row.label for row in rows} != set(CLASSES):
        raise ValueError("untouched test must contain bearish, neutral, and bullish rows")


def _validate_economic_cases(cases: list[EconomicCase]) -> None:
    for case in cases:
        if (
            not case.security_cluster
            or not case.date_block
            or not case.concentration_group
            or not case.walk_forward_fold
            or case.calendar_days < 1
            or not math.isfinite(case.case_spy_relative_return)
            or not math.isfinite(case.control_spy_relative_return)
        ):
            raise ValueError("economic case values are invalid")


def _percentile(values: list[float], quantile: float) -> float:
    index = (len(values) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include an offset")
    return parsed.astimezone(UTC)


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sha256(value: object, name: str) -> str:
    text = str(value)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return text
