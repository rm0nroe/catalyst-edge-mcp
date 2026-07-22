from datetime import timedelta

from catalyst_edge_mcp.evidence_store import (
    EntityMatchAudit,
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
        "event_claim",
        "claim_source",
        "insider_transaction",
        "insider_cluster",
        "social_bucket",
        "collector_state",
        "source_policy",
        "entity_match_audit",
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
    assert regulator.claim_id.startswith("clm_")
    assert len(regulator.supporting_source_ids) == 3
    page = store.claim_sources(regulator.claim_id, limit=2)
    assert page.total_sources == 3
    assert len(page.sources) == 2
    assert page.next_cursor is not None
    second_page = store.claim_sources(
        regulator.claim_id, cursor=page.next_cursor, limit=2
    )
    assert len(second_page.sources) == 1
    assert second_page.next_cursor is None
    assert {
        item.accession_or_record_id for item in [*page.sources, *second_page.sources]
    } == {"record-1", "issuer-1", "0001045810-26-000001"}
    assert {
        item.source_reference_id for item in [*page.sources, *second_page.sources]
    } == set(regulator.supporting_source_ids)

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
    assert correction.claim_id != original.claim_id


def test_existing_event_relations_are_backfilled_into_immutable_claims(tmp_path):
    path = tmp_path / "events.sqlite3"
    store = EvidenceStore(str(path))
    event = store.ingest_event(_observation())
    store._connect().execute("DELETE FROM claim_source")
    store._connect().execute("DELETE FROM event_claim")
    store._connect().commit()
    store.close()

    reopened = EvidenceStore(str(path))
    recovered = reopened.list_events("CIK0001045810", AS_OF - timedelta(days=1))[0]

    assert recovered.claim_id == event.claim_id
    assert recovered.source_count == 1
    assert reopened.claim_sources(recovered.claim_id).total_sources == 1


def test_canonical_url_normalization_removes_tracking_and_fragments():
    assert (
        canonicalize_url("https://Example.com//news/item/?b=2&utm_source=rss&a=1#section")
        == "https://example.com/news/item?a=1&b=2"
    )


def _entity_audit(ruleset_version: str) -> EntityMatchAudit:
    return EntityMatchAudit(
        source_id="gdelt",
        issuer_key="CIK0001318605",
        document_id="42",
        canonical_url="https://publisher.example/tesla-candidate",
        published_at=AS_OF,
        observed_at=AS_OF,
        retrieved_at=AS_OF,
        toc_sha256="a" * 64,
        context_sha256="b" * 64,
        ruleset_version=ruleset_version,
        accepted=False,
        reason_code="negative_context",
        selected_rule_id=None,
        selected_rule_version=None,
        candidate_rule_ids=("tesla_brand_contextual",),
        matched_aliases=("Tesla",),
        required_context_matches=(),
        negative_context_matches=("Nikola",),
    )


def test_entity_match_audit_is_append_only_idempotent_and_ruleset_versioned(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))

    assert store.record_entity_match_audit(_entity_audit("entity-rules-v2:first"))
    assert not store.record_entity_match_audit(_entity_audit("entity-rules-v2:first"))
    assert store.record_entity_match_audit(_entity_audit("entity-rules-v2:second"))

    audits = store.entity_match_audits("CIK0001318605")
    assert [item["ruleset_version"] for item in audits] == [
        "entity-rules-v2:first",
        "entity-rules-v2:second",
    ]
    assert all(item["matched_aliases"] == ("Tesla",) for item in audits)
    assert store.entity_match_audit_summary("CIK0001318605") == {
        "candidate_documents": 2,
        "accepted_documents": 0,
        "rejected_documents": 2,
        "rejection_reasons": {"negative_context": 2},
    }
