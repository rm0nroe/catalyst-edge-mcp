"""Evidence-bound artifact promotion; no manual Stage B switch exists."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from catalyst_edge_mcp.replay.contracts import canonical_json, stable_id
from catalyst_edge_mcp.replay.model import CLASSES, ModelArtifact, _artifact_id, load_artifact

PREDICTIVE_GATES = {
    "stage_b_passed",
    "minimum_untouched_rows",
    "calibration_improved_two_folds",
    "primary_ci_above_zero",
    "monotonic_score_bands",
    "walk_forward_stable",
    "concentration_clear",
}
AUDIT_MEASUREMENTS = {
    "provenance",
    "record_counts",
    "valid_cases",
    "untouched_cases",
    "years",
    "class_counts",
    "correction_versions",
    "control_cases",
    "action_types",
    "terminal_statuses",
    "exclusion_reasons",
    "ticker_reuse",
    "claimed_family_cells",
    "covered_family_cells",
    "claimed_family_evaluability",
}


def promote_artifact(
    artifact_data: bytes,
    audit_data: bytes,
    evaluation_data: bytes,
    *,
    expected_hashes: dict[str, str],
) -> bytes:
    """Promote only from matching immutable market audit and predictive evaluation records."""
    artifact = load_artifact(
        artifact_data,
        require_stage_b=False,
        expected_hashes=expected_hashes,
    )
    if artifact.stage_b_passed or artifact.promotion is not None:
        raise ValueError("trained model artifact is already promoted")
    if artifact.provenance != "rights_cleared_market":
        raise ValueError("synthetic artifacts cannot pass Stage B")
    audit = _record(audit_data, "dataset audit")
    evaluation = _record(evaluation_data, "untouched evaluation")
    _validate_audit(audit, artifact.frozen_hashes["dataset_sha256"])
    _validate_evaluation(evaluation, artifact)
    source_payload = json.loads(artifact_data)
    promotion: dict[str, Any] = {
        "schema_version": 1,
        "record_type": "artifact_promotion",
        "source_artifact_id": artifact.artifact_id,
        "source_artifact_sha256": hashlib.sha256(canonical_json(source_payload)).hexdigest(),
        "audit_record_id": audit["record_id"],
        "evaluation_record_id": evaluation["record_id"],
        "frozen_hashes": artifact.frozen_hashes,
    }
    promotion["record_id"] = stable_id(
        "ceprom", hashlib.sha256(canonical_json(promotion)).hexdigest()
    )
    payload = source_payload
    payload["stage_b_passed"] = True
    payload["promotion"] = promotion
    payload["artifact_id"] = _artifact_id(
        {key: value for key, value in payload.items() if key != "artifact_id"}
    )
    promoted = canonical_json(payload)
    load_artifact(promoted, expected_hashes=expected_hashes)
    return promoted


def _validate_audit(record: dict[str, Any], dataset_sha256: str) -> None:
    required = {
        "schema_version",
        "record_type",
        "record_id",
        "provenance",
        "dataset_version",
        "dataset_sha256",
        "measurements",
        "critical_errors",
        "engineering_gate_passed",
        "stage_b_gate",
        "stage_b_passed",
    }
    if set(record) != required or record.get("record_type") != "dataset_audit":
        raise ValueError("dataset audit schema is invalid")
    _validate_record_id(record, "ceaudit")
    measurements = record.get("measurements")
    if not isinstance(measurements, dict) or set(measurements) != AUDIT_MEASUREMENTS:
        raise ValueError("dataset audit measurements are invalid")
    valid_cases, untouched_cases, evaluability, engineering_gate = _audit_measurements(measurements)
    expected_gate = {
        "provenance": "rights_cleared_market",
        "minimum_valid_cases": valid_cases >= 1_000,
        "minimum_untouched_cases": untouched_cases >= 250,
        "claimed_family_evaluability": evaluability >= 0.95,
        "zero_critical_errors": record.get("critical_errors") == [],
        "rights_cleared_market": record.get("provenance") == "rights_cleared_market",
    }
    derived = (
        record.get("provenance") == "rights_cleared_market"
        and record.get("dataset_sha256") == dataset_sha256
        and record.get("critical_errors") == []
        and record.get("engineering_gate_passed") is engineering_gate
        and engineering_gate
        and record.get("stage_b_gate") == expected_gate
        and record.get("stage_b_passed") is True
        and all(expected_gate.values())
    )
    if not derived:
        raise ValueError("dataset audit does not derive a passing Stage B gate")


def _audit_measurements(record: dict[str, Any]) -> tuple[int, int, float, bool]:
    valid_cases = _nonnegative_integer(record["valid_cases"], "valid_cases")
    untouched_cases = _nonnegative_integer(record["untouched_cases"], "untouched_cases")
    correction_versions = _nonnegative_integer(record["correction_versions"], "correction_versions")
    control_cases = _nonnegative_integer(record["control_cases"], "control_cases")
    family_cells = _nonnegative_integer(record["claimed_family_cells"], "claimed_family_cells")
    covered_cells = _nonnegative_integer(record["covered_family_cells"], "covered_family_cells")
    evaluability = _number(record["claimed_family_evaluability"], "claimed_family_evaluability")
    counts = record["class_counts"]
    record_counts = record["record_counts"]
    exclusions = record["exclusion_reasons"]
    if (
        record.get("provenance") != "rights_cleared_market"
        or not isinstance(counts, dict)
        or set(counts) != set(CLASSES)
        or any(_nonnegative_integer(counts[name], f"{name} class count") < 1 for name in CLASSES)
        or sum(counts.values()) != valid_cases
        or not isinstance(record_counts, dict)
        or _nonnegative_integer(record_counts.get("label"), "label record count") != valid_cases
        or not isinstance(exclusions, dict)
        or any(
            _nonnegative_integer(exclusions.get(name), f"{name} exclusion count") < 1
            for name in (
                "label_window_crosses_fold",
                "fold_embargo",
                "insufficient_forward_sessions",
            )
        )
        or untouched_cases > valid_cases
        or family_cells < 1
        or covered_cells > family_cells
        or evaluability != round(covered_cells / family_cells, 12)
    ):
        raise ValueError("dataset audit measurements are internally inconsistent")
    years = record["years"]
    actions = record["action_types"]
    terminals = record["terminal_statuses"]
    ticker_reuse = record["ticker_reuse"]
    engineering_gate = (
        years == list(range(2018, 2026))
        and correction_versions > 0
        and control_cases > 0
        and isinstance(actions, list)
        and {"split", "cash_dividend", "ticker_start", "ticker_end"}.issubset(actions)
        and isinstance(terminals, list)
        and {"bankrupt", "delisted", "acquired", "inactive"}.issubset(terminals)
        and isinstance(ticker_reuse, list)
        and bool(ticker_reuse)
    )
    return valid_cases, untouched_cases, evaluability, engineering_gate


def _validate_evaluation(record: dict[str, Any], artifact: ModelArtifact) -> None:
    required = {
        "schema_version",
        "record_type",
        "record_id",
        "artifact_id",
        "provenance",
        "all_candidates_validation",
        "validation_baselines",
        "untouched_test",
        "economic_20_session",
        "predictive_gates",
        "predictive_claim",
    }
    if set(record) != required or record.get("record_type") != "untouched_test_evaluation":
        raise ValueError("untouched evaluation schema is invalid")
    _validate_record_id(record, "cetv")
    gates = record.get("predictive_gates")
    if not isinstance(gates, dict) or set(gates) != PREDICTIVE_GATES:
        raise ValueError("untouched evaluation gates are invalid")
    if record.get("all_candidates_validation") != artifact.report.get("candidates") or record.get(
        "validation_baselines"
    ) != artifact.report.get("baselines"):
        raise ValueError("untouched evaluation does not match the frozen artifact report")
    untouched_rows = _validate_untouched_metrics(record.get("untouched_test"))
    economic = _validate_economic_report(record.get("economic_20_session"))
    selected = next(
        (
            candidate
            for candidate in artifact.report["candidates"]
            if float(candidate["l2"]) == artifact.selected_l2
        ),
        None,
    )
    if not isinstance(selected, dict):
        raise ValueError("frozen artifact lacks its selected candidate")
    walk_forward = selected.get("walk_forward")
    if not isinstance(walk_forward, list) or any(
        not isinstance(fold, dict) or not isinstance(fold.get("improved"), bool)
        for fold in walk_forward
    ):
        raise ValueError("frozen artifact calibration report is invalid")
    calibration_folds = sum(fold["improved"] for fold in walk_forward)
    if (
        _integer(selected.get("calibration_improvement_folds"), "calibration_improvement_folds")
        != calibration_folds
    ):
        raise ValueError("frozen artifact calibration report is inconsistent")
    expected_gates = {
        "stage_b_passed": artifact.stage_b_passed,
        "minimum_untouched_rows": untouched_rows >= 250,
        "calibration_improved_two_folds": calibration_folds >= 2,
        "primary_ci_above_zero": economic["primary_ci_above_zero"],
        "monotonic_score_bands": economic["monotonic_score_bands"],
        "walk_forward_stable": economic["walk_forward_stable"],
        "concentration_clear": economic["concentration_clear"],
    }
    derived = (
        record.get("artifact_id") == artifact.artifact_id
        and record.get("provenance") == "rights_cleared_market"
        and gates == expected_gates
        and all(value is True for name, value in expected_gates.items() if name != "stage_b_passed")
        and record.get("predictive_claim") == "demonstrated predictive edge"
    )
    if not derived:
        raise ValueError("untouched evaluation does not derive passing predictive gates")


def _validate_untouched_metrics(value: object) -> int:
    expected_names = {
        "trained_softmax",
        "majority_class",
        "training_class_prior",
        "deterministic_v1",
    }
    metric_fields = {
        "provenance",
        "log_loss",
        "brier",
        "ece",
        "accuracy",
        "class_counts",
        "confusion_matrix",
    }
    if not isinstance(value, dict) or set(value) != expected_names:
        raise ValueError("untouched evaluation metrics are invalid")
    totals = set()
    for metrics in value.values():
        if (
            not isinstance(metrics, dict)
            or set(metrics) != metric_fields
            or metrics.get("provenance") != "rights_cleared_market"
        ):
            raise ValueError("untouched evaluation metrics are invalid")
        counts = metrics.get("class_counts")
        if not isinstance(counts, dict) or set(counts) != set(CLASSES):
            raise ValueError("untouched evaluation class counts are invalid")
        count_values = [
            _nonnegative_integer(counts[name], f"{name} class count") for name in CLASSES
        ]
        if any(count < 1 for count in count_values):
            raise ValueError("untouched evaluation class counts are invalid")
        total = sum(count_values)
        matrix = metrics.get("confusion_matrix")
        if (
            not isinstance(matrix, list)
            or len(matrix) != len(CLASSES)
            or any(not isinstance(row, list) or len(row) != len(CLASSES) for row in matrix)
        ):
            raise ValueError("untouched evaluation confusion matrix is invalid")
        parsed_matrix = [
            [_nonnegative_integer(cell, "confusion matrix cell") for cell in row] for row in matrix
        ]
        if [sum(row) for row in parsed_matrix] != count_values:
            raise ValueError("untouched evaluation confusion matrix is invalid")
        log_loss = _number(metrics.get("log_loss"), "log_loss")
        brier = _number(metrics.get("brier"), "brier")
        ece = _number(metrics.get("ece"), "ece")
        accuracy = _number(metrics.get("accuracy"), "accuracy")
        derived_accuracy = round(
            sum(parsed_matrix[index][index] for index in range(len(CLASSES))) / total,
            12,
        )
        if log_loss < 0 or not 0 <= brier <= 2 or not 0 <= ece <= 1 or accuracy != derived_accuracy:
            raise ValueError("untouched evaluation metrics are internally inconsistent")
        totals.add(total)
    if len(totals) != 1:
        raise ValueError("untouched evaluation row counts do not match")
    return totals.pop()


def _validate_economic_report(value: object) -> dict[str, bool]:
    required = {
        "provenance",
        "high_bucket",
        "high_bucket_cases",
        "primary_mean_difference",
        "bootstrap_method",
        "bootstrap_iterations",
        "bootstrap_seed",
        "bootstrap_95_ci",
        "cost_scenarios",
        "score_band_means",
        "monotonic_score_bands",
        "walk_forward_means",
        "walk_forward_stable",
        "concentration",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("untouched economic report is invalid")
    if (
        value.get("provenance") != "rights_cleared_market"
        or value.get("high_bucket") != "score >= 70"
        or value.get("bootstrap_method") != "security-clustered/date-block"
        or _integer(value.get("bootstrap_iterations"), "bootstrap_iterations") < 100
        or _integer(value.get("high_bucket_cases"), "high_bucket_cases") < 1
    ):
        raise ValueError("untouched economic report is invalid")
    _number(value.get("primary_mean_difference"), "primary_mean_difference")
    _integer(value.get("bootstrap_seed"), "bootstrap_seed")
    _validate_cost_scenarios(value.get("cost_scenarios"))
    interval = value.get("bootstrap_95_ci")
    if not isinstance(interval, list) or len(interval) != 2:
        raise ValueError("untouched economic confidence interval is invalid")
    lower, upper = (_number(item, "bootstrap confidence interval") for item in interval)
    if lower > upper:
        raise ValueError("untouched economic confidence interval is invalid")
    bands = value.get("score_band_means")
    if not isinstance(bands, dict) or set(bands) != {"0_49", "50_69", "70_100"}:
        raise ValueError("untouched score bands are invalid")
    band_values = [
        _number(bands[name], f"{name} score band") for name in ("0_49", "50_69", "70_100")
    ]
    monotonic = band_values[0] <= band_values[1] <= band_values[2]
    folds = value.get("walk_forward_means")
    if not isinstance(folds, dict):
        raise ValueError("untouched walk-forward report is invalid")
    fold_values = [_number(item, "walk-forward mean") for item in folds.values()]
    walk_forward = len(fold_values) >= 2 and all(item > 0 for item in fold_values)
    concentration = value.get("concentration")
    concentration_fields = {
        "max_security_share",
        "security_hhi",
        "max_date_block_share",
        "date_block_hhi",
        "max_group_share",
        "group_hhi",
        "material",
    }
    if not isinstance(concentration, dict) or set(concentration) != concentration_fields:
        raise ValueError("untouched concentration report is invalid")
    security_share = _number(concentration["max_security_share"], "max_security_share")
    security_hhi = _number(concentration["security_hhi"], "security_hhi")
    date_share = _number(concentration["max_date_block_share"], "max_date_block_share")
    date_hhi = _number(concentration["date_block_hhi"], "date_block_hhi")
    group_share = _number(concentration["max_group_share"], "max_group_share")
    group_hhi = _number(concentration["group_hhi"], "group_hhi")
    if any(
        not 0 <= item <= 1
        for item in (security_share, security_hhi, date_share, date_hhi, group_share, group_hhi)
    ):
        raise ValueError("untouched concentration report is invalid")
    material = security_share > 0.25 or date_share > 0.35 or group_share > 0.40
    if (
        value.get("monotonic_score_bands") is not monotonic
        or value.get("walk_forward_stable") is not walk_forward
        or concentration.get("material") is not material
    ):
        raise ValueError("untouched economic derived fields do not match")
    return {
        "primary_ci_above_zero": lower > 0,
        "monotonic_score_bands": monotonic,
        "walk_forward_stable": walk_forward,
        "concentration_clear": not material,
    }


def _validate_cost_scenarios(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"base", "stressed"}:
        raise ValueError("untouched cost scenarios are invalid")
    fields = {
        "half_spread_bps_per_side",
        "slippage_bps_per_side",
        "annual_borrow_rate",
        "mean_case_net",
        "mean_control_net",
        "mean_difference",
    }
    expected = {"base": (5, 5, 0.03), "stressed": (15, 15, 0.10)}
    for name, scenario in value.items():
        if not isinstance(scenario, dict) or set(scenario) != fields:
            raise ValueError("untouched cost scenarios are invalid")
        half_spread, slippage, borrow = expected[name]
        case_net = _number(scenario["mean_case_net"], f"{name} mean_case_net")
        control_net = _number(scenario["mean_control_net"], f"{name} mean_control_net")
        difference = _number(scenario["mean_difference"], f"{name} mean_difference")
        if (
            scenario["half_spread_bps_per_side"] != half_spread
            or scenario["slippage_bps_per_side"] != slippage
            or scenario["annual_borrow_rate"] != borrow
            or difference != round(case_net - control_net, 12)
        ):
            raise ValueError("untouched cost scenarios are internally inconsistent")


def _validate_record_id(record: dict[str, Any], prefix: str) -> None:
    body = {key: value for key, value in record.items() if key != "record_id"}
    expected = stable_id(prefix, hashlib.sha256(canonical_json(body)).hexdigest())
    if record.get("record_id") != expected:
        raise ValueError(f"{record.get('record_type')} record ID does not match")


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    return value


def _nonnegative_integer(value: object, name: str) -> int:
    parsed = _integer(value, name)
    if parsed < 0:
        raise ValueError(f"{name} must be nonnegative")
    return parsed


def _number(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


def _record(data: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{name} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value
