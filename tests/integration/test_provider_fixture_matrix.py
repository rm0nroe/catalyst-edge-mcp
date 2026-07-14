import json
from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.adapters.finnhub import FinnhubLobbyingAdapter, FinnhubSocialAdapter
from catalyst_edge_mcp.adapters.fmp import FmpInsiderAdapter, FmpNewsAdapter, FmpTechnicalAdapter
from catalyst_edge_mcp.adapters.options import (
    CheddarFlowAdapter,
    FlowAlgoAdapter,
    YFinanceOptionsAdapter,
)
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from tests.conftest import AS_OF

FIXTURES = Path(__file__).parents[1] / "fixtures" / "providers"


def _load(name):
    return json.loads((FIXTURES / name).read_text())


def _http_adapter(case, client):
    factories = {
        "sec": lambda: SecFilingsAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        ),
        "fmp_news": lambda: FmpNewsAdapter("test-key", client=client, clock=lambda: AS_OF),
        "fmp_insider": lambda: FmpInsiderAdapter("test-key", client=client, clock=lambda: AS_OF),
        "fmp_technical": lambda: FmpTechnicalAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ),
        "finnhub_social": lambda: FinnhubSocialAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ),
        "finnhub_lobbying": lambda: FinnhubLobbyingAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ),
        "flowalgo": lambda: FlowAlgoAdapter("test-key", client=client, clock=lambda: AS_OF),
        "cheddarflow": lambda: CheddarFlowAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ),
    }
    return factories[case]()


def _success_payload(case, request):
    if case == "sec":
        fixture = _load("sec.json")
        return (
            fixture["ticker_map"]
            if "company_tickers" in request.url.path
            else fixture["submissions"]
        )
    if case == "fmp_technical":
        fixture = _load("fmp_technical.json")
        indicator = request.url.path.rsplit("/", 1)[-1]
        period = request.url.params["periodLength"]
        return fixture[f"{indicator}_{period}"]
    return _load(
        {
            "fmp_news": "fmp_news.json",
            "fmp_insider": "fmp_insider.json",
            "finnhub_social": "finnhub_social.json",
            "finnhub_lobbying": "finnhub_lobbying.json",
            "flowalgo": "flowalgo.json",
            "cheddarflow": "cheddarflow.json",
        }[case]
    )


HTTP_CASES = [
    "sec",
    "fmp_news",
    "fmp_insider",
    "fmp_technical",
    "finnhub_social",
    "finnhub_lobbying",
    "flowalgo",
    "cheddarflow",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", HTTP_CASES)
async def test_PT_PROVIDER_SUCCESS_AND_PROVENANCE_FROM_SANITIZED_FIXTURES(case):
    def handler(request):
        return httpx.Response(200, json=_success_payload(case, request))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await _http_adapter(case, client).collect("NVDA", 14)

    assert result.provider == case.split("_")[0]
    assert result.evidence
    assert all(item.sources and item.sources[0].observed_at for item in result.evidence)


def _empty_payload(case, request):
    empty = _load("empty.json")
    if case == "sec":
        return (
            empty["sec"]["ticker_map"]
            if "company_tickers" in request.url.path
            else empty["sec"]["submissions"]
        )
    if case == "finnhub_social":
        return empty["finnhub_social"]
    if case in {"finnhub_lobbying", "flowalgo", "cheddarflow"}:
        return empty["data"]
    return empty["list"]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", HTTP_CASES)
async def test_PT_PROVIDER_EMPTY_DATA_FROM_SANITIZED_FIXTURES(case):
    def handler(request):
        return httpx.Response(200, json=_empty_payload(case, request))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await _http_adapter(case, client).collect("NVDA", 14)

    assert result.evidence == []
    assert result.warnings


def _malformed_payload(case, request):
    malformed = _load("malformed.json")
    if case == "sec":
        return malformed["sec"]
    if case in {"fmp_news", "fmp_insider", "fmp_technical"}:
        return malformed["object"]
    if case == "finnhub_social":
        return {"reddit": malformed["object"], "twitter": []}
    if case == "finnhub_lobbying":
        return {"data": malformed["object"]}
    return malformed["object"]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", HTTP_CASES)
async def test_PT_PROVIDER_MALFORMED_SCHEMA_FROM_SANITIZED_FIXTURES(case):
    def handler(request):
        return httpx.Response(200, json=_malformed_payload(case, request))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises((TypeError, ValueError)):
            await _http_adapter(case, client).collect("NVDA", 14)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", HTTP_CASES)
@pytest.mark.parametrize("status", [401, 429])
async def test_PT_PROVIDER_AUTH_AND_RATE_LIMIT_PER_PROVIDER(case, status):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, json={"error": "x"}))
    ) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await _http_adapter(case, client).collect("NVDA", 14)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", HTTP_CASES)
async def test_PT_PROVIDER_TIMEOUT_PER_PROVIDER(case):
    def handler(request):
        raise httpx.ReadTimeout("fixture timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.ReadTimeout):
            await _http_adapter(case, client).collect("NVDA", 14)


@pytest.mark.asyncio
async def test_PT_YFINANCE_NORMALIZATION_EMPTY_MALFORMED_TIMEOUT_AND_PROVENANCE():
    fixture = _load("yfinance.json")
    adapter = YFinanceOptionsAdapter(
        chain_loader=lambda ticker: (
            fixture["expiration"],
            fixture["calls"],
            fixture["puts"],
        ),
        clock=lambda: AS_OF,
    )
    success = await adapter.collect("NVDA", 14)
    assert success.evidence[0].sources[0].name == "yfinance chain snapshot"

    empty = _load("empty.json")["yfinance"]
    empty_result = await YFinanceOptionsAdapter(
        chain_loader=lambda ticker: (empty["expiration"], empty["calls"], empty["puts"]),
        clock=lambda: AS_OF,
    ).collect("NVDA", 14)
    assert empty_result.evidence == []

    for error in (TypeError("malformed fixture"), TimeoutError("fixture timeout")):
        def fail(ticker, error=error):
            raise error

        with pytest.raises(type(error)):
            await YFinanceOptionsAdapter(chain_loader=fail, clock=lambda: AS_OF).collect(
                "NVDA", 14
            )
