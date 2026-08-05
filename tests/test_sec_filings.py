import hashlib
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.models import Direction
from catalyst_edge_mcp.sec_document_rules import RULESET_VERSION
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from tests.conftest import AS_OF

PRIMARY_DOCUMENT_FIXTURES = Path(__file__).parent / "fixtures" / "sec" / "primary_documents"


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


def _generic_item_801_evidence(*, form: str = "8-K"):
    payload = {
        "filings": {
            "recent": {
                "form": [form],
                "filingDate": ["2026-07-15"],
                "acceptanceDateTime": ["2026-07-15T12:00:00Z"],
                "accessionNumber": ["0001045810-26-000099"],
                "primaryDocument": ["event.htm"],
                "items": ["8.01,9.01"],
            }
        }
    }
    return SecFilingsAdapter._normalize_recent(
        payload, "0001045810", AS_OF - timedelta(days=14), AS_OF
    )[0]


@pytest.mark.parametrize(
    ("fixture_name", "expected_event_type", "expected_rule_id"),
    [
        (
            "debt_completed_inline_xbrl.html",
            "debt_offering",
            "completed_debt_offering",
        ),
        (
            "repurchase_table.html",
            "share_repurchase",
            "share_repurchase_activity",
        ),
        (
            "prospectus_update.html",
            "securities_offering",
            "filed_prospectus_supplement",
        ),
    ],
)
def test_sec_primary_document_rules_handle_representative_structures(
    fixture_name, expected_event_type, expected_rule_id
):
    evidence = _generic_item_801_evidence()

    SecFilingsAdapter._apply_primary_document_context(
        evidence,
        SecFilingsAdapter._classify_primary_document(
            (PRIMARY_DOCUMENT_FIXTURES / fixture_name).read_bytes()
        ),
    )

    enrichment = evidence.raw_signal["document_enrichment"]
    assert evidence.context.event_type == expected_event_type
    assert enrichment == {
        "ruleset_version": RULESET_VERSION,
        "status": "matched",
        "rule_id": expected_rule_id,
        "rule_version": "1",
        "candidate_rule_ids": enrichment["candidate_rule_ids"],
    }
    assert expected_rule_id in enrichment["candidate_rule_ids"]
    assert evidence.sources[0].parser_version == f"sec-events-v1+{RULESET_VERSION}"
    assert f"{expected_rule_id}@1" in evidence.notes


def test_sec_primary_document_rule_preserves_amendment_semantics():
    evidence = _generic_item_801_evidence(form="8-K/A")

    SecFilingsAdapter._apply_primary_document_context(
        evidence,
        SecFilingsAdapter._classify_primary_document(
            (PRIMARY_DOCUMENT_FIXTURES / "equity_amendment.html").read_bytes()
        ),
    )

    assert evidence.context.event_type == "equity_distribution"
    assert evidence.context.novelty == "amendment"
    assert (
        evidence.raw_signal["document_enrichment"]["rule_id"]
        == "equity_distribution_agreement"
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "debt_proposed.html",
        "repurchase_negated.html",
        "equity_terminated.html",
        "near_match.html",
    ],
)
def test_sec_primary_document_rules_fail_closed_on_negative_or_near_matches(
    fixture_name,
):
    evidence = _generic_item_801_evidence()
    original_context = evidence.context.model_copy(deep=True)

    SecFilingsAdapter._apply_primary_document_context(
        evidence,
        SecFilingsAdapter._classify_primary_document(
            (PRIMARY_DOCUMENT_FIXTURES / fixture_name).read_bytes()
        ),
    )

    assert evidence.context == original_context
    assert evidence.raw_signal["document_enrichment"] == {
        "ruleset_version": RULESET_VERSION,
        "status": "no_match",
        "rule_id": None,
        "rule_version": None,
        "candidate_rule_ids": [],
    }
    assert "document_event_type" not in evidence.raw_signal
    assert evidence.sources[0].parser_version == "sec-events-v1"


def test_sec_primary_document_rules_fail_closed_on_multiple_specific_events():
    evidence = _generic_item_801_evidence()
    original_context = evidence.context.model_copy(deep=True)

    SecFilingsAdapter._apply_primary_document_context(
        evidence,
        SecFilingsAdapter._classify_primary_document(
            (PRIMARY_DOCUMENT_FIXTURES / "multi_event_ambiguous.html").read_bytes()
        ),
    )

    enrichment = evidence.raw_signal["document_enrichment"]
    assert evidence.context == original_context
    assert enrichment["status"] == "ambiguous"
    assert set(enrichment["candidate_rule_ids"]) == {
        "completed_debt_offering",
        "share_repurchase_activity",
    }
    assert enrichment["rule_id"] is None


@pytest.mark.asyncio
async def test_sec_adapter_fetches_hashes_and_versions_bounded_item_801_document():
    content = (
        PRIMARY_DOCUMENT_FIXTURES / "debt_completed_inline_xbrl.html"
    ).read_bytes()
    accession = "0001045810-26-000098"
    accession_path = accession.replace("-", "")

    def transport(request: httpx.Request) -> httpx.Response:
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
                            "form": ["8-K"],
                            "filingDate": ["2026-07-15"],
                            "acceptanceDateTime": ["2026-07-15T12:00:00Z"],
                            "accessionNumber": [accession],
                            "primaryDocument": ["event.htm"],
                            "items": ["8.01,9.01"],
                        }
                    }
                },
            )
        if request.url.path == (
            f"/Archives/edgar/data/1045810/{accession_path}/event.htm"
        ):
            return httpx.Response(200, content=content)
        if request.url.path == (
            f"/Archives/edgar/data/1045810/{accession_path}/index.json"
        ):
            return httpx.Response(200, json={"directory": {"item": []}})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await SecFilingsAdapter(
            "Catalyst Edge test@example.com", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    evidence = result.evidence[0]
    assert result.warnings == []
    assert evidence.context.event_type == "debt_offering"
    assert evidence.sources[0].raw_sha256 == hashlib.sha256(content).hexdigest()
    assert evidence.sources[0].parser_version == f"sec-events-v1+{RULESET_VERSION}"
    assert evidence.raw_signal["document_enrichment"]["status"] == "matched"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.sec.gov/Archives/edgar/data/1/filing.htm",
        "https://sec.gov/Archives/edgar/data/1/filing.htm",
        "https://www.sec.gov/Archives/edgar/data/1/filing.htm?download=1",
        "https://www.sec.gov/Archives/edgar/data/../../etc/passwd",
    ],
)
def test_sec_primary_document_archive_url_validation_fails_closed(url):
    with pytest.raises(ValueError, match="outside the official archive"):
        SecFilingsAdapter._require_archive_url(url)
