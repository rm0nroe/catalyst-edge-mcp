"""Explainable deterministic catalyst scorer."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from catalyst_edge_mcp.models import Direction, Edge, Evidence

FAMILY_WEIGHTS: dict[str, float] = {
    "filings_news": 16.0,
    "insider_trading": 12.0,
    "options_flow": 10.0,
    "technical": 6.0,
    "social": 4.0,
    "alternative": 4.0,
}
HIGH_VALUE_FAMILIES = frozenset({"filings_news", "insider_trading"})
CANONICAL_FAMILIES = frozenset(
    {"filings_news", "insider_trading", "options_flow", "technical", "social"}
)


@dataclass(frozen=True, slots=True)
class ScoringResult:
    edge: Edge
    evidence: list[Evidence]
    family_contributions: dict[str, float]


class CatalystScorer(Protocol):
    method: str
    model_status: str

    def score(
        self,
        evidence: list[Evidence],
        *,
        as_of: datetime,
        lookback_days: int,
        expected_families: set[str] | frozenset[str],
    ) -> ScoringResult: ...


class DeterministicScorer:
    """Score normalized evidence without a trained or random-weight model."""

    method = "deterministic_v1"
    model_status = "not_trained"

    def score(
        self,
        evidence: list[Evidence],
        *,
        as_of: datetime,
        lookback_days: int,
        expected_families: set[str] | frozenset[str],
    ) -> ScoringResult:
        copied = [item.model_copy(deep=True) for item in evidence]
        raw_by_family: dict[str, list[tuple[Evidence, float]]] = defaultdict(list)

        for item in copied:
            polarity = {
                Direction.BULLISH: 1.0,
                Direction.BEARISH: -1.0,
                Direction.NEUTRAL: 0.0,
            }[item.direction]
            age_days = max(0.0, (as_of - item.timestamp).total_seconds() / 86_400)
            recency = max(0.0, 1.0 - age_days / lookback_days)
            raw = polarity * item.strength * item.confidence * item.source_quality * recency
            raw_by_family[item.family].append((item, raw))

        family_contributions: dict[str, float] = {}
        for family, values in raw_by_family.items():
            raw_total = sum(raw for _, raw in values)
            bounded = max(-1.0, min(1.0, raw_total))
            family_points = bounded * FAMILY_WEIGHTS.get(family, 3.0)
            family_contributions[family] = family_points
            for item, raw in values:
                scale = family_points / raw_total if raw_total else FAMILY_WEIGHTS.get(family, 3.0)
                item.contribution = raw * scale

        observed = {item.family for item in copied}
        missing = set(expected_families) - observed
        missing_high_value = HIGH_VALUE_FAMILIES.intersection(missing)
        missing_other = missing - HIGH_VALUE_FAMILIES
        coverage_factor = max(
            0.60,
            1.0 - 0.15 * len(missing_high_value) - 0.05 * len(missing_other),
        )
        score_value = max(
            0.0,
            min(100.0, 50.0 + sum(family_contributions.values()) * coverage_factor),
        )
        rounded_score = round(score_value)
        direction = (
            Direction.BULLISH
            if rounded_score >= 55
            else Direction.BEARISH
            if rounded_score <= 45
            else Direction.NEUTRAL
        )

        confidence = self._confidence(copied, expected_families)
        edge = Edge(score=rounded_score, direction=direction, confidence=round(confidence, 4))
        return ScoringResult(edge, copied, family_contributions)

    @staticmethod
    def _confidence(
        evidence: list[Evidence], expected_families: set[str] | frozenset[str]
    ) -> float:
        if not evidence:
            return 0.0
        total_strength = sum(item.strength for item in evidence)
        quality = (
            sum(item.strength * item.confidence * item.source_quality for item in evidence)
            / total_strength
            if total_strength
            else 0.0
        )
        observed = {item.family for item in evidence}
        coverage = (
            len(observed & expected_families) / len(expected_families) if expected_families else 1.0
        )
        directional_families = {
            item.family for item in evidence if item.direction != Direction.NEUTRAL
        }
        confirmation = min(1.0, len(directional_families) / 3.0)
        return min(0.95, quality * (0.55 + 0.25 * coverage + 0.20 * confirmation))
