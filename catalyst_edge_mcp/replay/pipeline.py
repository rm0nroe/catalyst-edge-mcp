"""Run the complete synthetic-only replay, model, evaluation, and shadow path."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import Direction, Evidence
from catalyst_edge_mcp.replay.audit import audit_dataset
from catalyst_edge_mcp.replay.build import _atomic_write, replay_bundle, write_bundle
from catalyst_edge_mcp.replay.contracts import canonical_json, dataset_version
from catalyst_edge_mcp.replay.evaluation import (
    EconomicCase,
    evaluate_untouched_test,
    freeze_untouched_unseal,
)
from catalyst_edge_mcp.replay.model import fit, materialize_model_rows
from catalyst_edge_mcp.replay.runtime import load_runtime_scorer
from catalyst_edge_mcp.replay.synthetic import build_synthetic_spec


def run_synthetic_pipeline(root: Path, *, epochs: int = 100) -> dict[str, object]:
    if epochs < 1:
        raise ValueError("epochs must be positive")
    root.mkdir(parents=True, exist_ok=True)
    spec = build_synthetic_spec()
    version = dataset_version(spec)
    spec_path = root / "synthetic-spec.json"
    _write_matching(spec_path, canonical_json(spec))
    if (root / version).exists():
        manifest = replay_bundle(version, root)
    else:
        manifest = write_bundle(spec_path, root)
    bundle = root / version
    dataset = (bundle / "dataset.jsonl").read_bytes()
    audit_data = audit_dataset(spec, dataset, manifest)
    audit = json.loads(audit_data)
    if not audit["engineering_gate_passed"] or audit["stage_b_passed"]:
        raise ValueError("synthetic coverage audit did not pass its fail-closed contract")
    _write_matching(bundle / "coverage-audit.json", audit_data)

    rows, model_rows = materialize_model_rows(dataset)
    fit_rows = [row for row in rows if row.evaluated_at.year <= 2023]
    untouched_rows = [row for row in rows if row.evaluated_at.year >= 2024]
    exclusions = (
        b"\n".join(line for line in dataset.splitlines() if b'"record_type":"exclusion"' in line)
        + b"\n"
    )
    frozen_hashes = {
        "dataset_sha256": manifest["canonical_sha256"],
        "config_sha256": spec["config_sha256"],
        "code_sha256": spec["code_sha256"],
        "exclusions_sha256": hashlib.sha256(exclusions).hexdigest(),
    }
    artifact_data = fit(
        fit_rows,
        **frozen_hashes,
        provenance="synthetic_only",
        epochs=epochs,
    )
    artifact_sha256 = hashlib.sha256(artifact_data).hexdigest()
    artifact_path = bundle / f"artifact-{artifact_sha256}.json"
    _write_matching(artifact_path, artifact_data)

    unseal_data = freeze_untouched_unseal(
        artifact_data,
        untouched_rows,
        opened_at=datetime(2026, 8, 8, 12, tzinfo=UTC),
        owner="synthetic-engineering-pipeline",
    )
    evaluation_data = evaluate_untouched_test(
        artifact_data,
        untouched_rows,
        _economic_cases(untouched_rows),
        unseal_data,
        bootstrap_iterations=100,
    )
    evaluation = json.loads(evaluation_data)
    if (
        evaluation["provenance"] != "synthetic_only"
        or evaluation["predictive_gates"]["stage_b_passed"]
    ):
        raise ValueError("synthetic evaluation escaped its fail-closed provenance")
    _write_matching(bundle / "untouched-unseal.json", unseal_data)
    _write_matching(bundle / "synthetic-evaluation.json", evaluation_data)
    _write_matching(bundle / "model-rows.jsonl", model_rows)

    runtime_manifest = {
        "schema_version": 1,
        "artifact_sha256": artifact_sha256,
        "frozen_hashes": frozen_hashes,
        "provenance": "synthetic_only",
    }
    runtime_manifest_path = bundle / "runtime-manifest.json"
    _write_matching(runtime_manifest_path, canonical_json(runtime_manifest))
    shadow = load_runtime_scorer(
        artifact_path,
        runtime_manifest_path,
        require_stage_b=False,
    ).score(
        [
            Evidence(
                family="filings_news",
                signal="synthetic_shadow_probe",
                direction=Direction.BULLISH,
                strength=0.8,
                confidence=0.8,
                source_quality=0.9,
                timestamp=datetime(2025, 6, 2, 12, tzinfo=UTC),
            )
        ],
        as_of=datetime(2025, 6, 2, 13, tzinfo=UTC),
        lookback_days=14,
        expected_families=frozenset(
            {"filings_news", "insider_trading", "options_flow", "social", "technical"}
        ),
    )
    result = {
        "schema_version": 1,
        "provenance": "synthetic_only",
        "dataset_version": version,
        "dataset_sha256": manifest["canonical_sha256"],
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "coverage_audit_record_id": audit["record_id"],
        "evaluation_record_id": evaluation["record_id"],
        "shadow_prediction": {
            "provenance": "synthetic_only",
            "score": shadow.edge.score,
            "direction": shadow.edge.direction.value,
            "confidence": shadow.edge.confidence,
        },
        "stage_b_passed": False,
        "public_scoring_method": "deterministic_v1",
        "public_model_status": "not_trained",
    }
    _write_matching(bundle / "pipeline-result.json", canonical_json(result))
    return result


def _economic_cases(rows) -> list[EconomicCase]:
    returns = {"bearish": -0.05, "neutral": 0.0, "bullish": 0.05}
    return [
        EconomicCase(
            evaluation_id=row.evaluation_id,
            security_cluster=row.event_group_id,
            date_block=row.evaluated_at.strftime("%Y-%m"),
            concentration_group=f"synthetic_{index % 6}",
            case_spy_relative_return=returns[row.label],
            control_spy_relative_return=0.0,
            calendar_days=28,
            walk_forward_fold=str(row.evaluated_at.year),
        )
        for index, row in enumerate(rows)
    ]


def _write_matching(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"existing pipeline artifact differs: {path}")
        return
    _atomic_write(path, data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()
    print(
        json.dumps(run_synthetic_pipeline(args.root, epochs=args.epochs), indent=2, sort_keys=True)
    )


if __name__ == "__main__":
    main()
