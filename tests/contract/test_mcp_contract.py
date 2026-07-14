import os
import socket
import subprocess
import time
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from pydantic import ValidationError

from catalyst_edge_mcp.models import CatalystEdgeResponse, ToolInput
from catalyst_edge_mcp.server import catalyst_edge_score, mcp

TRANSPORTS = ("stdio", "streamable-http")
INVALID_ARGUMENTS = (
    {"ticker": "NVDA", "bogus": 1},
    {"ticker": "NVDA", "lookback_days": "7"},
    {"ticker": "NVDA", "include_sources": "false"},
)
POPULATED_EVIDENCE_SERVER = Path(__file__).with_name("populated_evidence_server.py")
HTTP_START_ATTEMPTS = 3
HTTP_START_TIMEOUT_SECONDS = 30


def _offline_server_env(**overrides):
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("CATALYST_EDGE_")
    }
    environment["CATALYST_EDGE_ISSUER_FEEDS"] = "disabled"
    environment["CATALYST_EDGE_GDELT"] = "disabled"
    environment["CATALYST_EDGE_BLUESKY"] = "disabled"
    environment.update(overrides)
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


def _validated_response(result, *, output_schema=None):
    assert result.isError is False
    payload = result.structuredContent
    if set(payload or {}) == {"result"}:
        payload = payload["result"]
    if output_schema is not None:
        Draft202012Validator(output_schema).validate(payload)
    assert all(item["source_count"] == len(item["sources"]) for item in payload["evidence"])
    validation_payload = deepcopy(payload)
    for item in validation_payload["evidence"]:
        item.pop("source_count")
    return CatalystEdgeResponse.model_validate(validation_payload)


def _assert_empty_structured_response(result):
    response = _validated_response(result)
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


def _server_command(*, populated_evidence):
    if populated_evidence:
        return ["uv", "run", "python", str(POPULATED_EVIDENCE_SERVER)]
    return ["uv", "run", "catalyst-edge-mcp"]


def _ephemeral_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _terminate_process(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _wait_for_http_server(process, port):
    deadline = time.monotonic() + HTTP_START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return process.stderr.read()
        try:
            httpx.get(f"http://127.0.0.1:{port}/mcp", timeout=0.2)
            return None
        except httpx.TransportError:
            time.sleep(0.05)
    _terminate_process(process)
    stderr = process.stderr.read()
    return f"readiness timeout after {HTTP_START_TIMEOUT_SECONDS}s\n{stderr}"


def _is_bind_collision(stderr):
    message = stderr.lower()
    return "address already in use" in message or "errno 48" in message


@asynccontextmanager
async def _transport_session(transport, *, populated_evidence=False):
    command = _server_command(populated_evidence=populated_evidence)
    if transport == "stdio":
        parameters = StdioServerParameters(
            command=command[0],
            args=command[1:],
            env=_offline_server_env(CATALYST_EDGE_TRANSPORT="stdio"),
        )
        async with (
            stdio_client(parameters) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            yield session
        return

    last_error = ""
    for attempt in range(HTTP_START_ATTEMPTS):
        port = _ephemeral_port()
        environment = _offline_server_env(
            CATALYST_EDGE_TRANSPORT="streamable-http",
            CATALYST_EDGE_HOST="127.0.0.1",
            CATALYST_EDGE_PORT=str(port),
        )
        process = subprocess.Popen(
            command,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            startup_error = _wait_for_http_server(process, port)
            if startup_error is not None:
                last_error = startup_error
                if _is_bind_collision(startup_error) and attempt + 1 < HTTP_START_ATTEMPTS:
                    continue
                pytest.fail(f"HTTP server did not start:\n{startup_error}")
            async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
                read_stream, write_stream, _ = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
            return
        finally:
            _terminate_process(process)
    pytest.fail(f"HTTP server could not bind after {HTTP_START_ATTEMPTS} attempts:\n{last_error}")


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


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.asyncio
async def test_CT_TRANSPORT_REJECTS_UNKNOWN_AND_COERCED_INPUTS(transport):
    async with _transport_session(transport) as session:
        for arguments in INVALID_ARGUMENTS:
            result = await session.call_tool("catalyst_edge_score", arguments)
            assert result.isError is True
            assert result.structuredContent is None


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.asyncio
async def test_CT_TRANSPORT_SERIALIZES_POPULATED_EVIDENCE(transport):
    async with _transport_session(transport, populated_evidence=True) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        result = await session.call_tool("catalyst_edge_score", {"ticker": "NVDA"})

    response = _validated_response(
        result,
        output_schema=tools["catalyst_edge_score"].outputSchema,
    )
    assert len(response.evidence) == 1
    assert len(response.evidence[0].sources) == 1


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
    async with _transport_session("stdio") as session:
        tools = await session.list_tools()
    assert [tool.name for tool in tools.tools] == ["catalyst_edge_score"]


@pytest.mark.asyncio
async def test_CT_STDIO_INVOCATION():
    async with _transport_session("stdio") as session:
        result = await session.call_tool("catalyst_edge_score", {"ticker": " nvda "})
    _assert_empty_structured_response(result)


@pytest.mark.asyncio
async def test_CT_HTTP_DISCOVERY():
    async with _transport_session("streamable-http") as session:
        tools = await session.list_tools()
    assert [tool.name for tool in tools.tools] == ["catalyst_edge_score"]


@pytest.mark.asyncio
async def test_CT_HTTP_INVOCATION():
    async with _transport_session("streamable-http") as session:
        result = await session.call_tool("catalyst_edge_score", {"ticker": " nvda "})
    _assert_empty_structured_response(result)
