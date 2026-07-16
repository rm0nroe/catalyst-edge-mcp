from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.adapters.gdelt import GDELT_ENDPOINT, GdeltAdapter
from catalyst_edge_mcp.discovery_registry import DiscoveryIssuer
from catalyst_edge_mcp.evidence_store import EventObservation, EvidenceStore
from catalyst_edge_mcp.models import Direction, PolicyDecision, SourceStatus
from catalyst_edge_mcp.registry_config import publisher_quality_for_domain
from catalyst_edge_mcp.registry_models import PublisherDomainQuality
from tests.conftest import AS_OF

FIXTURE = Path(__file__).parent / "fixtures" / "providers" / "gdelt.json"
ISSUER = DiscoveryIssuer(
    issuer_key="CIK0001045810",
    issuer_name="NVIDIA Corporation",
    tickers=("NVDA",),
    query_aliases=("NVIDIA", "NVIDIA Corporation"),
)


def _adapter(tmp_path, client, **kwargs):
    return GdeltAdapter(
        str(tmp_path / "events.sqlite3"),
        registry={"NVDA": ISSUER},
        client=client,
        gate=ProviderGate(concurrency=1),
        clock=kwargs.pop("clock", lambda: AS_OF),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_PT_GDELT_NORMALIZATION_is_neutral_metadata_only(tmp_path):
    requests = []

    def transport(request):
        requests.append(request)
        return httpx.Response(200, content=FIXTURE.read_bytes())

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert len(requests) == 1
    assert str(requests[0].url).startswith(GDELT_ENDPOINT)
    assert requests[0].url.params["mode"] == "artlist"
    assert requests[0].url.params["format"] == "json"
    assert requests[0].url.params["maxrecords"] == "50"
    assert requests[0].url.params["timespan"] == "14d"
    assert requests[0].url.params["query"] == '("NVIDIA" OR "NVIDIA Corporation")'
    assert result.status == SourceStatus.FRESH
    assert len(result.evidence) == 1
    item = result.evidence[0]
    assert item.signal == "publisher_link_discovery"
    assert item.context.event_type == "publisher_coverage"
    assert item.context.materiality == "discovery_only"
    assert item.direction == Direction.NEUTRAL
    assert item.source_quality == 0.60
    assert item.sources[0].source_id == "gdelt"
    assert item.sources[0].source_tier == "discovery"
    assert item.sources[0].policy_decision == PolicyDecision.APPROVED_DISCOVERY
    assert str(item.sources[0].canonical_url) == (
        "https://publisher.example/nvidia-announces-new-platform"
    )
    assert item.sources[0].raw_sha256
    assert item.sources[0].parser_version == "gdelt-doc-v1"
    serialized = item.model_dump_json()
    assert "secret-publisher-body-marker" not in serialized
    assert "secret-publisher-content-marker" not in serialized


@pytest.mark.asyncio
async def test_gdelt_applies_reviewed_publisher_domain_quality_tier(tmp_path):
    quality = PublisherDomainQuality(
        domain="publisher.example",
        tier="wire_service",
        quality=0.70,
        reviewed_on="2026-07-15",
        review_note="Fixture-reviewed publisher.",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=FIXTURE.read_bytes())
        )
    ) as client:
        result = await _adapter(
            tmp_path,
            client,
            publisher_quality_registry={"publisher.example": quality},
        ).collect("NVDA", 14)

    item = result.evidence[0]
    assert item.source_quality == 0.70
    assert item.raw_signal["publisher_domain"] == "publisher.example"
    assert item.raw_signal["publisher_quality_tier"] == "wire_service"


def test_publisher_domain_quality_uses_exact_or_subdomain_boundary_only():
    quality = PublisherDomainQuality(
        domain="reuters.com",
        tier="wire_service",
        quality=0.70,
        reviewed_on="2026-07-15",
        review_note="Fixture-reviewed publisher.",
    )
    registry = {"reuters.com": quality}

    assert publisher_quality_for_domain("www.reuters.com", registry) is quality
    assert publisher_quality_for_domain("notreuters.com", registry) is None


