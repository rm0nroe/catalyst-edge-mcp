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


def _adapter(tmp_path, client=None, *, store=None, clock=lambda: AS_OF, live_refresh=True):
    return BlueskyAdapter(
        str(tmp_path / "events.sqlite3"),
        registry={"NVDA": ISSUER},
        store=store,
        client=client,
        gate=ProviderGate(concurrency=1),
        clock=clock,
        live_refresh=live_refresh,
    )


def _seed_daily_bucket(store, bucket_at, *, posts, prefix, coverage_state="adequate"):
    store.record_social_bucket(
        issuer_key=ISSUER.issuer_key,
        source_id="bluesky",
        bucket_at=bucket_at,
        metrics={
            "post_count": posts,
            "unique_authors": 3,
            "uri_sha256s": [f"uri-{prefix}-{index}" for index in range(posts)],
            "author_sha256s": [f"author-{prefix}-{index}" for index in range(3)],
            "representative_urls": [f"https://bsky.app/profile/{prefix}.example/post/1"],
            "newest_at": (bucket_at + timedelta(hours=12)).isoformat(),
            "raw_sha256": "a" * 64,
            "coverage": 1.0 if coverage_state == "adequate" else 0.0,
            "coverage_state": coverage_state,
            "partial_population": True,
            "search_model": "ranked_incomplete",
            "window_start": bucket_at.isoformat(),
            "window_end": (bucket_at + timedelta(days=1)).isoformat(),
        },
    )


def _mark_fresh(store, checked_at=AS_OF):
    store.update_collector_state(
        source_id="bluesky",
        issuer_key=ISSUER.issuer_key,
        feed_url="https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        status=SourceStatus.FRESH.value,
        checked_at=checked_at,
        succeeded=True,
    )


@pytest.mark.asyncio
async def test_forward_collector_uses_official_fallback_and_retains_no_post_bodies(tmp_path):
    requests = []

    def transport(request):
        requests.append(request)
        if request.url.host == "public.api.bsky.app":
            return httpx.Response(403)
        return httpx.Response(200, content=FIXTURE.read_bytes())

    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    def clock():
        return AS_OF + timedelta(days=1)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await _adapter(tmp_path, client, store=store, clock=clock).collect("NVDA", 14)

    assert [request.url.host for request in requests] == [
        "public.api.bsky.app",
        "api.bsky.app",
    ]
    assert requests[0].url.path == "/xrpc/app.bsky.feed.searchPosts"
    assert requests[0].url.params["q"] == '$NVDA | "NVIDIA"'
    assert "cursor" not in requests[0].url.params
    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert "warm_up: 1 of 14" in result.warnings[0]
    buckets = store.social_buckets(ISSUER.issuer_key, "bluesky", AS_OF - timedelta(days=1))
    assert buckets[0]["post_count"] == 2
    assert buckets[0]["unique_authors"] == 2
    assert buckets[0]["coverage_state"] == "adequate"
    assert len(buckets[0]["representative_urls"]) == 2
    assert "secret-social-body-marker" not in str(buckets)
    assert b"secret-social-body-marker" not in (tmp_path / "events.sqlite3").read_bytes()


