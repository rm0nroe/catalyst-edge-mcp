import asyncio
import logging

import pytest

from catalyst_edge_mcp.models import RiskMode
from catalyst_edge_mcp.server import catalyst_edge_score, mcp
from catalyst_edge_mcp.settings import Settings
from tests.conftest import AS_OF


def test_provider_http_logs_cannot_emit_credential_bearing_urls():
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING


@pytest.mark.asyncio
async def test_exported_tool_returns_contract(monkeypatch):
    from catalyst_edge_mcp import server
    from catalyst_edge_mcp.service import CatalystService

    monkeypatch.setattr(server, "_service", CatalystService(clock=lambda: AS_OF))
    response = await catalyst_edge_score("nvda", risk_mode=RiskMode.RESEARCH)

    assert response.ticker == "NVDA"
    assert response.edge.scoring_method == "deterministic_v1"
    assert response.edge.model_status == "not_trained"


@pytest.mark.asyncio
async def test_exported_tool_reuses_process_service(monkeypatch):
    from catalyst_edge_mcp import server

    calls = 0

    class RecordingService:
        async def evaluate(self, request):
            nonlocal calls
            calls += 1
            return await server.CatalystService(clock=lambda: AS_OF).evaluate(request)

    service = RecordingService()
    monkeypatch.setattr(server, "_service", service)

    await catalyst_edge_score("NVDA")
    await catalyst_edge_score("AAPL")

    assert calls == 2
    assert server._service is service


@pytest.mark.asyncio
async def test_fastmcp_registers_expected_tool():
    tools = await mcp.list_tools()
    registered = {tool.name: tool for tool in tools}

    assert "catalyst_edge_score" in registered
    schema = registered["catalyst_edge_score"].inputSchema
    assert schema["properties"]["lookback_days"]["default"] == 14
    assert schema["properties"]["include_raw_signals"]["default"] is False


def test_build_service_defaults_to_sec_only_when_identity_is_declared(monkeypatch):
    from catalyst_edge_mcp.server import build_service

    monkeypatch.delenv("CATALYST_EDGE_SEC_USER_AGENT", raising=False)
    assert build_service(Settings.from_env()).adapters == ()

    monkeypatch.setenv("CATALYST_EDGE_SEC_USER_AGENT", "Catalyst Edge ops@example.com")
    configured = build_service(Settings.from_env())
    assert [adapter.provider for adapter in configured.adapters] == ["sec", "sec", "sec_funds"]
    assert {adapter.family for adapter in configured.adapters} == {
        "filings_news",
        "insider_trading",
    }

    monkeypatch.setenv("CATALYST_EDGE_ISSUER_FEEDS", "enabled")
    monkeypatch.setenv("CATALYST_EDGE_GDELT", "enabled")
    monkeypatch.setenv("CATALYST_EDGE_BLUESKY", "enabled")
    extensions_enabled = build_service(Settings.from_env())
    assert [adapter.provider for adapter in extensions_enabled.adapters] == [
        "sec",
        "sec",
        "sec_funds",
        "issuer_feed",
        "gdelt",
        "bluesky",
    ]
    assert {adapter.family for adapter in extensions_enabled.adapters} == {
        "filings_news",
        "insider_trading",
        "social",
    }
    gdelt = next(
        adapter for adapter in extensions_enabled.adapters if adapter.provider == "gdelt"
    )
    assert gdelt.live_refresh is False

    monkeypatch.setenv("CATALYST_EDGE_ISSUER_FEEDS", "disabled")
    disabled = build_service(Settings.from_env())
    assert [adapter.provider for adapter in disabled.adapters] == [
        "sec",
        "sec",
        "sec_funds",
        "gdelt",
        "bluesky",
    ]

    monkeypatch.setenv("CATALYST_EDGE_GDELT", "disabled")
    fully_disabled = build_service(Settings.from_env())
    assert [adapter.provider for adapter in fully_disabled.adapters] == [
        "sec",
        "sec",
        "sec_funds",
        "bluesky",
    ]

    monkeypatch.setenv("CATALYST_EDGE_BLUESKY", "disabled")
    no_network_extensions = build_service(Settings.from_env())
    assert [adapter.provider for adapter in no_network_extensions.adapters] == [
        "sec",
        "sec",
        "sec_funds",
    ]


def test_main_treats_operator_cancellation_as_clean_shutdown(monkeypatch):
    from catalyst_edge_mcp import server

    def cancel(*, transport):
        raise asyncio.CancelledError

    monkeypatch.setattr(server.mcp, "run", cancel)

    server.main()


@pytest.mark.asyncio
async def test_server_lifespan_starts_and_stops_collection_lifecycle(monkeypatch):
    from catalyst_edge_mcp import server

    calls = []

    class RecordingLifecycle:
        def start(self):
            calls.append("start")

        async def stop(self):
            calls.append("stop")

    lifecycle = RecordingLifecycle()
    monkeypatch.setattr(server, "build_collection_lifecycle", lambda settings: lifecycle)

    async with server.server_lifespan(None) as context:
        assert calls == ["start"]
        assert context["collection_lifecycle"] is lifecycle

    assert calls == ["start", "stop"]


@pytest.mark.parametrize("provider", ["flowalgo", "cheddarflow", "yfinance"])
def test_build_service_never_composes_unentitled_options_provider(provider):
    from catalyst_edge_mcp.server import build_service

    settings = Settings(
        options_provider=provider,
        flowalgo_api_key="fixture-key",
        cheddarflow_api_key="fixture-key",
        issuer_feeds_enabled=False,
        gdelt_enabled=False,
        bluesky_enabled=False,
    )

    assert build_service(settings).adapters == ()