@pytest.mark.asyncio
async def test_gdelt_empty_result_is_typed_no_observations(tmp_path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"articles": []}))
    ) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert result.evidence == []


@pytest.mark.asyncio
async def test_gdelt_malformed_json_is_schema_error_without_body_leak(tmp_path):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"secret malformed response")
        )
    ) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert result.status == SourceStatus.SCHEMA_ERROR
    assert result.degraded is True
    assert "secret malformed response" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_gdelt_429_is_typed_and_defers_future_starts(tmp_path):
    class RecordingGate(ProviderGate):
        def __init__(self):
            super().__init__(concurrency=1)
            self.deferred = []

        async def defer_for(self, seconds):
            self.deferred.append(seconds)

    gate = RecordingGate()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": "30"})
        )
    ) as client:
        adapter = GdeltAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": ISSUER},
            client=client,
            gate=gate,
            clock=lambda: AS_OF,
        )
        result = await adapter.collect("NVDA", 14)

    assert result.status == SourceStatus.RATE_LIMITED
    assert gate.deferred == [30.0]


@pytest.mark.asyncio
async def test_gdelt_timeout_returns_typed_cached_degradation(tmp_path):
    clock = [AS_OF]
    calls = 0

    def transport(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, content=FIXTURE.read_bytes())
        raise httpx.ReadTimeout("fixture timeout", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = _adapter(tmp_path, client, clock=lambda: clock[0])
        await adapter.collect("NVDA", 14)
        clock[0] += timedelta(seconds=301)
        result = await adapter.collect("NVDA", 14)

    assert result.status == SourceStatus.TIMEOUT
    assert result.degraded is True
    assert len(result.evidence) == 1
    assert "fixture timeout" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_gdelt_request_path_is_cache_only_and_never_calls_upstream(tmp_path):
    def transport(request):
        raise AssertionError("request-time GDELT must not make a network request")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = _adapter(tmp_path, client, live_refresh=False)
        result = await adapter.collect("NVDA", 14)

    assert result.status == SourceStatus.STALE
    assert result.degraded is True
    assert result.evidence == []
    assert "catalyst-edge-refresh-gdelt" in result.warnings[0]


@pytest.mark.asyncio
async def test_gdelt_request_path_reads_successful_background_cache(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=FIXTURE.read_bytes())
        )
    ) as client:
        refresher = GdeltAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": ISSUER},
            store=store,
            client=client,
            gate=ProviderGate(concurrency=1),
            clock=lambda: AS_OF,
        )
        await refresher.collect("NVDA", 14)

    def transport(request):
        raise AssertionError("request-time GDELT must use the successful cache")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        request_adapter = GdeltAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": ISSUER},
            store=store,
            client=client,
            gate=ProviderGate(concurrency=1),
            clock=lambda: AS_OF,
            live_refresh=False,
        )
        result = await request_adapter.collect("NVDA", 14)

    assert result.status == SourceStatus.FRESH
    assert len(result.evidence) == 1


@pytest.mark.asyncio
async def test_gdelt_request_path_exposes_stale_background_cache_age(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    store.update_collector_state(
        source_id="gdelt",
        issuer_key=ISSUER.issuer_key,
        feed_url=GDELT_ENDPOINT,
        status=SourceStatus.FRESH.value,
        checked_at=AS_OF - timedelta(seconds=901),
        succeeded=True,
    )
    adapter = GdeltAdapter(
        str(tmp_path / "events.sqlite3"),
        registry={"NVDA": ISSUER},
        store=store,
        clock=lambda: AS_OF,
        live_refresh=False,
        max_cache_age_seconds=900,
    )

    result = await adapter.collect("NVDA", 14)

    assert result.status is SourceStatus.STALE
    assert result.degraded is True
    assert "901 seconds ago" in result.warnings[0]


@pytest.mark.asyncio
async def test_gdelt_request_path_exposes_failed_background_refresh(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    store.update_collector_state(
        source_id="gdelt",
        issuer_key=ISSUER.issuer_key,
        feed_url=GDELT_ENDPOINT,
        status=SourceStatus.FRESH.value,
        checked_at=AS_OF - timedelta(seconds=60),
        succeeded=True,
    )
    store.update_collector_state(
        source_id="gdelt",
        issuer_key=ISSUER.issuer_key,
        feed_url=GDELT_ENDPOINT,
        status=SourceStatus.TIMEOUT.value,
        checked_at=AS_OF,
        succeeded=False,
        error_class="ReadTimeout",
    )
    adapter = GdeltAdapter(
        str(tmp_path / "events.sqlite3"),
        registry={"NVDA": ISSUER},
        store=store,
        clock=lambda: AS_OF,
        live_refresh=False,
    )

    result = await adapter.collect("NVDA", 14)

    assert result.status is SourceStatus.TIMEOUT
    assert result.degraded is True
    assert "ReadTimeout" in result.warnings[0]


@pytest.mark.asyncio
async def test_gdelt_rejects_redirect_outside_official_endpoint(tmp_path):
    def transport(request):
        if request.url.host == "api.gdeltproject.org":
            return httpx.Response(
                302, headers={"Location": "https://attacker.example/api/v2/doc/doc"}
            )
        return httpx.Response(200, json={"articles": []})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport), follow_redirects=True
    ) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert result.status == SourceStatus.SCHEMA_ERROR
    assert result.evidence == []


