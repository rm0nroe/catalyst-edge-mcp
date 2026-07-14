from datetime import timedelta

import pytest

from catalyst_edge_mcp.models import Direction
from catalyst_edge_mcp.scorer import DeterministicScorer
from tests.conftest import AS_OF, make_evidence


def test_exact_single_family_scoring_math():
    evidence = make_evidence(
        "options_flow",
        "unusual_call_activity",
        strength=0.8,
        confidence=0.5,
        source_quality=0.5,
    )

    result = DeterministicScorer().score(
        [evidence], as_of=AS_OF, lookback_days=14, expected_families={"options_flow"}
    )

    # 50 + (10 * .8 * .5 * .5) = 52; no high-value coverage penalty.
    assert result.edge.score == 52
    assert result.edge.direction == Direction.NEUTRAL
    assert result.family_contributions["options_flow"] == pytest.approx(2.0)
    assert result.evidence[0].contribution == pytest.approx(2.0)


def test_missing_high_value_family_neutralizes_delta_not_directionally_penalizes():
    evidence = make_evidence(
        "options_flow",
        "large_put_activity",
        direction=Direction.BEARISH,
        strength=1,
        confidence=1,
        source_quality=1,
    )

    result = DeterministicScorer().score(
        [evidence],
        as_of=AS_OF,
        lookback_days=14,
        expected_families={"options_flow", "filings_news"},
    )

    assert result.edge.score == 42  # 50 - 10 * .85, rounded with Python semantics.
    assert result.edge.direction == Direction.BEARISH


def test_recency_reduces_contribution():
    evidence = make_evidence(
        "filings_news",
        "material_filing",
        strength=1,
        confidence=1,
        source_quality=1,
        timestamp=AS_OF - timedelta(days=7),
    )
    result = DeterministicScorer().score(
        [evidence], as_of=AS_OF, lookback_days=14, expected_families={"filings_news"}
    )

    assert result.edge.score == 58
    assert result.evidence[0].contribution == pytest.approx(8.0)


def test_family_contribution_is_bounded_and_item_attribution_sums():
    items = [
        make_evidence("social", f"signal_{index}", strength=1, confidence=1, source_quality=1)
        for index in range(3)
    ]
    result = DeterministicScorer().score(
        items, as_of=AS_OF, lookback_days=14, expected_families={"social"}
    )

    assert result.family_contributions["social"] == 4
    assert sum(item.contribution for item in result.evidence) == pytest.approx(4, abs=0.001)


def test_no_data_is_neutral_with_zero_confidence():
    result = DeterministicScorer().score(
        [], as_of=AS_OF, lookback_days=14, expected_families={"filings_news"}
    )

    assert result.edge.score == 50
    assert result.edge.direction == Direction.NEUTRAL
    assert result.edge.confidence == 0
    assert result.edge.scoring_method == "deterministic_v1"
    assert result.edge.model_status == "not_trained"
