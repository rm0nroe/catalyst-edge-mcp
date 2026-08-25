import pytest

from catalyst_edge_mcp.models import Direction, EvidenceContext, ResearchDisposition
from catalyst_edge_mcp.research import build_research_assessment
from tests.conftest import make_evidence


def claim_evidence(
    claim_character: str,
    *,
    direction: Direction = Direction.BULLISH,
    confidence: float = 0.9,
    materiality: str = "material",
    contribution: float = 1.0,
):
    item = make_evidence(
        "filings_news",
        f"claim_{claim_character}",
        direction=direction,
        confidence=confidence,
    )
    item.contribution = contribution
    item.context = EvidenceContext(
        event_type="material_filing",
        event_label=f"Claim {claim_character}",
        novelty="new",
        materiality=materiality,
        why_it_matters="The filing changes the current research record.",
        claim_id=f"clm_{claim_character * 64}",
    )
    return item


def test_empty_evidence_is_insufficient_with_stable_gaps():
    result = build_research_assessment(
        [],
        missing_families={"technical", "filings_news"},
        stale_families={"technical"},
        checks=["Retry with lookback_days=30 to check a wider filing window."],
    )

    assert result.disposition == ResearchDisposition.INSUFFICIENT_EVIDENCE
    assert result.primary_claim_id is None
    assert result.supporting_claim_ids == []
    assert result.contradicting_claim_ids == []
    assert result.blocking_gaps == ["filings_news", "technical"]
    assert result.next_action == "Retry with lookback_days=30 to check a wider filing window."


@pytest.mark.parametrize(
    ("direction", "confidence", "materiality", "with_source"),
    [
        (Direction.NEUTRAL, 0.9, "material", True),
        (Direction.BULLISH, 0.49, "material", True),
        (Direction.BULLISH, 0.9, "discovery_only", True),
        (Direction.BULLISH, 0.9, "not_material", True),
        (Direction.BULLISH, 0.9, "material", False),
    ],
)
def test_non_reviewable_primary_is_monitor(direction, confidence, materiality, with_source):
    item = claim_evidence(
        "a",
        direction=direction,
        confidence=confidence,
        materiality=materiality,
    )
    if not with_source:
        item.sources = []

    result = build_research_assessment(
        [item],
        missing_families=set(),
        stale_families=set(),
        checks=["Fallback check."],
    )

    assert result.disposition == ResearchDisposition.MONITOR


def test_review_now_ranks_and_deduplicates_canonical_claims():
    primary = claim_evidence("a", contribution=8, direction=Direction.BULLISH)
    supporting = claim_evidence("b", contribution=4, direction=Direction.BULLISH)
    supporting_duplicate = supporting.model_copy(deep=True)
    contradiction = claim_evidence("c", contribution=-3, direction=Direction.BEARISH)

    result = build_research_assessment(
        [contradiction, supporting_duplicate, primary, supporting],
        missing_families={"options_flow"},
        stale_families=set(),
        checks=["Fallback check."],
    )

    assert result.disposition == ResearchDisposition.REVIEW_NOW
    assert result.primary_claim_id == primary.context.claim_id
    assert result.supporting_claim_ids == [supporting.context.claim_id]
    assert result.contradicting_claim_ids == [contradiction.context.claim_id]
    assert result.blocking_gaps == ["options_flow"]
