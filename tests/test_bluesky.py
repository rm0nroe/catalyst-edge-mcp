from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.adapters.bluesky import BlueskyAdapter
from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.models import Direction, PolicyDecision, SourceStatus
from catalyst_edge_mcp.social_registry import SocialIssuer
from tests.conftest import AS_OF

FIXTURE = Path(__file__).parent / "fixtures" / "providers" / "bluesky.json"
ISSUER = SocialIssuer(
    issuer_key="CIK0001045810",
    issuer_name="NVIDIA Corporation",
    tickers=("NVDA",),
    exact_aliases=("NVIDIA",),
)


def _adapter(tmp_path, client, *, store=None, clock=lambda: AS_OF):
    return BlueskyAdapter(
        str(tmp_path / "events.sqlite3"),
        registry={"NVDA": ISSUER},
        store=store,
        client=client,
        gate=ProviderGate(concurrency=1),
        clock=clock,
    )


@pytest.mark.asyncio
async def test_PT_BLUESKY_HOST_FALLBACK_and_metadata_only_warmup(tmp_path):
    requests = []

    def transport(request):
        requests.append(request)
        if request.url.host == "public.api.bsky.app":
            return httpx.Response(403)
        return httpx.Response(200, content=FIXTURE.read_bytes())

    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await _adapter(tmp_path, client, store=store).collect("NVDA", 14)

    assert [request.url.host for request in requests] == [
        "public.api.bsky.app",
        "api.bsky.app",
    ]
    assert all(request.url.path == "/xrpc/app.bsky.feed.searchPosts" for request in requests)
    assert requests[0].url.params["q"] == '("$NVDA" OR "NVIDIA")'
    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert result.evidence == []
    assert "warming up" in result.warnings[0]
    buckets = store.social_buckets(ISSUER.issuer_key, "bluesky", AS_OF - timedelta(days=1))
    assert buckets[0]["post_count"] == 2
    assert buckets[0]["unique_authors"] == 2
    assert "secret-social-body-marker" not in str(buckets)


@pytest.mark.asyncio
async def test_bluesky_emits_neutral_attention_only_after_baseline(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    store.record_social_bucket(
        issuer_key=ISSUER.issuer_key,
        source_id="bluesky",
        bucket_at=AS_OF - timedelta(days=14),
        metrics={"post_count": 6, "unique_authors": 5, "coverage": 1.0},
    )
    store.record_social_bucket(
        issuer_key=ISSUER.issuer_key,
        source_id="bluesky",
        bucket_at=AS_OF - timedelta(days=6),
        metrics={"post_count": 8, "unique_authors": 7, "coverage": 1.0},
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=FIXTURE.read_bytes())
        )
    ) as client:
        result = await _adapter(tmp_path, client, store=store).collect("NVDA", 14)

    assert result.status == SourceStatus.FRESH
    assert len(result.evidence) == 1
    item = result.evidence[0]
    assert item.signal == "attention_change"
    assert item.direction == Direction.NEUTRAL
    assert item.change.baseline_value == 6
    assert item.change.current_value == 10
    assert item.sources[0].source_id == "bluesky"
    assert item.sources[0].source_tier == "partial_attention"
    assert item.sources[0].policy_decision == PolicyDecision.APPROVED_PARTIAL_ATTENTION
    assert str(item.sources[0].url) == "https://bsky.app/profile/alpha.example/post/one"
    assert "secret-social-body-marker" not in item.model_dump_json()


@pytest.mark.asyncio
async def test_bluesky_outage_stays_neutral_and_counts_against_coverage(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))

    def transport(request):
        raise httpx.ReadTimeout("secret upstream detail", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await _adapter(tmp_path, client, store=store).collect("NVDA", 14)

    assert result.status == SourceStatus.TIMEOUT
    assert result.degraded is True
    assert result.evidence == []
    assert "secret upstream detail" not in result.model_dump_json()
    buckets = store.social_buckets(ISSUER.issuer_key, "bluesky", AS_OF - timedelta(days=1))
    assert buckets[0]["coverage"] == 0.0


@pytest.mark.asyncio
async def test_bluesky_rejects_redirect_outside_documented_hosts(tmp_path):
    def transport(request):
        if request.url.host in {"public.api.bsky.app", "api.bsky.app"}:
            return httpx.Response(302, headers={"Location": "https://attacker.example/xrpc"})
        return httpx.Response(200, json={"posts": []})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport), follow_redirects=True
    ) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert result.status == SourceStatus.SCHEMA_ERROR
    assert result.evidence == []


@pytest.mark.asyncio
async def test_bluesky_429_uses_returned_rate_limit_header(tmp_path):
    class RecordingGate(ProviderGate):
        def __init__(self):
            super().__init__(concurrency=1)
            self.deferred = []

        async def defer_for(self, seconds):
            self.deferred.append(seconds)

    gate = RecordingGate()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": "20"})
        )
    ) as client:
        adapter = BlueskyAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": ISSUER},
            client=client,
            gate=gate,
            clock=lambda: AS_OF,
        )
        result = await adapter.collect("NVDA", 14)

    assert result.status == SourceStatus.RATE_LIMITED
    assert gate.deferred == [20.0]


@pytest.mark.asyncio
async def test_unregistered_bluesky_ticker_makes_no_request(tmp_path):
    def transport(request):
        raise AssertionError("unregistered aliases must not be requested")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = BlueskyAdapter(
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