@pytest.mark.asyncio
async def test_request_path_is_cache_only_and_emits_neutral_forward_attention(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    today = AS_OF.replace(hour=0, minute=0, second=0, microsecond=0)
    for index in range(14):
        _seed_daily_bucket(
            store,
            today - timedelta(days=14 - index),
            posts=1 if index < 7 else 2,
            prefix=f"day{index}",
        )
    _mark_fresh(store)

    def transport(request):
        raise AssertionError("request-time Bluesky must never call AppView")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await _adapter(
            tmp_path, client, store=store, live_refresh=False
        ).collect("NVDA", 14)

    assert result.status == SourceStatus.FRESH
    assert len(result.evidence) == 1
    item = result.evidence[0]
    assert item.signal == "attention_change"
    assert item.direction == Direction.NEUTRAL
    assert item.change.baseline_value == 7
    assert item.change.current_value == 14
    assert item.sources[0].source_id == "bluesky"
    assert item.sources[0].source_tier == "partial_attention"
    assert item.sources[0].policy_decision == PolicyDecision.APPROVED_PARTIAL_ATTENTION
    assert "ranked, incomplete partial public attention" in item.notes.lower()
    assert item.raw_signal["unique_authors"] == 21


@pytest.mark.asyncio
async def test_forward_first_page_truncation_fails_closed_without_cursor_request(tmp_path):
    requests = []

    def transport(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "posts": [],
                "hitsTotal": 183,
                "cursor": "must-not-be-used",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert len(requests) == 1
    assert result.status == SourceStatus.STALE
    assert result.degraded is True
    assert "ranked first page reported truncation" in result.warnings[0]


@pytest.mark.asyncio
async def test_cursor_with_fully_returned_hit_total_is_an_adequate_ranked_bucket(tmp_path):
    payload = {
        "posts": [
            {
                "uri": "at://did:plc:author/app.bsky.feed.post/one",
                "author": {"did": "did:plc:author", "handle": "author.example"},
                "record": {
                    "text": "$NVDA exact match",
                    "createdAt": (AS_OF - timedelta(hours=1)).isoformat(),
                },
            }
        ],
        "hitsTotal": 1,
        "cursor": "unconditional-token",
    }
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        result = await _adapter(tmp_path, client).collect("NVDA", 14)

    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert "warm_up: 1 of 14" in result.warnings[0]


@pytest.mark.asyncio
async def test_recheck_with_disappeared_uri_hash_fails_closed(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    calls = 0

    def transport(request):
        nonlocal calls
        calls += 1
        payload = {
            "posts": [
                {
                    "uri": f"at://did:plc:author/app.bsky.feed.post/{index}",
                    "author": {"did": f"did:plc:{index}", "handle": f"a{index}.example"},
                    "record": {
                        "text": "$NVDA exact match",
                        "createdAt": (AS_OF - timedelta(hours=1)).isoformat(),
                    },
                }
                for index in range(2 if calls == 1 else 1)
            ]
        }
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = _adapter(
            tmp_path,
            client,
            store=store,
            clock=lambda: AS_OF + timedelta(days=1),
        )
        first = await adapter.collect("NVDA", 14)
        second = await adapter.collect("NVDA", 14)

    assert first.status == SourceStatus.NO_OBSERVATIONS
    assert second.status == SourceStatus.STALE
    assert second.degraded is True
    assert "URI hashes disappeared" in second.warnings[0]


@pytest.mark.asyncio
async def test_cache_warmup_gap_outage_and_staleness_are_explicit(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    today = AS_OF.replace(hour=0, minute=0, second=0, microsecond=0)
    for index in range(13):
        _seed_daily_bucket(
            store,
            today - timedelta(days=14 - index),
            posts=1,
            prefix=f"day{index}",
        )
    _mark_fresh(store)
    adapter = _adapter(tmp_path, store=store, live_refresh=False)

    gap = await adapter.collect("NVDA", 14)
    assert gap.status == SourceStatus.STALE
    assert "coverage gap: 13 of 14" in gap.warnings[0]

    _seed_daily_bucket(
        store,
        today - timedelta(days=1),
        posts=0,
        prefix="outage",
        coverage_state="rate_limited",
    )
    outage = await adapter.collect("NVDA", 14)
    assert outage.status == SourceStatus.STALE
    assert "13 of 14 daily buckets" in outage.warnings[0]

    _mark_fresh(store, checked_at=AS_OF - timedelta(seconds=43_201))
    stale = await adapter.collect("NVDA", 14)
    assert stale.status == SourceStatus.STALE
    assert "43201 seconds ago" in stale.warnings[0]


@pytest.mark.asyncio
async def test_bluesky_outage_is_persisted_without_upstream_detail(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))

    def transport(request):
        raise httpx.ReadTimeout("secret upstream detail", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await _adapter(tmp_path, client, store=store).collect("NVDA", 14)

    assert result.status == SourceStatus.TIMEOUT
    assert result.degraded is True
    assert "secret upstream detail" not in result.model_dump_json()
    buckets = store.social_buckets(ISSUER.issuer_key, "bluesky", AS_OF - timedelta(days=2))
    assert buckets[0]["coverage"] == 0.0
    assert buckets[0]["coverage_state"] == "timeout"


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
