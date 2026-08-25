import json
from copy import deepcopy
from pathlib import Path

import pytest

from catalyst_edge_mcp.replay.audit import audit_dataset
from catalyst_edge_mcp.replay.contracts import canonical_json, stable_id
from catalyst_edge_mcp.replay.model import _artifact_id, fit, load_artifact
from catalyst_edge_mcp.replay.pipeline import run_synthetic_pipeline
from catalyst_edge_mcp.replay.promotion import promote_artifact
from catalyst_edge_mcp.server import build_service
from catalyst_edge_mcp.settings import Settings
from tests.test_trained_softmax import _rows


def test_synthetic_pipeline_is_reproducible_complete_and_fail_closed(tmp_path):
    root = tmp_path / "synthetic-run"
    first = run_synthetic_pipeline(root, epochs=5)
    assert run_synthetic_pipeline(root, epochs=5) == first
    assert first["provenance"] == "synthetic_only"
    assert first["stage_b_passed"] is False
    assert first["public_scoring_method"] == "deterministic_v1"
    assert first["public_model_status"] == "not_trained"

    bundle = root / first["dataset_version"]
    audit = json.loads((bundle / "coverage-audit.json").read_bytes())
    assert audit["engineering_gate_passed"] is True
    assert audit["stage_b_passed"] is False
    assert audit["measurements"]["years"] == list(range(2018, 2026))
    assert set(audit["measurements"]["class_counts"]) == {
        "bearish",
        "neutral",
        "bullish",
    }
    assert audit["measurements"]["correction_versions"] > 0
    assert audit["measurements"]["ticker_reuse"] == ["REUSE"]
    assert set(audit["measurements"]["terminal_statuses"]) >= {
        "bankrupt",
        "delisted",
        "acquired",
        "inactive",
    }
    assert (
        audit["measurements"]["covered_family_cells"]
        < audit["measurements"]["claimed_family_cells"]
    )
    spec = json.loads((root / "synthetic-spec.json").read_bytes())
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    dataset = (bundle / "dataset.jsonl").read_bytes()
    mismatch = json.loads(audit_dataset(spec, dataset.replace(b'{"', b'{ "', 1), manifest))
    assert mismatch["critical_errors"] == ["manifest_dataset_sha256_mismatch"]
    assert mismatch["engineering_gate_passed"] is False
    assert mismatch["stage_b_passed"] is False

    artifact = Path(first["artifact_path"]).read_bytes()
    runtime_manifest = bundle / "runtime-manifest.json"
    shadow_service = build_service(
        Settings(
            model_mode="shadow",
            model_artifact_path=first["artifact_path"],
            model_manifest_path=str(runtime_manifest),
            gdelt_enabled=False,
        )
    )
    assert shadow_service.scorer.method == "deterministic_v1"
    assert shadow_service.shadow_scorer.method == "trained_softmax"
    with pytest.raises(ValueError, match="has not passed Stage B"):
        build_service(
            Settings(
                model_mode="active",
                model_artifact_path=first["artifact_path"],
                model_manifest_path=str(runtime_manifest),
                gdelt_enabled=False,
            )
        )
    with pytest.raises(ValueError, match="synthetic artifacts cannot pass Stage B"):
        promote_artifact(
            artifact,
            (bundle / "coverage-audit.json").read_bytes(),
            (bundle / "synthetic-evaluation.json").read_bytes(),
            expected_hashes=json.loads(artifact)["frozen_hashes"],
        )


