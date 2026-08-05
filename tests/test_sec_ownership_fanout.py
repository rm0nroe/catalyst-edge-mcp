"""Per-ticker ownership fan-out must be bounded and newest-first.

One request per ownership filing, issued serially, made per-ticker cost scale with
issuer filing count against a fixed 8s adapter deadline: every ticker needing >=12
requests timed out, while every survivor needed <=9. Fetches now go out concurrently
under SEC_GATE's concurrency bound, with a cap for pathological filers.
"""

from datetime import timedelta

import httpx
import pytest

from catalyst_edge_mcp.sec_ownership import MAX_OWNERSHIP_DOCUMENTS, SecInsiderAdapter
from tests.conftest import AS_OF

UA = "Catalyst Edge test@example.com"
CIK = "0001045810"
EMPTY_OWNERSHIP_XML = b"<ownershipDocument></ownershipDocument>"


def _submissions(count: int) -> httpx.Response:
    """`count` Form 4s inside the window, deliberately OLDEST-first.

    SEC returns filings.recent newest-first by convention, not contract, so the
    fixture inverts it: a cap that trusts payload order keeps the wrong filings.
    """
    accessions = [f"0001045810-26-{index:06d}" for index in range(count)]
    # Spaced by hours so every filing sits inside the 14-day window; the point of the
    # fixture is ordering and count, not cutoff behavior.
    stamps = [AS_OF - timedelta(hours=count - index) for index in range(count)]
    dates = [stamp.date().isoformat() for stamp in stamps]
    times = [stamp.isoformat().replace("+00:00", "Z") for stamp in stamps]
    return httpx.Response(
        200,
        json={
            "filings": {
                "recent": {
                    "form": ["4"] * count,
                    "filingDate": dates,
                    "acceptanceDateTime": times,
                    "accessionNumber": accessions,
                    "primaryDocument": [f"form4-{index}.xml" for index in range(count)],
                }
            }
        },
    )


def _client(count: int) -> tuple[httpx.AsyncClient, list[str]]:
    fetched: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/files/company_tickers_exchange.json":
            return httpx.Response(
                200,
                json={
                    "fields": ["cik", "name", "ticker", "exchange"],
                    "data": [[1045810, "NVIDIA CORP", "NVDA", "Nasdaq"]],
                },
            )
        if path == f"/submissions/CIK{CIK}.json":
            return _submissions(count)
        if "/Archives/" in path:
            fetched.append(path)
            return httpx.Response(200, content=EMPTY_OWNERSHIP_XML)
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), fetched


@pytest.mark.asyncio
async def test_every_filing_is_fetched_when_under_the_cap():
    client, fetched = _client(MAX_OWNERSHIP_DOCUMENTS - 5)
    async with client:
        result = await SecInsiderAdapter(UA, client=client, clock=lambda: AS_OF).collect("NVDA", 14)

    assert len(fetched) == MAX_OWNERSHIP_DOCUMENTS - 5
    assert not any("truncated" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_pathological_filer_is_capped_and_says_so():
    client, fetched = _client(MAX_OWNERSHIP_DOCUMENTS + 9)
    async with client:
        result = await SecInsiderAdapter(UA, client=client, clock=lambda: AS_OF).collect("NVDA", 14)

    assert len(fetched) == MAX_OWNERSHIP_DOCUMENTS
    # A silent cap reads as "this issuer filed less", which is the bug class we just fixed.
    assert any("truncated" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_cap_keeps_the_most_recent_filings_not_the_payload_order():
    count = MAX_OWNERSHIP_DOCUMENTS + 9
    client, fetched = _client(count)
    async with client:
        await SecInsiderAdapter(UA, client=client, clock=lambda: AS_OF).collect("NVDA", 14)

    # The fixture is oldest-first, so the newest filings are the highest indices.
    newest = {f"form4-{index}.xml" for index in range(count - MAX_OWNERSHIP_DOCUMENTS, count)}
    assert {path.rsplit("/", 1)[-1] for path in fetched} == newest
