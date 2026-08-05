"""Filing index and primary documents are immutable too, and re-fetched every scan.

`index.json` plus 8-K/6-K primary-document enrichment is 676 of a scan's 2086 SEC
requests. Both are accession-addressed, so both cache — but a filing directory can gain
documents in the minutes after acceptance, so an index is only cached once the filing has
settled. The primary-document payload is the classification decision, keyed on the
ruleset version, so a rules bump re-derives instead of replaying an old reading.
"""

from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from tests.conftest import AS_OF

UA = "Catalyst Edge test@example.com"
CIK = "0001045810"
SETTLED = "0001045810-26-000101"
YOUNG = "0001045810-26-000102"
FIXTURE = (
    Path(__file__).parent / "fixtures" / "sec" / "primary_documents"
    / "debt_completed_inline_xbrl.html"
)


def _path(accession: str, document: str) -> str:
    return f"/Archives/edgar/data/1045810/{accession.replace('-', '')}/{document}"


def _client() -> tuple[httpx.AsyncClient, list[str]]:
    """Two 8-Ks: one filed 11 days ago, one filed 30 minutes ago."""
    fetched: list[str] = []
    content = FIXTURE.read_bytes()

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
            settled_at = AS_OF - timedelta(days=11)
            young_at = AS_OF - timedelta(minutes=30)
            return httpx.Response(
                200,
                json={
                    "filings": {
                        "recent": {
                            "form": ["8-K", "8-K"],
                            "filingDate": [
                                settled_at.date().isoformat(),
                                young_at.date().isoformat(),
                            ],
                            "acceptanceDateTime": [
                                settled_at.isoformat().replace("+00:00", "Z"),
                                young_at.isoformat().replace("+00:00", "Z"),
                            ],
                            "accessionNumber": [SETTLED, YOUNG],
                            "primaryDocument": ["event.htm", "event.htm"],
                            "items": ["8.01,9.01", "8.01,9.01"],
                        }
                    }
                },
            )
        if "/Archives/" in path:
            fetched.append(path)
            if path.endswith("/index.json"):
                return httpx.Response(
                    200,
                    json={"directory": {"item": [{"name": "ex991.htm", "type": "EX-99.1"}]}},
                )
            return httpx.Response(200, content=content)
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), fetched


async def _scan(store_path: str) -> tuple[object, list[str]]:
    client, fetched = _client()
    async with client:
        result = await SecFilingsAdapter(
            UA, client=client, clock=lambda: AS_OF, store_path=store_path
        ).collect("NVDA", 14)
    return result, fetched


def _facts(result) -> list[tuple]:
    return [
        (
            item.sources[0].accession_or_record_id,
            item.sources[0].raw_sha256,
            item.context.event_type if item.context else None,
            tuple(str(link) for link in (item.sources[0].related_sources or [])),
        )
        for item in result.evidence
    ]


@pytest.mark.asyncio
async def test_settled_filing_is_fetched_once_across_scans(tmp_path):
    store_path = str(tmp_path / "evidence.sqlite3")

    first, first_fetched = await _scan(store_path)
    second, second_fetched = await _scan(store_path)

    assert sorted(first_fetched) == sorted(
        [
            _path(SETTLED, "event.htm"),
            _path(SETTLED, "index.json"),
            _path(YOUNG, "event.htm"),
            _path(YOUNG, "index.json"),
        ]
    )
    # The settled filing is fully cached; the young one keeps re-fetching its index.
    assert sorted(second_fetched) == sorted([_path(YOUNG, "index.json")])
    assert _facts(second) == _facts(first)
    assert second.warnings == first.warnings


@pytest.mark.asyncio
async def test_ruleset_bump_re_derives_the_primary_document(tmp_path, monkeypatch):
    store_path = str(tmp_path / "evidence.sqlite3")

    await _scan(store_path)
    monkeypatch.setattr("catalyst_edge_mcp.sec_filings.RULESET_VERSION", "sec-primary-v2")
    _, second_fetched = await _scan(store_path)

    assert _path(SETTLED, "event.htm") in second_fetched


@pytest.mark.asyncio
async def test_cached_filings_outside_the_window_are_pruned(tmp_path):
    store_path = str(tmp_path / "evidence.sqlite3")
    store = EvidenceStore(store_path)
    stale_url = "https://www.sec.gov/Archives/edgar/data/1045810/000000000000000001/old.json"
    store.put_sec_document(
        stale_url,
        parser_version="sec-events-v1",
        raw_sha256="0" * 64,
        payload=[],
        filed_at=AS_OF - timedelta(days=90),
        retrieved_at=AS_OF - timedelta(days=90),
    )

    await _scan(store_path)

    assert store.get_sec_documents([stale_url], "sec-events-v1") == {}
