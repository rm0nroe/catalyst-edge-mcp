"""Fail-closed runtime loader and scorer for shadow or promoted artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from catalyst_edge_mcp.models import Direction, Edge, Evidence
from catalyst_edge_mcp.replay.model import ModelArtifact, extract_features, load_artifact
from catalyst_edge_mcp.scorer import DeterministicScorer, ScoringResult


class TrainedSoftmaxScorer:
    method = "trained_softmax"

    def __init__(self, artifact: ModelArtifact, *, shadow_only: bool) -> None:
        self.artifact = artifact
        self.shadow_only = shadow_only
        self.model_status = "shadow_only" if shadow_only else "trained"

    def score(
        self,
        evidence: list[Evidence],
        *,
        as_of,
        lookback_days: int,
        expected_families: set[str] | frozenset[str],
    ) -> ScoringResult:
        deterministic = DeterministicScorer().score(
            evidence,
            as_of=as_of,
            lookback_days=lookback_days,
            expected_families=expected_families,
        )
        prediction = self.artifact.predict(
            extract_features(evidence, as_of=as_of, lookback_days=lookback_days)
        )
        edge = Edge(
            score=prediction["score"],
            direction=Direction(prediction["direction"]),
            confidence=prediction["confidence"],
            scoring_method=self.method,
            model_status=self.model_status,
        )
        return ScoringResult(edge, deterministic.evidence, deterministic.family_contributions)


def load_runtime_scorer(
    artifact_path: Path,
    manifest_path: Path,
    *,
    require_stage_b: bool,
) -> TrainedSoftmaxScorer:
    artifact_data = artifact_path.read_bytes()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("model runtime manifest is invalid JSON") from exc
    required = {"schema_version", "artifact_sha256", "frozen_hashes", "provenance"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError("model runtime manifest has an invalid schema")
    if manifest["schema_version"] != 1:
        raise ValueError("model runtime manifest version is unsupported")
    if manifest["artifact_sha256"] != hashlib.sha256(artifact_data).hexdigest():
        raise ValueError("model runtime artifact hash does not match")
    artifact = load_artifact(
        artifact_data,
        require_stage_b=require_stage_b,
        expected_hashes=manifest["frozen_hashes"],
    )
    if artifact.provenance != manifest["provenance"]:
        raise ValueError("model runtime provenance does not match")
    return TrainedSoftmaxScorer(artifact, shadow_only=not require_stage_b)
