import hashlib
import json
from dataclasses import replace
from datetime import datetime

import pytest

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.replay.evaluation import (
    EconomicCase,
    build_attempt_ledger,
    evaluate_untouched_test,
    freeze_untouched_unseal,
)
from catalyst_edge_mcp.replay.model import CLASSES, ModelRow, fit
from tests.test_trained_softmax import _rows


def _artifact_and_test_rows():
    artifact = fit(
        _rows(),
        dataset_sha256="a" * 64,
        config_sha256="b" * 64,
        code_sha256="c" * 64,
        exclusions_sha256="d" * 64,
        provenance="synthetic_only",
        epochs=10,
    )
    source = _rows()
    test_rows = []
    for year in (2024, 2025):
        for index, label in enumerate(CLASSES):
            template = next(row for row in source if row.label == label)
            test_rows.append(
                replace(
                    template,
                    evaluation_id=f"test_{year}_{label}",
                    event_group_id=f"test_group_{year}_{label}",
                    evaluated_at=datetime(year, 6, 10 + index, 16, tzinfo=UTC),
                    observation_ids=(f"observation_{year}_{label}",),
                )
            )
    return artifact, test_rows


def test_attempt_ledger_and_unseal_are_canonical_and_tamper_evident():
    attempts = [
        {
            "attempted_at": "2026-08-08T12:00:00Z",
            "kind": "model",
            "candidate": "trained_softmax:l2=0.1",
            "parameters_sha256": "a" * 64,
            "result_sha256": "b" * 64,
            "status": "completed",
        },
        {
            "attempted_at": "2026-08-08T12:01:00Z",
            "kind": "threshold",
            "candidate": "score>=70",
            "parameters_sha256": "c" * 64,
            "result_sha256": "d" * 64,
            "status": "rejected",
        },
    ]
    assert build_attempt_ledger(list(reversed(attempts))) == build_attempt_ledger(attempts)
    artifact, rows = _artifact_and_test_rows()
    unseal = freeze_untouched_unseal(
        artifact,
        rows,
        opened_at=datetime(2026, 8, 8, 13, tzinfo=UTC),
        owner="synthetic-contract-test",
    )
    assert json.loads(unseal)["artifact_sha256"] == hashlib.sha256(artifact).hexdigest()
    tampered = json.loads(unseal)
    tampered["owner"] = "changed"
    with pytest.raises(ValueError, match="unseal ID does not match"):
        evaluate_untouched_test(
            artifact,
            rows,
            _economic_cases(rows),
            json.dumps(tampered).encode(),
            bootstrap_iterations=100,
        )
    tampered = json.loads(unseal)
    tampered["candidates_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="frozen evidence does not match"):
        evaluate_untouched_test(
            artifact,
            rows,
            _economic_cases(rows),
            json.dumps(tampered).encode(),
            bootstrap_iterations=100,
        )


def test_synthetic_evaluation_reports_every_gate_and_fails_closed():
    artifact, rows = _artifact_and_test_rows()
    unseal = freeze_untouched_unseal(
        artifact,
        rows,
        opened_at=datetime(2026, 8, 8, 13, tzinfo=UTC),
        owner="synthetic-contract-test",
    )
    first = evaluate_untouched_test(
        artifact,
        rows,
        _economic_cases(rows),
        unseal,
        bootstrap_iterations=100,
    )
    assert (
        evaluate_untouched_test(
            artifact,
            list(reversed(rows)),
            list(reversed(_economic_cases(rows))),
            unseal,
            bootstrap_iterations=100,
        )
        == first
    )
    report = json.loads(first)
    assert len(report["all_candidates_validation"]) == 4
    assert set(report["untouched_test"]) == {
        "trained_softmax",
        "majority_class",
        "training_class_prior",
        "deterministic_v1",
    }
    assert set(report["economic_20_session"]["cost_scenarios"]) == {"base", "stressed"}
    assert report["economic_20_session"]["bootstrap_method"] == ("security-clustered/date-block")
    assert report["predictive_gates"]["stage_b_passed"] is False
    assert report["provenance"] == "synthetic_only"
    assert report["predictive_gates"]["minimum_untouched_rows"] is False
    assert report["predictive_claim"] == "backtested; no demonstrated predictive edge"


def _economic_cases(rows: list[ModelRow]) -> list[EconomicCase]:
    cases = []
    for index, row in enumerate(rows):
        label_return = {"bearish": -0.03, "neutral": 0.0, "bullish": 0.05}[row.label]
        cases.append(
            EconomicCase(
                evaluation_id=row.evaluation_id,
                security_cluster=f"security_{index}",
                date_block=row.evaluated_at.strftime("%Y-%m"),
                concentration_group=f"group_{index % 3}",
                case_spy_relative_return=label_return,
                control_spy_relative_return=0.0,
                calendar_days=28,
                walk_forward_fold=str(row.evaluated_at.year),
            )
        )
    return cases
