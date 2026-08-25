"""Deterministic per-ticker research assessment."""

from __future__ import annotations

from catalyst_edge_mcp.models import (
    Direction,
    Evidence,
    ResearchAssessment,
    ResearchDisposition,
)
from catalyst_edge_mcp.summary import evidence_check


def _claim_id(item: Evidence) -> str | None:
    return item.context.claim_id if item.context else None


def _identity(item: Evidence) -> tuple[str, str, str, str]:
    source_record = (
        item.sources[0].accession_or_record_id
        if item.sources and item.sources[0].accession_or_record_id
        else ""
    )
    return (_claim_id(item) or "", item.family, item.signal, source_record)


def _rank(evidence: list[Evidence]) -> list[Evidence]:
    return sorted(
        evidence,
        key=lambda item: (-abs(item.contribution), -item.timestamp.timestamp(), _identity(item)),
    )


def _reviewable(item: Evidence) -> bool:
    materiality = item.context.materiality if item.context else None
    return (
        item.direction != Direction.NEUTRAL
        and item.confidence >= 0.50
        and materiality not in {"discovery_only", "not_material"}
        and bool(item.sources)
    )


def build_research_assessment(
    evidence: list[Evidence],
    *,
    missing_families: set[str],
    stale_families: set[str],
    checks: list[str],
) -> ResearchAssessment:
    gaps = sorted(missing_families | stale_families)
    if not evidence:
        return ResearchAssessment(
            disposition=ResearchDisposition.INSUFFICIENT_EVIDENCE,
            blocking_gaps=gaps,
            next_action=checks[0],
        )

    ranked = _rank(evidence)
    primary = ranked[0]
    primary_claim_id = _claim_id(primary)
    supporting: list[str] = []
    contradicting: list[str] = []
    seen = {primary_claim_id} if primary_claim_id else set()
    if primary.direction != Direction.NEUTRAL:
        for item in ranked:
            claim_id = _claim_id(item)
            if not claim_id or claim_id in seen:
                continue
            seen.add(claim_id)
            if item.direction == primary.direction:
                supporting.append(claim_id)
            elif item.direction != Direction.NEUTRAL:
                contradicting.append(claim_id)

    return ResearchAssessment(
        disposition=(
            ResearchDisposition.REVIEW_NOW
            if _reviewable(primary)
            else ResearchDisposition.MONITOR
        ),
        primary_claim_id=primary_claim_id,
        supporting_claim_ids=supporting,
        contradicting_claim_ids=contradicting,
        blocking_gaps=gaps,
        next_action=evidence_check(primary) or checks[0],
    )