@pytest.mark.asyncio
async def test_unregistered_gdelt_ticker_makes_no_request(tmp_path):
    def transport(request):
        raise AssertionError("unregistered aliases must not be requested")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = GdeltAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={},
            client=client,
            gate=ProviderGate(concurrency=1),
            clock=lambda: AS_OF,
        )
        result = await adapter.collect("MSFT", 14)

    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert result.evidence == []
    assert not (tmp_path / "events.sqlite3").exists()


def test_gdelt_graph_merge_preserves_issuer_primary_ranking_and_source_views(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    store.ingest_event(
        EventObservation(
            source_id="gdelt",
            source_name="GDELT discovery (publisher.example)",
            source_tier="discovery",
            issuer_key=ISSUER.issuer_key,
            record_id="https://publisher.example/platform",
            canonical_url="https://publisher.example/platform",
            title="NVIDIA Announces New Platform",
            published_at=AS_OF,
            observed_at=AS_OF,
            retrieved_at=AS_OF,
            raw_sha256="a" * 64,
            parser_version="gdelt-doc-v1",
            policy_decision=PolicyDecision.APPROVED_DISCOVERY,
        )
    )
    merged = store.ingest_event(
        EventObservation(
            source_id="issuer_feed",
            source_name="NVIDIA official feed",
            source_tier="issuer_primary",
            issuer_key=ISSUER.issuer_key,
            record_id="issuer-platform",
            canonical_url="https://nvidianews.nvidia.com/news/platform",
            title="NVIDIA Announces New Platform",
            published_at=AS_OF + timedelta(hours=1),
            observed_at=AS_OF,
            retrieved_at=AS_OF,
            raw_sha256="b" * 64,
            parser_version="issuer-feed-v1",
            policy_decision=PolicyDecision.APPROVED_PER_REGISTRY,
        )
    )

    assert merged.primary_source.source_id == "issuer_feed"
    discovery_view = store.list_events_for_source(
        ISSUER.issuer_key, "gdelt", AS_OF - timedelta(days=1)
    )[0]
    issuer_view = store.list_events_for_source(
        ISSUER.issuer_key, "issuer_feed", AS_OF - timedelta(days=1)
    )[0]
    assert discovery_view.event_id == issuer_view.event_id == merged.event_id
    assert discovery_view.primary_source.source_id == "gdelt"
    assert issuer_view.primary_source.source_id == "issuer_feed"


@pytest.mark.asyncio
async def test_gdelt_long_publisher_url_is_bounded_for_public_source_contract(tmp_path):
    long_url = "https://publisher.example/" + "segment-" * 40
    payload = {
        "articles": [
            {
                "url": long_url,
                "title": "NVIDIA Announces a New Platform",
                "seendate": "20260712T153000Z",
                "domain": "publisher.example",
            }
        ]
    }
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert len(result.evidence) == 1
    assert len(result.evidence[0].sources[0].accession_or_record_id) == 160
