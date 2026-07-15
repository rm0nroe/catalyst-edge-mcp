from datetime import timedelta

import httpx
import pytest

from catalyst_edge_mcp.models import Direction
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from tests.conftest import AS_OF


def sec_transport(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/files/company_tickers_exchange.json":
        return httpx.Response(
            200,
            json={
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [
                    [1045810, "NVIDIA CORP", "NVDA", "Nasdaq"],
                    [1045810, "BERKSHIRE CLASS B", "BRK-B", "NYSE"],
                ],
            },
        )
    if request.url.path == "/submissions/CIK0001045810.json":
        return httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "form": ["8-K", "4", "10-Q"],
                        "filingDate": [
                            AS_OF.date().isoformat(),
                            AS_OF.date().isoformat(),
                            (AS_OF - timedelta(days=30)).date().isoformat(),
                        ],
                        "acceptanceDateTime": [
                            "2026-07-12T15:45:00Z",
                            "2026-07-12T15:46:00Z",
                            "2026-06-12T15:47:00Z",
                        ],
                        "accessionNumber": [
                            "0001045810-26-000001",
                            "0001045810-26-000002",
                            "0001045810-26-000003",
                        ],
                        "primaryDocument": ["nvda-8k.htm", "form4.xml", "nvda-10q.htm"],
                        "items": ["2.02,9.01", "", ""],
                    }
                }
            },
        )
    if request.url.path == "/Archives/edgar/data/1045810/000104581026000001/index.json":
        return httpx.Response(
            200,
            json={
                "directory": {
                    "item": [
                        {"name": "nvda-8k.htm", "type": "8-K"},
                        {"name": "earnings-exhibit.htm", "type": "EX-99.1"},
                        {"name": "a8-kex991q2202603282026.htm", "type": "text.gif"},
                    ]
                }
            },
        )
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_sec_adapter_normalizes_recent_primary_source_evidence():
    async with httpx.AsyncClient(transport=httpx.MockTransport(sec_transport)) as client:
        adapter = SecFilingsAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        )
        result = await adapter.collect("NVDA", 14)

    assert result.family == "filings_news"
    assert len(result.evidence) == 1
    evidence = result.evidence[0]
    assert evidence.signal == "sec_form_8_k"
    assert evidence.direction == Direction.NEUTRAL
    assert evidence.context.event_type == "financial_results"
    assert evidence.context.event_label == "Results of operations and financial condition"
    assert evidence.source_quality == 1
    assert evidence.source_count == 1
    assert str(evidence.sources[0].url).endswith("/000104581026000001/nvda-8k.htm")
    assert evidence.timestamp.isoformat() == "2026-07-12T15:45:00+00:00"
    assert evidence.sources[0].source_id == "sec"
    assert evidence.sources[0].accession_or_record_id == "0001045810-26-000001"
    assert evidence.sources[0].parser_version == "sec-events-v1"
    assert [str(url) for url in evidence.sources[0].related_sources] == [
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/earnings-exhibit.htm",
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/a8-kex991q2202603282026.htm",
    ]
    assert evidence.raw_signal["items"] == "2.02,9.01"


@pytest.mark.asyncio
async def test_sec_adapter_unknown_ticker_is_empty_with_warning():
    async with httpx.AsyncClient(transport=httpx.MockTransport(sec_transport)) as client:
        adapter = SecFilingsAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        )
        result = await adapter.collect("ZZZZ", 14)

    assert result.evidence == []
    assert "no CIK" in result.warnings[0]


@pytest.mark.asyncio
async def test_sec_adapter_resolves_display_style_class_ticker():
    async with httpx.AsyncClient(transport=httpx.MockTransport(sec_transport)) as client:
        result = await SecFilingsAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        ).collect("BRK.B", 14)

    assert len(result.evidence) == 1
    assert result.evidence[0].sources[0].accession_or_record_id == "0001045810-26-000001"


def test_sec_adapter_requires_contact_email():
    with pytest.raises(ValueError, match="contact email"):
        SecFilingsAdapter("anonymous-client")


def test_PT_SEC_MATERIAL_EVENT_maps_only_allowlisted_item_direction():
    payload = {
        "filings": {
            "recent": {
                "form": ["8-K", "8-K"],
                "filingDate": ["2026-07-12", "2026-07-12"],
                "accessionNumber": ["0001045810-26-000010", "0001045810-26-000011"],
                "primaryDocument": ["bankruptcy.htm", "earnings.htm"],
                "items": ["1.03", "2.02"],
            }
        }
    }

    evidence = SecFilingsAdapter._normalize_recent(
        payload, "0001045810", AS_OF - timedelta(days=14), AS_OF
    )

    assert evidence[0].signal == "bankruptcy"
    assert evidence[0].direction == Direction.BEARISH
    assert evidence[1].signal == "sec_form_8_k"
    assert evidence[1].direction == Direction.NEUTRAL
