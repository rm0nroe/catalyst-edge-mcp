from types import SimpleNamespace

import pytest

from catalyst_edge_mcp.adapters import StaticAdapter
from catalyst_edge_mcp.models import Direction, PolicyDecision, ToolInput
from catalyst_edge_mcp.service import CatalystService
from catalyst_edge_mcp.smoke import _run, readiness_report
from tests.conftest import make_evidence, make_result


def _adapter(family, provider, item):
    return StaticAdapter(family, make_result(family, item), provider=provider)


@pytest.mark.asyncio
async def test_UT_SMOKE_REJECTS_PRIVATE_PROXY(fixed_clock):
    sec = make_evidence(
        "filings_news", "adverse", direction=Direction.BEARISH
    )
    sec.sources[0].name = "SEC EDGAR"
    sec.sources[0].source_id = "sec"
    yfinance = make_evidence("options_flow", "chain", direction=Direction.BULLISH)
    yfinance.sources[0].name = "yfinance chain snapshot"
    yfinance.sources[0].source_id = "yfinance"
    adapters = [
        _adapter("filings_news", "sec", sec),
        _adapter("options_flow", "yfinance", yfinance),
    ]
    response = await CatalystService(adapters, clock=fixed_clock).evaluate(ToolInput(ticker="NVDA"))

    report = readiness_report(response, adapters)

    assert report["sec_provenance"] is True
    assert report["fresh_directional_family"] is False
    assert report["launch_ready"] is False


@pytest.mark.asyncio
async def test_UT_SMOKE_ACCEPTS_DIRECT_SEC_INSIDER(fixed_clock):
    sec = make_evidence("filings_news", "filing", direction=Direction.NEUTRAL)
    sec.sources[0].name = "SEC EDGAR"
    sec.sources[0].source_id = "sec"
    insider = make_evidence("insider_trading", "open_market_purchase", direction=Direction.BULLISH)
    insider.sources[0].name = "SEC EDGAR"
    insider.sources[0].source_id = "sec"
    adapters = [
        _adapter("filings_news", "sec", sec),
        _adapter("insider_trading", "sec", insider),
        SimpleNamespace(provider="fmp", family="technical"),
    ]
    response = await CatalystService(adapters[:2], clock=fixed_clock).evaluate(
        ToolInput(ticker="NVDA")
    )

    report = readiness_report(response, adapters)

    assert report["fresh_directional_providers"] == ["sec"]
    assert report["launch_ready"] is True
    statuses = {item["provider"]: item for item in report["providers"]}
    assert statuses["sec"]["status"] == "fresh_evidence"
    assert statuses["sec"]["evidence_count"] == 2
    assert statuses["fmp"]["status"] == "no_fresh_evidence"


@pytest.mark.asyncio
async def test_UT_SMOKE_REQUIRES_EXPLICIT_AUTHORIZATION(fixed_clock):
    sec = make_evidence("filings_news", "filing", direction=Direction.NEUTRAL)
    sec.sources[0].source_id = "sec"
    social = make_evidence("social", "sentiment", direction=Direction.BULLISH)
    social.sources[0].source_id = "finnhub"
    response = await CatalystService(
        [_adapter("filings_news", "sec", sec), _adapter("social", "fixture", social)],
        clock=fixed_clock,
    ).evaluate(ToolInput(ticker="NVDA"))

    assert readiness_report(response, [])["launch_ready"] is False

    social.sources[0].policy_decision = PolicyDecision.APPROVED
    authorized_response = await CatalystService(
        [_adapter("filings_news", "sec", sec), _adapter("social", "fixture", social)],
        clock=fixed_clock,
    ).evaluate(ToolInput(ticker="NVDA"))
    assert readiness_report(authorized_response, [])["launch_ready"] is True


@pytest.mark.asyncio
async def test_smoke_preflight_makes_no_provider_calls_when_environment_is_missing(
    monkeypatch, capsys
):
    from catalyst_edge_mcp import smoke

    for name in (
        "CATALYST_EDGE_SEC_USER_AGENT",
        "FMP_API_KEY",
        "FINNHUB_API_KEY",
        "FLOWALGO_API_KEY",
        "CHEDDARFLOW_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    def fail_if_called(settings):
        raise AssertionError("provider composition must not happen before configuration passes")

    monkeypatch.setattr(smoke, "build_service", fail_if_called)

    assert await _run("nvda", 14) == 2
    output = capsys.readouterr().out
    assert '"configuration_ready": false' in output
    assert '"launch_ready": false' in output
