from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.models import Direction, PolicyDecision, SourceStatus
from catalyst_edge_mcp.sec_ownership import (
    SecInsiderAdapter,
    parse_form_144_xml,
    parse_ownership_xml,
)
from tests.conftest import AS_OF

FIXTURES = Path(__file__).parent / "fixtures" / "sec"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_PT_SEC_OWNERSHIP_XML_preserves_transaction_semantics_and_provenance_facts():
    parsed = parse_ownership_xml(_fixture("form4_purchase_one.xml"))

    assert parsed["form"] == "4"
    assert parsed["issuer_cik"] == "0001045810"
    assert parsed["owners"][0] == {
        "cik": "0000000001",
        "name": "ALPHA OWNER",
        "is_director": True,
        "is_officer": False,
        "is_ten_percent_owner": False,
        "officer_title": None,
    }
    purchase, grant = parsed["transactions"]
    assert purchase["code"] == "P"
    assert purchase["shares"] == 100
    assert purchase["price"] == 50
    assert purchase["acquired_disposed"] == "A"
    assert purchase["holdings_after"] == 1100
    assert purchase["ownership_form"] == "D"
    assert grant["code"] == "A"
    assert parsed["footnotes"]["F1"] == "Open-market purchase."

    planned_content = _fixture("form4_purchase_one.xml").replace(
        b"Open-market purchase.", b"Sale under a Rule 10b5-1 trading plan."
    )
    planned = parse_ownership_xml(planned_content)
    assert planned["transactions"][0]["is_10b5_1"] is True


def test_PT_SEC_FORM_144_is_parsed_as_proposed_not_completed():
    parsed = parse_form_144_xml(_fixture("form144_proposed.xml"))

    assert parsed["issuer_cik"] == "0001045810"
    assert parsed["filer_name"] == "DELTA OWNER"
    assert parsed["units_to_be_sold"] == 2500
    assert parsed["approx_sale_date"] == "2026-07-15"


def _transport(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/files/company_tickers_exchange.json":
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
    if path == "/submissions/CIK0001045810.json":
        return httpx.Response(
            200,
            json={
                "filings": {
                    "recent": {
                        "form": ["4", "4", "4", "144"],
                        "filingDate": ["2026-07-12", "2026-07-11", "2026-07-10", "2026-07-11"],
                        "acceptanceDateTime": [
                            "2026-07-12T14:01:00Z",
                            "2026-07-11T14:02:00Z",
                            "2026-07-10T14:03:00Z",
                            "2026-07-11T15:04:00Z",
                        ],
                        "accessionNumber": [
                            "0001045810-26-000101",
                            "0001045810-26-000102",
                            "0001045810-26-000103",
                            "0001045810-26-000104",
                        ],
                        "primaryDocument": [
                            "form4-one.xml",
                            "form4-two.xml",
                            "form4-three.xml",
                            "form144.xml",
                        ],
                    }
                }
            },
        )
    documents = {
        "/Archives/edgar/data/1045810/000104581026000101/form4-one.xml": "form4_purchase_one.xml",
        "/Archives/edgar/data/1045810/000104581026000102/form4-two.xml": "form4_purchase_two.xml",
        "/Archives/edgar/data/1045810/000104581026000103/form4-three.xml": (
            "form4_purchase_three.xml"
        ),
        "/Archives/edgar/data/1045810/000104581026000104/form144.xml": "form144_proposed.xml",
    }
    if path in documents:
        return httpx.Response(200, content=_fixture(documents[path]))
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_PT_SEC_INSIDER_NORMALIZATION_builds_strong_cluster_and_neutral_form144():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_transport)) as client:
        result = await SecInsiderAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.status == SourceStatus.FRESH
    assert result.policy_decision == PolicyDecision.APPROVED
    cluster = next(
        item for item in result.evidence if item.signal == "insider_purchase_strong_cluster"
    )
    proposed = next(
        item for item in result.evidence if item.signal == "insider_proposed_sale_intent"
    )
    assert cluster.direction == Direction.BULLISH
    assert cluster.confidence == 0.88
    assert cluster.context.event_type == "open_market_purchase_strong_cluster"
    assert cluster.context.novelty == "new_activity"
    assert cluster.context.corroborating_source_count == 2
    assert cluster.change.current_value == 30_800
    assert cluster.change.baseline_value == 0
    assert len(cluster.sources) == 3
    assert all(source.source_id == "sec" for source in cluster.sources)
    assert all(source.raw_sha256 for source in cluster.sources)
    assert all(source.accession_or_record_id for source in cluster.sources)
    assert len(cluster.raw_signal) == 3
    assert proposed.direction == Direction.NEUTRAL
    assert proposed.context.event_type == "proposed_insider_sale"
    assert proposed.raw_signal["completed_execution"] is False
    assert "not evidence of completed execution" in proposed.notes


@pytest.mark.asyncio
async def test_sec_insider_unknown_ticker_returns_typed_no_observations():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_transport)) as client:
        result = await SecInsiderAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        ).collect("ZZZZ", 14)

    assert result.evidence == []
    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert "no CIK" in result.warnings[0]


@pytest.mark.asyncio
async def test_sec_insider_resolves_display_style_class_ticker():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_transport)) as client:
        result = await SecInsiderAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        ).collect("BRK.B", 14)

    assert result.status == SourceStatus.FRESH
    assert any(item.signal == "insider_purchase_strong_cluster" for item in result.evidence)


def test_sec_insider_requires_contact_email():
    with pytest.raises(ValueError, match="contact email"):
        SecInsiderAdapter("anonymous-client")


def test_sec_insider_archive_url_strips_xsl_display_path():
    url = SecInsiderAdapter._archive_url(
        "0001045810", "0001045810-26-000101", "xslF345X05/form4-one.xml"
    )

    assert url.endswith("/000104581026000101/form4-one.xml")
    assert "xslF345X05" not in url
