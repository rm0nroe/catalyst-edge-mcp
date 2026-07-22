from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.models import Direction, ReasonCode, SourceStatus
from catalyst_edge_mcp.registry_config import DEFAULT_REGISTRY_PATH, load_registry_bundle
from catalyst_edge_mcp.sec_funds import SecFundAdapter
from catalyst_edge_mcp.sec_ownership import SecInsiderAdapter
from tests.conftest import AS_OF

FUND_FIXTURES = Path(__file__).parent / "fixtures" / "sec" / "funds"


def _fund_transport(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/submissions/CIK0001067839.json":
        return httpx.Response(
            200,
            json={
                "cik": "1067839",
                "filings": {
                    "recent": {
                        "form": ["NPORT-P", "N-CEN", "8-K"],
                        "filingDate": ["2026-07-19", "2026-07-18", "2026-07-17"],
                        "acceptanceDateTime": [
                            "2026-07-19T10:53:06Z",
                            "2026-07-18T19:23:11Z",
                            "2026-07-17T12:00:00Z",
                        ],
                        "reportDate": ["2026-03-31", "2025-12-19", ""],
                        "accessionNumber": [
                            "0001067839-26-000024",
                            "0001067839-26-000018",
                            "0001067839-26-000099",
                        ],
                        "primaryDocument": [
                            "xslFormNPORT-P_X01/primary_doc.xml",
                            "xslFormN-CEN_X01/primary_doc.xml",
                            "corporate.htm",
                        ],
                    }
                },
            },
        )
    if request.url.path.endswith("/000106783926000024/primary_doc.xml"):
        return httpx.Response(200, content=(FUND_FIXTURES / "nport.xml").read_bytes())
    if request.url.path.endswith("/000106783926000018/primary_doc.xml"):
        return httpx.Response(200, content=(FUND_FIXTURES / "ncen.xml").read_bytes())
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_sec_fund_adapter_parses_neutral_as_filed_chronology():
    bundle = load_registry_bundle(DEFAULT_REGISTRY_PATH)
    async with httpx.AsyncClient(transport=httpx.MockTransport(_fund_transport)) as client:
        result = await SecFundAdapter(
            "Catalyst Edge test@example.com",
            registry=bundle.fund_identity_index,
            client=client,
            clock=lambda: AS_OF,
        ).collect("QQQ", 14)

    assert result.status == SourceStatus.FRESH
    assert [item.signal for item in result.evidence] == [
        "sec_fund_nport_report",
        "sec_fund_ncen_report",
    ]
    nport, ncen = result.evidence
    assert nport.direction == ncen.direction == Direction.NEUTRAL
    assert nport.context.materiality == "research_only"
    assert nport.raw_signal["registrant_cik"] == "CIK0001067839"
    assert nport.raw_signal["series_id"] == "S000101292"
    assert nport.raw_signal["class_id"] == "C000271435"
    assert nport.raw_signal["report_date"] == "2026-03-31"
    assert nport.raw_signal["reporting_period_end"] == "2026-09-30"
    assert nport.raw_signal["accepted_at"] == "2026-07-19T10:53:06+00:00"
    assert nport.raw_signal["holdings_count"] == 2
    assert ncen.raw_signal["reporting_period_end"] == "2025-12-19"
    assert nport.sources[0].parser_version == "sec-funds-v1"
    assert str(nport.sources[0].related_sources[0]).startswith(
        "https://www.invesco.com/"
    )
    assert "no sponsor notice" in nport.notes.lower()


@pytest.mark.parametrize(
    ("ticker", "expected_status"),
    [
        ("SPY", "unsupported_no_series_class"),
        ("DIA", "unsupported_no_series_class"),
        ("GLD", "unsupported_non_investment_company"),
    ],
)
@pytest.mark.asyncio
async def test_sec_fund_adapter_returns_typed_unsupported_identity_without_network(
    ticker, expected_status
):
    def unexpected_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected request: {request.url}")

    bundle = load_registry_bundle(DEFAULT_REGISTRY_PATH)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(unexpected_request)
    ) as client:
        result = await SecFundAdapter(
            "Catalyst Edge test@example.com",
            registry=bundle.fund_identity_index,
            client=client,
            clock=lambda: AS_OF,
        ).collect(ticker, 14)

    assert result.status == SourceStatus.UNSUPPORTED
    assert result.evidence == []
    assert result.reason_records[0].code == ReasonCode.SOURCE_UNSUPPORTED
    assert result.reason_records[0].detail == expected_status


def test_sec_fund_parser_rejects_series_class_identity_mismatch():
    bundle = load_registry_bundle(DEFAULT_REGISTRY_PATH)
    content = (FUND_FIXTURES / "nport.xml").read_bytes().replace(
        b"C000271435", b"C000000000"
    )

    with pytest.raises(ValueError, match="series/class"):
        SecFundAdapter._parse_document(
            content,
            form="NPORT-P",
            fund=bundle.fund_identity_index["QQQ"],
        )


@pytest.mark.asyncio
async def test_fund_ticker_skips_corporate_insider_semantics_without_network():
    def unexpected_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected request: {request.url}")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(unexpected_request)
    ) as client:
        result = await SecInsiderAdapter(
            "Catalyst Edge test@example.com",
            client=client,
            clock=lambda: AS_OF,
            fund_tickers=frozenset({"QQQ"}),
        ).collect("QQQ", 14)

    assert result.status == SourceStatus.UNSUPPORTED
    assert result.evidence == []
    assert result.reason_records[0].detail == "fund_has_no_corporate_insider_semantics"
