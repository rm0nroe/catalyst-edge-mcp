import os
import socket
import subprocess
import time
from copy import deepcopy

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from pydantic import ValidationError

from catalyst_edge_mcp.models import CatalystEdgeResponse, ToolInput
from catalyst_edge_mcp.server import catalyst_edge_score, mcp


def _offline_server_env(**overrides):
    environment = {**os.environ, **overrides}
    environment["CATALYST_EDGE_ISSUER_FEEDS"] = "disabled"
    environment["CATALYST_EDGE_GDELT"] = "disabled"
    environment["CATALYST_EDGE_BLUESKY"] = "disabled"
    for name in (
        "CATALYST_EDGE_SEC_USER_AGENT",
        "FMP_API_KEY",
        "FINNHUB_API_KEY",
        "FLOWALGO_API_KEY",
        "CHEDDARFLOW_API_KEY",
    ):
        environment.pop(name, None)
    stub_path = os.path.abspath("tests/stubs")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (stub_path, environment.get("PYTHONPATH")) if part
    )
    return environment


def _assert_structured_response(result):
    assert result.isError is False
    payload = result.structuredContent
    if set(payload or {}) == {"result"}:
        payload = payload["result"]
    assert all(item["source_count"] == len(item["sources"]) for item in payload["evidence"])
    validation_payload = deepcopy(payload)
    for item in validation_payload["evidence"]:
        item.pop("source_count")
    response = CatalystEdgeResponse.model_validate(validation_payload)
    assert response.ticker == "NVDA"
    assert response.lookback_days == 14
    assert response.edge.scoring_method == "deterministic_v1"
    assert response.edge.model_status == "not_trained"
    assert response.data_quality.coverage == "none"
    assert set(response.data_quality.missing_families) == {
        "filings_news",
        "insider_trading",
        "options_flow",
        "technical",
        "social",
    }
    assert response.evidence == []
    statuses = {item.family: item for item in response.data_quality.family_statuses}
    assert statuses["options_flow"].reason == "licensed_transaction_feed_required"
    assert statuses["technical"].reason == "licensed_ohlc_feed_required"
    return response


@pytest.mark.asyncio
async def test_CT_DISCOVERY():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    tool = tools["catalyst_edge_score"]
    assert tool.name == "catalyst_edge_score"


@pytest.mark.asyncio
async def test_CT_INPUT_SCHEMA():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    tool = tools["catalyst_edge_score"]
    assert tool.inputSchema["properties"]["ticker"]["type"] == "string"
    assert tool.inputSchema["properties"]["lookback_days"]["default"] == 14
    assert set(tool.inputSchema["$defs"]["RiskMode"]["enum"]) == {
        "research",
        "alert_triage",
        "thesis_review",
    }
    assert tool.inputSchema["additionalProperties"] is False
    assert tool.inputSchema["properties"]["lookback_days"]["minimum"] == 1
    assert tool.inputSchema["properties"]["lookback_days"]["maximum"] == 90


@pytest.mark.asyncio
async def test_CT_RESPONSE_SCHEMA():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    tool = tools["catalyst_edge_score"]
    assert tool.outputSchema["required"] == [
        "ticker",
        "as_of",
        "lookback_days",
        "edge",
        "summary",
        "evidence",
        "data_quality",
        "next_checks",
    ]
    assert "source_count" in tool.outputSchema["$defs"]["Evidence"]["required"]


def test_CT_INPUT_SCHEMA_REJECTS_UNKNOWN():
    schema = ToolInput.model_json_schema()
    assert schema["additionalProperties"] is False
    with pytest.raises(ValidationError):
        ToolInput.model_validate({"ticker": "NVDA", "other": 1})


@pytest.mark.asyncio
async def test_UT_INPUT_VALIDATION_PRECEDES_COMPOSITION(monkeypatch):
    from catalyst_edge_mcp import server

    called = False

    def fail_if_called(settings):
        nonlocal called
        called = True
        raise AssertionError("composition must not happen")

    monkeypatch.setattr(server, "build_service", fail_if_called)
    with pytest.raises(ValidationError):
        await catalyst_edge_score("bad/ticker")
    assert called is False


@pytest.mark.asyncio
async def test_CT_STDIO_DISCOVERY():
    parameters = StdioServerParameters(
        command="uv",
        args=["run", "catalyst-edge-mcp"],
        env=_offline_server_env(CATALYST_EDGE_TRANSPORT="stdio"),
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
    assert [tool.name for tool in tools.tools] == ["catalyst_edge_score"]


@pytest.mark.asyncio
async def test_CT_STDIO_INVOCATION():
    parameters = StdioServerParameters(
        command="uv",
        args=["run", "catalyst-edge-mcp"],
        env=_offline_server_env(CATALYST_EDGE_TRANSPORT="stdio"),
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        result = await session.call_tool("catalyst_edge_score", {"ticker": " nvda "})
    _assert_structured_response(result)


@pytest.mark.asyncio
async def test_CT_HTTP_DISCOVERY():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = _offline_server_env(
        CATALYST_EDGE_TRANSPORT="streamable-http",
        CATALYST_EDGE_HOST="127.0.0.1",
        CATALYST_EDGE_PORT=str(port),
    )
    process = subprocess.Popen(
        ["uv", "run", "catalyst-edge-mcp"],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(f"HTTP server exited: {process.stderr.read()}")
            try:
                httpx.get(f"http://127.0.0.1:{port}/mcp", timeout=0.2)
                break
            except httpx.TransportError:
                time.sleep(0.05)
        else:
            pytest.fail("HTTP server did not start")
        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
            read_stream, write_stream, _ = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
        assert [tool.name for tool in tools.tools] == ["catalyst_edge_score"]
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.mark.asyncio
async def test_CT_HTTP_INVOCATION():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = _offline_server_env(
        CATALYST_EDGE_TRANSPORT="streamable-http",
        CATALYST_EDGE_HOST="127.0.0.1",
        CATALYST_EDGE_PORT=str(port),
    )
    process = subprocess.Popen(
        ["uv", "run", "catalyst-edge-mcp"],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(f"HTTP server exited: {process.stderr.read()}")
            try:
                httpx.get(f"http://127.0.0.1:{port}/mcp", timeout=0.2)
                break
            except httpx.TransportError:
                time.sleep(0.05)
        else:
            pytest.fail("HTTP server did not start")
        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
            read_stream, write_stream, _ = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("catalyst_edge_score", {"ticker": " nvda "})
        _assert_structured_response(result)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
