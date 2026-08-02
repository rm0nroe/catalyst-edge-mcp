from datetime import datetime

import pytest

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.evidence_store import EventObservation, EvidenceStore
from catalyst_edge_mcp.models import PolicyDecision
from scripts.run_design_partner_demo import _paginate_claim, _requests


def test_demo_requires_five_unique_valid_tickers():
    requests = _requests(["aapl", "NVDA", "TSLA", "RKLB", "BRK.B"], 14)
    assert [request.ticker for request in requests] == [
        "AAPL",
        "NVDA",
        "TSLA",
        "RKLB",
        "BRK.B",
    ]
    with pytest.raises(ValueError, match="five unique tickers"):
        _requests(["AAPL", "AAPL", "TSLA", "RKLB", "BRK.B"], 14)


def test_demo_paginates_every_claim_source(tmp_path):
    store = EvidenceStore(str(tmp_path / "evidence.sqlite3"))
    as_of = datetime(2026, 8, 2, tzinfo=UTC)
    event = None
    for index, source_id in enumerate(("gdelt", "issuer_feed", "sec"), start=1):
        event = store.ingest_event(
            EventObservation(
                source_id=source_id,
                source_name=f"Source {index}",
                source_tier=f"tier_{index}",
                issuer_key="CIK0001045810",
                record_id=f"record-{index}",
                canonical_url=f"https://example.com/source-{index}",
                title="NVIDIA reports the same material event",
                published_at=as_of,
                observed_at=as_of,
                retrieved_at=as_of,
                raw_sha256=str(index) * 64,
                parser_version="fixture-v1",
                policy_decision=PolicyDecision.APPROVED,
            )
        )

    assert event is not None
    result = _paginate_claim(store, tmp_path, "NVDA", event.claim_id)

    assert result["complete"] is True
    assert result["total_sources"] == 3
    assert result["returned_source_count"] == 3
    assert len(result["page_files"]) == 3
