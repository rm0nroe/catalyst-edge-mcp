"""Accession-addressed EDGAR documents must be fetched once, not once per scan.

Ownership documents are immutable and byte-identical on every re-read, yet a 14-day
window at 3 scans/day re-fetched each one 42 times: 814 of a scan's 2086 SEC requests,
98% of them for documents filed before the previous scan. The cache stores the parsed
payload rather than the body (bodies are ~184 MB/window, parsed results ~10 MB) and is
keyed on parser_version so a parser bump re-derives instead of serving a stale reading.
"""

from datetime import timedelta

import httpx
import pytest

from catalyst_edge_mcp import sec_ownership
from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.sec_ownership import SecInsiderAdapter
from tests.conftest import AS_OF
from tests.test_sec_ownership import _transport

UA = "Catalyst Edge test@example.com"


def _counting_client() -> tuple[httpx.AsyncClient, list[str]]:
    """The shared ownership transport, plus a tally of document fetches."""
    fetched: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "/Archives/" in request.url.path:
            fetched.append(request.url.path)
        return _transport(request)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), fetched


async def _scan(store_path: str) -> tuple[object, list[str]]:
    client, fetched = _counting_client()
    async with client:
        result = await SecInsiderAdapter(
            UA, client=client, clock=lambda: AS_OF, store_path=store_path
        ).collect("NVDA", 14)
    return result, fetched


def _provenance(result) -> set[tuple[str, str]]:
    return {
        (str(source.url), str(source.raw_sha256))
        for item in result.evidence
        for source in item.sources
    }


@pytest.mark.asyncio
async def test_second_scan_serves_every_document_from_cache(tmp_path):
    store_path = str(tmp_path / "evidence.sqlite3")

    first, first_fetched = await _scan(store_path)
    second, second_fetched = await _scan(store_path)

    assert first_fetched, "first scan must actually fetch the documents"
    assert second_fetched == []
    # A cache that loses the parsed payload or its hash is a provenance regression,
    # not a speedup: raw_sha256 is the evidence field readers verify against.
    assert _provenance(second) == _provenance(first)
    assert {item.signal for item in second.evidence} == {item.signal for item in first.evidence}


@pytest.mark.asyncio
async def test_parser_version_bump_re_derives_instead_of_serving_a_stale_reading(
    tmp_path, monkeypatch
):
    store_path = str(tmp_path / "evidence.sqlite3")

    _, first_fetched = await _scan(store_path)
    monkeypatch.setattr(sec_ownership, "PARSER_VERSION", "sec-ownership-v2")
    _, second_fetched = await _scan(store_path)

    assert second_fetched == first_fetched


@pytest.mark.asyncio
async def test_documents_older_than_the_lookback_window_are_pruned(tmp_path):
    store_path = str(tmp_path / "evidence.sqlite3")
    store = EvidenceStore(store_path)
    stale_url = "https://www.sec.gov/Archives/edgar/data/1045810/000000000000000001/old.xml"
    store.put_sec_document(
        stale_url,
        parser_version=sec_ownership.PARSER_VERSION,
        raw_sha256="0" * 64,
        payload={"transactions": []},
        filed_at=AS_OF - timedelta(days=90),
        retrieved_at=AS_OF - timedelta(days=90),
    )

    await _scan(store_path)

    assert store.get_sec_documents([stale_url], sec_ownership.PARSER_VERSION) == {}
