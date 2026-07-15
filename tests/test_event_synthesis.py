import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from catalyst_edge_mcp.adapters import StaticAdapter
from catalyst_edge_mcp.models import PolicyDecision, RiskMode, Source, ToolInput
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from catalyst_edge_mcp.sec_ownership import SecInsiderAdapter
from catalyst_edge_mcp.service import CatalystService
from tests.conftest import AS_OF, make_result

FIXTURES = Path(__file__).parent / "fixtures" / "sec"


def _json_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _rklb_form144():
    fixture = _json_fixture("rklb_form144_2026_07_06.json")
    accepted_at = datetime.fromisoformat(fixture["accepted_at"].replace("Z", "+00:00"))
    accession = fixture["accession"]
    url = (
        "https://www.sec.gov/Archives/edgar/data/1819994/"
        f"{accession.replace('-', '')}/{fixture['primary_document']}"
    )
    source = Source(
        name="SEC EDGAR",
        source_id="sec",
        source_tier="primary_regulator",
        url=url,
        canonical_url=url,
        accession_or_record_id=accession,
        published_at=accepted_at,
        observed_at=accepted_at,
        retrieved_at=AS_OF,
        parser_version="sec-ownership-v1",
        policy_decision=PolicyDecision.APPROVED,
    )
    return SecInsiderAdapter._form_144_evidence(fixture["facts"], accepted_at, source, accession)


def test_real_rklb_8k_metadata_maps_to_specific_event_context():
    fixture = _json_fixture("rklb_8k_2026_06_29.json")

    evidence = SecFilingsAdapter._normalize_recent(
        fixture,
        fixture["cik"],
        AS_OF - timedelta(days=14),
        AS_OF,
    )[0]

    assert evidence.sources[0].accession_or_record_id == "0001753926-26-001085"
    assert evidence.context.event_type == "material_agreement"
    assert evidence.context.event_label == "Material definitive agreement"
    assert evidence.context.novelty == "new_event"
    assert evidence.context.materiality == "material"
    assert "committed economics" in evidence.context.why_it_matters
    assert "Item 1.01 (Material definitive agreement)" in evidence.change.description


@pytest.mark.asyncio
async def test_real_rklb_cases_generate_evidence_specific_dossier_even_when_sources_hidden():
    filing_fixture = _json_fixture("rklb_8k_2026_06_29.json")
    filing = SecFilingsAdapter._normalize_recent(
        filing_fixture,
        filing_fixture["cik"],
        AS_OF - timedelta(days=14),
        AS_OF,
    )[0]
    form144 = _rklb_form144()
    service = CatalystService(
        [
            StaticAdapter("filings_news", make_result("filings_news", filing)),
            StaticAdapter("insider_trading", make_result("insider_trading", form144)),
        ],
        clock=lambda: AS_OF,
    )

    response = await service.evaluate(
        ToolInput(
            ticker="RKLB",
            include_sources=False,
            risk_mode=RiskMode.ALERT_TRIAGE,
        )
    )

    assert all(not item.sources for item in response.evidence)
    assert "Proposed insider sale notice" in response.summary.headline
    assert "not establish that a disposition was completed" in response.summary.why_it_matters
    assert any("0001753926-26-001085" in check for check in response.next_checks)
    assert any("proposed intent, not execution" in check for check in response.next_checks)
    assert not any("conflicting evidence" in check for check in response.next_checks)
    assert any(
        "later filing changes the proposed terms" in item
        for item in response.summary.what_would_invalidate
    )
