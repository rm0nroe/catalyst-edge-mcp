import json
from datetime import timedelta
from pathlib import Path

import pytest

from catalyst_edge_mcp.adapters import StaticAdapter
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import AdapterResult, SourceStatus, ToolInput
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from catalyst_edge_mcp.service import CatalystService

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "validation" / "real_catalyst_cases.json"
)


def _cases():
    return json.loads(FIXTURE_PATH.read_text())["cases"]


def _evidence(case):
    accepted = SecFilingsAdapter._parse_datetime(case["accepted_at"])
    recent = {
        "form": [case["form"]],
        "acceptanceDateTime": [case["accepted_at"]],
        "filingDate": [case["accepted_at"][:10]],
        "accessionNumber": [case["accession"]],
        "primaryDocument": [case["primary_document"]],
        "items": [case["items"]],
    }
    evidence = SecFilingsAdapter._normalize_recent(
        {"filings": {"recent": recent}},
        case["cik"],
        accepted - timedelta(seconds=1),
        accepted,
    )[0]
    if detail := case.get("detail_text"):
        SecFilingsAdapter._apply_primary_document_context(
            evidence,
            f"<html><body>{detail}</body></html>".encode(),
        )
    return evidence


def test_REAL_CATALYST_CORPUS_HAS_25_PRIMARY_SOURCE_CASES():
    fixture = json.loads(FIXTURE_PATH.read_text())
    cases = fixture["cases"]

    assert len(cases) == 25
    assert "real sec catalyst" in fixture["description"].lower()
    assert fixture["verified_on"] == "2026-07-15"
    assert len({case["id"] for case in cases}) == 25
    assert len({case["accession"] for case in cases}) == 25
    assert len({case["ticker"] for case in cases}) == 8
    assert all(case["verified_http_status"] == 200 for case in cases)
    assert {case["research_value"] for case in cases} == {"high", "medium"}


@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
def test_REAL_CATALYST_CLASSIFICATION_PROVENANCE_AND_FRESHNESS(case):
    item = _evidence(case)
    source = item.sources[0]
    accepted = SecFilingsAdapter._parse_datetime(case["accepted_at"])
    expected_url = (
        f"https://www.sec.gov/Archives/edgar/data/{int(case['cik'])}/"
        f"{case['accession'].replace('-', '')}/{case['primary_document']}"
    )

    assert item.context.event_type == case["expected_event_type"]
    assert item.direction.value == case["expected_direction"]
    assert str(source.canonical_url) == expected_url
    assert source.accession_or_record_id == case["accession"]
    assert source.published_at == accepted.astimezone(UTC)
    assert source.observed_at == accepted.astimezone(UTC)
    assert item.timestamp == accepted.astimezone(UTC)


def test_REAL_CATALYST_NEARBY_FILINGS_REMAIN_DISTINCT():
    grouped = {}
    evidence = []
    for case in _cases():
        item = _evidence(case)
        evidence.append(item)
        if group := case.get("distinct_group"):
            grouped.setdefault(group, []).append(item)

    deduplicated = CatalystService._deduplicate(evidence)

    assert len(deduplicated) == 25
    assert set(grouped) == {
        "aapl_q2_results",
        "nvda_q1_results",
        "tsla_q1_results",
        "rklb_may20_filings",
    }
    assert all(len(items) == 2 for items in grouped.values())
    assert all(
        len({str(item.sources[0].canonical_url) for item in items}) == 2
        for items in grouped.values()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
async def test_REAL_CATALYST_DOSSIER_DIRECTION_MATCHES_REVIEWED_CASE(case):
    item = _evidence(case)
    accepted = SecFilingsAdapter._parse_datetime(case["accepted_at"])
    result = AdapterResult(
        family="filings_news",
        provider="sec",
        evidence=[item],
        status=SourceStatus.FRESH,
        collected_at=accepted,
    )
    service = CatalystService(
        [StaticAdapter("filings_news", result, provider="sec")],
        clock=lambda: accepted + timedelta(seconds=1),
    )

    response = await service.evaluate(ToolInput(ticker=case["ticker"], lookback_days=1))

    assert response.edge.direction.value == case["expected_direction"]