def test_promotion_is_derived_from_bound_audit_and_evaluation_records():
    hashes = {
        "dataset_sha256": "a" * 64,
        "config_sha256": "b" * 64,
        "code_sha256": "c" * 64,
        "exclusions_sha256": "d" * 64,
    }
    artifact = fit(
        _rows(),
        **hashes,
        provenance="rights_cleared_market",
        epochs=5,
    )
    artifact_payload = json.loads(artifact)
    selected = next(
        candidate
        for candidate in artifact_payload["report"]["candidates"]
        if candidate["l2"] == artifact_payload["selected_l2"]
    )
    selected["calibration_improvement_folds"] = 2
    for fold in selected["walk_forward"][:2]:
        fold["improved"] = True
    artifact_payload["artifact_id"] = _artifact_id(
        {key: value for key, value in artifact_payload.items() if key != "artifact_id"}
    )
    artifact = canonical_json(artifact_payload)
    artifact_id = artifact_payload["artifact_id"]
    audit = {
        "schema_version": 1,
        "record_type": "dataset_audit",
        "provenance": "rights_cleared_market",
        "dataset_version": "ced_fixture",
        "dataset_sha256": hashes["dataset_sha256"],
        "measurements": {
            "provenance": "rights_cleared_market",
            "record_counts": {"label": 1_000},
            "valid_cases": 1_000,
            "untouched_cases": 250,
            "years": list(range(2018, 2026)),
            "class_counts": {"bearish": 333, "neutral": 333, "bullish": 334},
            "correction_versions": 1,
            "control_cases": 300,
            "action_types": ["cash_dividend", "split", "ticker_end", "ticker_start"],
            "terminal_statuses": ["acquired", "bankrupt", "delisted", "inactive"],
            "exclusion_reasons": {
                "fold_embargo": 1,
                "insufficient_forward_sessions": 1,
                "label_window_crosses_fold": 1,
            },
            "ticker_reuse": ["REUSE"],
            "claimed_family_cells": 5_000,
            "covered_family_cells": 4_750,
            "claimed_family_evaluability": 0.95,
        },
        "critical_errors": [],
        "engineering_gate_passed": True,
        "stage_b_gate": {
            "provenance": "rights_cleared_market",
            "minimum_valid_cases": True,
            "minimum_untouched_cases": True,
            "claimed_family_evaluability": True,
            "zero_critical_errors": True,
            "rights_cleared_market": True,
        },
        "stage_b_passed": True,
    }
    audit["record_id"] = _record_id("ceaudit", audit)
    metrics = {
        "provenance": "rights_cleared_market",
        "log_loss": 0.5,
        "brier": 0.4,
        "ece": 0.1,
        "accuracy": 0.68,
        "class_counts": {"bearish": 80, "neutral": 85, "bullish": 85},
        "confusion_matrix": [[50, 15, 15], [10, 60, 15], [10, 15, 60]],
    }
    evaluation = {
        "schema_version": 1,
        "record_type": "untouched_test_evaluation",
        "artifact_id": artifact_id,
        "provenance": "rights_cleared_market",
        "all_candidates_validation": artifact_payload["report"]["candidates"],
        "validation_baselines": artifact_payload["report"]["baselines"],
        "untouched_test": {
            name: deepcopy(metrics)
            for name in (
                "trained_softmax",
                "majority_class",
                "training_class_prior",
                "deterministic_v1",
            )
        },
        "economic_20_session": {
            "provenance": "rights_cleared_market",
            "high_bucket": "score >= 70",
            "high_bucket_cases": 40,
            "primary_mean_difference": 0.03,
            "bootstrap_method": "security-clustered/date-block",
            "bootstrap_iterations": 2_000,
            "bootstrap_seed": 17,
            "bootstrap_95_ci": [0.01, 0.05],
            "cost_scenarios": {
                "base": {
                    "half_spread_bps_per_side": 5,
                    "slippage_bps_per_side": 5,
                    "annual_borrow_rate": 0.03,
                    "mean_case_net": 0.028,
                    "mean_control_net": -0.002,
                    "mean_difference": 0.03,
                },
                "stressed": {
                    "half_spread_bps_per_side": 15,
                    "slippage_bps_per_side": 15,
                    "annual_borrow_rate": 0.10,
                    "mean_case_net": 0.024,
                    "mean_control_net": -0.006,
                    "mean_difference": 0.03,
                },
            },
            "score_band_means": {"0_49": -0.02, "50_69": 0.0, "70_100": 0.03},
            "monotonic_score_bands": True,
            "walk_forward_means": {"2024": 0.02, "2025": 0.03},
            "walk_forward_stable": True,
            "concentration": {
                "max_security_share": 0.10,
                "security_hhi": 0.05,
                "max_date_block_share": 0.20,
                "date_block_hhi": 0.10,
                "max_group_share": 0.30,
                "group_hhi": 0.20,
                "material": False,
            },
        },
        "predictive_gates": {
            "stage_b_passed": False,
            "minimum_untouched_rows": True,
            "calibration_improved_two_folds": True,
            "primary_ci_above_zero": True,
            "monotonic_score_bands": True,
            "walk_forward_stable": True,
            "concentration_clear": True,
        },
        "predictive_claim": "demonstrated predictive edge",
    }
    evaluation["record_id"] = _record_id("cetv", evaluation)
    incomplete_evaluation = deepcopy(evaluation)
    incomplete_evaluation["predictive_gates"] = {"stage_b_passed": False}
    incomplete_evaluation.pop("record_id")
    incomplete_evaluation["record_id"] = _record_id("cetv", incomplete_evaluation)
    with pytest.raises(ValueError, match="evaluation gates are invalid"):
        promote_artifact(
            artifact,
            canonical_json(audit),
            canonical_json(incomplete_evaluation),
            expected_hashes=hashes,
        )

    self_asserted = deepcopy(evaluation)
    self_asserted["economic_20_session"]["bootstrap_95_ci"] = [-0.01, 0.05]
    self_asserted.pop("record_id")
    self_asserted["record_id"] = _record_id("cetv", self_asserted)
    with pytest.raises(ValueError, match="does not derive passing predictive gates"):
        promote_artifact(
            artifact,
            canonical_json(audit),
            canonical_json(self_asserted),
            expected_hashes=hashes,
        )

    manual = json.loads(artifact)
    manual["stage_b_passed"] = True
    manual["promotion"] = {}
    manual["artifact_id"] = _artifact_id(
        {key: value for key, value in manual.items() if key != "artifact_id"}
    )
    with pytest.raises(ValueError, match="promotion record is invalid"):
        load_artifact(canonical_json(manual), expected_hashes=hashes)

    promoted = promote_artifact(
        artifact,
        canonical_json(audit),
        canonical_json(evaluation),
        expected_hashes=hashes,
    )
    loaded = load_artifact(promoted, expected_hashes=hashes)
    assert loaded.stage_b_passed is True
    assert loaded.promotion["audit_record_id"] == audit["record_id"]
    assert loaded.promotion["evaluation_record_id"] == evaluation["record_id"]


def _record_id(prefix, value):
    import hashlib

    return stable_id(prefix, hashlib.sha256(canonical_json(value)).hexdigest())
