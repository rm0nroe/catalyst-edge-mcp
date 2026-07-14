import json
from pathlib import Path

import pytest

from catalyst_edge_mcp.adapters import StaticAdapter
from catalyst_edge_mcp.models import (
    AdapterResult,
    Direction,
    PolicyDecision,
    SourceStatus,
    ToolInput,
)
from catalyst_edge_mcp.service import CatalystService
from catalyst_edge_mcp.source_policy import SOURCE_POLICIES, get_source_policy
from tests.conftest import make_evidence


def test_UT_SOURCE_POLICY_fixture_matches_fail_closed_registry():
    fixture_path = Path(__file__).parents[1] / "fixtures" / "source_policies" / "decisions.json"
    expected = json.loads(fixture_path.read_text())

    assert {key: SOURCE_POLICIES[key].decision.value for key in expected} == expected
    assert get_source_policy("sec").production_allowed is True
    with pytest.raises(ValueError, match="not reviewed"):
        get_source_policy("unknown_vendor")


def test_PT_GDELT_THROTTLE_contract_is_serialized_one_per_five_seconds():
    policy = get_source_policy("gdelt")

    assert policy.requests_per_second == 0.2
    assert policy.concurrency == 1
    assert policy.retention == "publisher metadata and links only"


def test_PT_BLUESKY_HOST_FALLBACK_uses_only_documented_official_hosts():
    policy = get_source_policy("bluesky")

    assert policy.official_hosts == ("public.api.bsky.app", "api.bsky.app")
    assert policy.decision == PolicyDecision.APPROVED_PARTIAL_ATTENTION


@pytest.mark.asyncio
async def test_PT_PERMISSION_REQUIRED_blocks_vendor_evidence(fixed_clock):
    evidence = make_evidence("social", "sentiment", direction=Direction.BULLISH)
    result = AdapterResult(
        family="social",
        provider="finnhub",
        evidence=[evidence],
        policy_decision=PolicyDecision.PERMISSION_REQUIRED,
    )
    response = await CatalystService(
        [StaticAdapter("social", result, provider="finnhub")], clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA"))

    assert response.edge.score == 50
    assert response.evidence == []
    status = next(item for item in response.data_quality.family_statuses if item.family == "social")
    assert status.status == SourceStatus.PERMISSION_REQUIRED
    assert status.available is False


@pytest.mark.asyncio
async def test_FX_LICENSED_FEED_REQUIRED_is_explicit_for_options(fixed_clock):
    response = await CatalystService(clock=fixed_clock).evaluate(ToolInput(ticker="NVDA"))
    status = next(
        item for item in response.data_quality.family_statuses if item.family == "options_flow"
    )

    assert status.status == SourceStatus.LICENSED_FEED_REQUIRED
    assert status.reason == "licensed_transaction_feed_required"
    assert status.available is False


@pytest.mark.asyncio
async def test_FX_OPTIONS_UNLICENSED_NEUTRAL_yfinance_gets_no_credit(fixed_clock):
    evidence = make_evidence("options_flow", "chain_activity", direction=Direction.BULLISH)
    result = AdapterResult(
        family="options_flow",
        provider="yfinance",
        evidence=[evidence],
        degraded=True,
        policy_decision=PolicyDecision.DEVELOPMENT_PRIVATE_ONLY,
    )
    response = await CatalystService(
        [StaticAdapter("options_flow", result, provider="yfinance")], clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA"))

    assert response.edge.score == 50
    assert response.edge.direction == Direction.NEUTRAL
    assert response.evidence == []
    assert "options_flow" in response.data_quality.missing_families


@pytest.mark.asyncio
async def test_FX_SOCIAL_ATTENTION_NEUTRAL_does_not_invent_sentiment(fixed_clock):
    attention = make_evidence("social", "attention_increase", direction=Direction.NEUTRAL)
    response = await CatalystService(
        [StaticAdapter("social", AdapterResult(family="social", evidence=[attention]))],
        clock=fixed_clock,
    ).evaluate(ToolInput(ticker="NVDA"))

    assert response.edge.score == 50
    assert response.edge.direction == Direction.NEUTRAL
    assert response.evidence[0].direction == Direction.NEUTRAL
