"""CIK resolution must distinguish "could not identify the issuer" from "issuer filed nothing".

SEC's ticker->CIK map is incomplete: on 2026-08-05 it omitted AEP (CIK 0000004904)
from both company_tickers_exchange.json and company_tickers.json, so a real 10-Q and
8-K filed inside the lookback window were reported as no_observations.
"""

from datetime import timedelta

import httpx
import pytest

from catalyst_edge_mcp.models import ReasonCode, SourceStatus
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from catalyst_edge_mcp.sec_ownership import SecInsiderAdapter
from tests.conftest import AS_OF

AEP_CIK = "0000004904"
UA = "Catalyst Edge test@example.com"

COMPANY_SEARCH_HIT = f"""<?xml version="1.0" encoding="ISO-8859-1" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <company-info>
    <cik>{AEP_CIK}</cik>
    <conformed-name>AMERICAN ELECTRIC POWER CO INC</conformed-name>
  </company-info>
</feed>
"""

COMPANY_SEARCH_MISS = """<?xml version="1.0" encoding="ISO-8859-1" ?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <error>No matching Ticker Symbol.</error>
</feed>
"""


def _map_without_aep() -> httpx.Response:
    """The real defect: AEP is absent from SEC's mapping file."""
    return httpx.Response(
        200,
        json={
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [[1045810, "NVIDIA CORP", "NVDA", "Nasdaq"]],
        },
    )


def _aep_submissions() -> httpx.Response:
    filed = AS_OF.date().isoformat()
    return httpx.Response(
        200,
        json={
            "filings": {
                "recent": {
                    "form": ["10-Q", "8-K"],
                    "filingDate": [filed, filed],
                    "acceptanceDateTime": ["2026-07-12T15:45:00Z", "2026-07-12T15:46:00Z"],
                    "accessionNumber": ["0000004904-26-000001", "0000004904-26-000002"],
                    "primaryDocument": ["aep-10q.htm", "aep-8k.htm"],
                    "items": ["", "2.02,9.01"],
                }
            }
        },
    )


def _transport(*, search_hits: bool):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/files/company_tickers_exchange.json":
            return _map_without_aep()
        if path == "/cgi-bin/browse-edgar":
            body = COMPANY_SEARCH_HIT if search_hits else COMPANY_SEARCH_MISS
            return httpx.Response(200, text=body)
        if path == f"/submissions/CIK{AEP_CIK}.json":
            return _aep_submissions()
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_sec_filings_recovers_ticker_missing_from_sec_map():
    async with httpx.AsyncClient(transport=_transport(search_hits=True)) as client:
        result = await SecFilingsAdapter(UA, client=client, clock=lambda: AS_OF).collect("AEP", 14)

    assert result.status == SourceStatus.FRESH
    forms = sorted(str((item.raw_signal or {}).get("form")) for item in result.evidence)
    assert forms == ["10-Q", "8-K"]


@pytest.mark.asyncio
async def test_sec_filings_unresolvable_issuer_is_not_silently_no_observations():
    async with httpx.AsyncClient(transport=_transport(search_hits=False)) as client:
        result = await SecFilingsAdapter(UA, client=client, clock=lambda: AS_OF).collect("AEP", 14)

    assert result.evidence == []
    # The reason lane, not the status lane, carries the distinction: ENTITY_REJECTED
    # outranks OBSERVED_NONE in REASON_PRECEDENCE (30 vs 40).
    assert any(r.code == ReasonCode.ENTITY_REJECTED for r in result.reason_records)


@pytest.mark.asyncio
async def test_sec_insider_recovers_ticker_missing_from_sec_map():
    async with httpx.AsyncClient(transport=_transport(search_hits=True)) as client:
        result = await SecInsiderAdapter(UA, client=client, clock=lambda: AS_OF).collect("AEP", 14)

    # No ownership forms in the fixture, so no evidence is correct here; what matters
    # is that resolution succeeded rather than aborting at the map miss.
    assert not any("no CIK" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_sec_insider_unresolvable_issuer_records_entity_rejected():
    async with httpx.AsyncClient(transport=_transport(search_hits=False)) as client:
        result = await SecInsiderAdapter(UA, client=client, clock=lambda: AS_OF).collect("AEP", 14)

    assert any(r.code == ReasonCode.ENTITY_REJECTED for r in result.reason_records)


@pytest.mark.asyncio
async def test_company_search_failure_degrades_instead_of_raising():
    """A failing fallback must not turn an unresolved ticker into an adapter error."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/files/company_tickers_exchange.json":
            return _map_without_aep()
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await SecFilingsAdapter(UA, client=client, clock=lambda: AS_OF).collect("AEP", 14)

    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert any(r.code == ReasonCode.ENTITY_REJECTED for r in result.reason_records)


@pytest.mark.asyncio
async def test_company_search_is_not_called_when_map_resolves():
    """The fallback costs a request; it must only fire on a map miss."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/files/company_tickers_exchange.json":
            return httpx.Response(
                200,
                json={
                    "fields": ["cik", "name", "ticker", "exchange"],
                    "data": [[1045810, "NVIDIA CORP", "NVDA", "Nasdaq"]],
                },
            )
        if request.url.path == "/submissions/CIK0001045810.json":
            return httpx.Response(
                200,
                json={
                    "filings": {
                        "recent": {
                            "form": ["10-Q"],
                            "filingDate": [(AS_OF - timedelta(days=1)).date().isoformat()],
                            "acceptanceDateTime": ["2026-07-11T15:45:00Z"],
                            "accessionNumber": ["0001045810-26-000001"],
                            "primaryDocument": ["nvda-10q.htm"],
                            "items": [""],
                        }
                    }
                },
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await SecFilingsAdapter(UA, client=client, clock=lambda: AS_OF).collect("NVDA", 14)

    assert "/cgi-bin/browse-edgar" not in calls
