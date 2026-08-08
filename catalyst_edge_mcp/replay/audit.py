"""Coverage and Stage B measurements derived from canonical replay records."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

from catalyst_edge_mcp.replay.contracts import (
    MODEL_EVIDENCE_FAMILIES,
    canonical_json,
    dataset_version,
    stable_id,
)


def audit_dataset(spec: dict[str, Any], dataset: bytes, manifest: dict[str, Any]) -> bytes:
    records = [json.loads(line) for line in dataset.splitlines()]
    provenance = str(spec["provenance"])
    version = dataset_version(spec)
    dataset_sha256 = hashlib.sha256(dataset).hexdigest()
    critical_errors = []
    if manifest.get("provenance") != provenance:
        critical_errors.append("manifest_provenance_mismatch")
    if manifest.get("dataset_version") != version:
        critical_errors.append("manifest_dataset_version_mismatch")
    if manifest.get("canonical_sha256") != dataset_sha256:
        critical_errors.append("manifest_dataset_sha256_mismatch")
    if any(record.get("provenance") != provenance for record in records):
        critical_errors.append("record_provenance_mismatch")

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_type[str(record.get("record_type"))].append(record)
    observations = {record["record_id"]: record for record in by_type["observation"]}
    labels = {record["evaluation_id"]: record for record in by_type["label"]}
    evaluations = by_type["evaluation"]
    eligible_evaluations = [row for row in evaluations if row["record_id"] in labels]
    family_cells = 0
    covered_cells = 0
    for evaluation in eligible_evaluations:
        present = {
            observations[identifier]["evidence_snapshot"]["family"]
            for identifier in evaluation["observation_ids"]
        }
        family_cells += len(MODEL_EVIDENCE_FAMILIES)
        covered_cells += len(present & MODEL_EVIDENCE_FAMILIES)

    ticker_securities: dict[str, set[str]] = defaultdict(set)
    for action in by_type["action"]:
        if ticker := action.get("ticker"):
            ticker_securities[str(ticker)].add(str(action["security_id"]))
    class_counts = Counter(str(label["class"]) for label in labels.values())
    years = sorted({int(row["evaluation_at"][:4]) for row in evaluations})
    terminal_statuses = sorted({str(row["status"]) for row in by_type["terminal_outcome"]})
    action_types = sorted({str(row["action_type"]) for row in by_type["action"]})
    exclusion_reasons = Counter(str(row["reason"]) for row in by_type["exclusion"])
    untouched_cases = sum(
        2024 <= int(row["evaluation_at"][:4]) <= 2025 for row in eligible_evaluations
    )
    measurements = {
        "provenance": provenance,
        "record_counts": {name: len(values) for name, values in sorted(by_type.items())},
        "valid_cases": len(labels),
        "untouched_cases": untouched_cases,
        "years": years,
        "class_counts": dict(sorted(class_counts.items())),
        "correction_versions": sum(
            row["correction_of_observation_id"] is not None for row in by_type["observation"]
        ),
        "control_cases": sum(row.get("case_type") == "control" for row in evaluations),
        "action_types": action_types,
        "terminal_statuses": terminal_statuses,
        "exclusion_reasons": dict(sorted(exclusion_reasons.items())),
        "ticker_reuse": sorted(
            ticker for ticker, securities in ticker_securities.items() if len(securities) > 1
        ),
        "claimed_family_cells": family_cells,
        "covered_family_cells": covered_cells,
        "claimed_family_evaluability": round(covered_cells / family_cells, 12)
        if family_cells
        else 0.0,
    }
    engineering_gate = (
        not critical_errors
        and years == list(range(2018, 2026))
        and set(class_counts) == {"bearish", "neutral", "bullish"}
        and measurements["correction_versions"] > 0
        and measurements["control_cases"] > 0
        and {"split", "cash_dividend", "ticker_start", "ticker_end"}.issubset(action_types)
        and {"bankrupt", "delisted", "acquired", "inactive"}.issubset(terminal_statuses)
        and bool(measurements["ticker_reuse"])
        and {
            "label_window_crosses_fold",
            "fold_embargo",
            "insufficient_forward_sessions",
        }.issubset(exclusion_reasons)
    )
    stage_b_gate = {
        "provenance": provenance,
        "minimum_valid_cases": len(labels) >= 1_000,
        "minimum_untouched_cases": untouched_cases >= 250,
        "claimed_family_evaluability": measurements["claimed_family_evaluability"] >= 0.95,
        "zero_critical_errors": not critical_errors,
        "rights_cleared_market": provenance == "rights_cleared_market",
    }
    result = {
        "schema_version": 1,
        "record_type": "dataset_audit",
        "provenance": provenance,
        "dataset_version": version,
        "dataset_sha256": dataset_sha256,
        "measurements": measurements,
        "critical_errors": critical_errors,
        "engineering_gate_passed": engineering_gate,
        "stage_b_gate": stage_b_gate,
        "stage_b_passed": all(stage_b_gate.values()),
    }
    result["record_id"] = stable_id("ceaudit", hashlib.sha256(canonical_json(result)).hexdigest())
    return canonical_json(result)
