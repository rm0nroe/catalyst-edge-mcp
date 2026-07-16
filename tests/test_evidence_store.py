from datetime import timedelta

from catalyst_edge_mcp.evidence_store import (
    EventObservation,
    EvidenceStore,
    canonicalize_url,
    normalize_title,
)
from catalyst_edge_mcp.models import PolicyDecision
from tests.conftest import AS_OF


def _observation(
    *,
    source_id="gdelt",
    source_name="Discovery source",
    source_tier="discovery",
    record_id="record-1",
    url="https://publisher.example/event",
    title="Company reports revenue of 10 million for quarter",
    published_at=AS_OF,
    policy_decision=PolicyDecision.APPROVED_DISCOVERY,
):
    return EventObservation(
        source_id=source_id,
        source_name=source_name,
        source_tier=source_tier,
        issuer_key="CIK0001045810",
        record_id=record_id,
        canonical_url=url,
        title=title,
        published_at=published_at,
        observed_at=AS_OF,
        retrieved_at=AS_OF,
        raw_sha256="a" * 64,
        parser_version="fixture-v1",
        policy_decision=policy_decision,
    )


def test_event_store_creates_required_wal_schema(tmp_path):
    store = EvidenceStore(str(tmp_path / "evidence.sqlite3"))

    assert store.journal_mode() == "wal"
    assert {
        "source_observation",
        "canonical_event",
        "event_source",
        "insider_transaction",
        "insider_cluster",
        "social_bucket",
        "collector_state",
        "source_policy",
    } <= store.table_names()


def test_title_normalization_preserves_unicode_alphanumeric_text():
    assert normalize_title("Уход спонсоров Гейтса: последние новости") == (
        "уход спонсоров гейтса последние новости"
    )
    assert normalize_title("NVIDIA & Partners: Q2 +10%") == "nvidia and partners q2 10%"


def test_event_graph_exact_fuzzy_dedupe_and_primary_source_ranking(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    discovery = store.ingest_event(_observation())
    issuer = store.ingest_event(
        _observation(
            source_id="issuer_feed",
            source_name="NVIDIA official feed",
            source_tier="issuer_primary",
            record_id="issuer-1",
            url="https://nvidianews.nvidia.com/news/company-quarter",
            published_at=AS_OF + timedelta(hours=1),
            policy_decision=PolicyDecision.APPROVED_PER_REGISTRY,
        )
    )

    assert issuer.event_id == discovery.event_id
    assert issuer.primary_source.source_id == "issuer_feed"
    assert issuer.related_urls == ("https://publisher.example/event",)

    regulator = store.ingest_event(
        _observation(
            source_id="sec",
            source_name="SEC EDGAR",
            source_tier="primary_regulator",
            record_id="0001045810-26-000001",
            url="https://www.sec.gov/Archives/edgar/data/1045810/filing.htm",
            published_at=AS_OF + timedelta(hours=2),
            policy_decision=PolicyDecision.APPROVED,
        )
    )
    assert regulator.event_id == discovery.event_id
    assert regulator.primary_source.source_id == "sec"
    assert regulator.source_count == 3
    assert regulator.source_tiers == ("discovery", "issuer_primary", "primary_regulator")
    assert set(regulator.related_urls) == {
        "https://publisher.example/event",
        "https://nvidianews.nvidia.com/news/company-quarter",
    }

    exact = store.ingest_event(
        _observation(
            source_id="issuer_feed",
            source_name="NVIDIA official feed",
            source_tier="issuer_primary",
            record_id="issuer-2",
            url=(
                "https://nvidianews.nvidia.com/news/company-quarter"
                "?utm_source=email&fbclid=tracking"
            ),
            policy_decision=PolicyDecision.APPROVED_PER_REGISTRY,
        )
    )
    assert exact.event_id == discovery.event_id
    assert exact.primary_source.source_id == "sec"


def test_event_graph_links_corrections_as_versions(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    original = store.ingest_event(_observation())
    correction = store.ingest_event(
        _observation(
            title="Correction: Company reports revenue of 12 million for quarter",
            published_at=AS_OF + timedelta(hours=2),
        )
    )

    assert correction.event_id != original.event_id
    assert correction.correction_of_event_id == original.event_id
    assert correction.version == 2
    assert correction.source_count == 1


def test_canonical_url_normalization_removes_tracking_and_fragments():
    assert (
        canonicalize_url("https://Example.com//news/item/?b=2&utm_source=rss&a=1#section")
        == "https://example.com/news/item?a=1&b=2"
    )
