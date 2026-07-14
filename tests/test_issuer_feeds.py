from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.adapters.issuer_feeds import IssuerFeedAdapter
from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.issuer_registry import IssuerFeed
from catalyst_edge_mcp.models import Direction, PolicyDecision, SourceStatus
from tests.conftest import AS_OF

FIXTURE = Path(__file__).parent / "fixtures" / "providers" / "issuer_feed.xml"
FEED = IssuerFeed(
    issuer_key="CIK0001045810",
    issuer_name="NVIDIA Corporation",
    tickers=("NVDA",),
    feed_url="https://nvidianews.nvidia.com/cats/press_release.xml",
    official_hosts=("nvidianews.nvidia.com",),
)


@pytest.mark.asyncio
async def test_PT_ISSUER_FEED_NORMALIZATION_and_conditional_cache(tmp_path):
    clock = [AS_OF]
    requests = []

    def transport(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200,
                content=FIXTURE.read_bytes(),
                headers={
                    "ETag": '"feed-v1"',
                    "Last-Modified": "Sun, 12 Jul 2026 15:30:00 GMT",
                },
            )
        assert request.headers["if-none-match"] == '"feed-v1"'
        assert request.headers["if-modified-since"] == "Sun, 12 Jul 2026 15:30:00 GMT"
        return httpx.Response(304)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = IssuerFeedAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": FEED},
            client=client,
            clock=lambda: clock[0],
        )
        first = await adapter.collect("NVDA", 14)
        clock[0] += timedelta(seconds=601)
        second = await adapter.collect("NVDA", 14)

    assert len(requests) == 2
    assert first.status == SourceStatus.FRESH
    assert second.status == SourceStatus.FRESH
    assert len(first.evidence) == len(second.evidence) == 1
    item = first.evidence[0]
    assert item.signal == "issuer_release"
    assert item.direction == Direction.NEUTRAL
    assert item.source_quality == 0.95
    assert item.sources[0].source_id == "issuer_feed"
    assert item.sources[0].source_tier == "issuer_primary"
    assert item.sources[0].policy_decision == PolicyDecision.APPROVED_PER_REGISTRY
    assert str(item.sources[0].canonical_url) == (
        "https://nvidianews.nvidia.com/news/nvidia-announces-new-platform"
    )
    assert item.sources[0].raw_sha256
    assert item.sources[0].parser_version == "issuer-feed-v1"
    assert "secret-body-marker" not in item.model_dump_json()


@pytest.mark.asyncio
async def test_issuer_feed_failure_returns_typed_stale_cached_result(tmp_path):
    clock = [AS_OF]
    calls = 0

    def transport(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, content=FIXTURE.read_bytes())
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = IssuerFeedAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": FEED},
            client=client,
            clock=lambda: clock[0],
        )
        await adapter.collect("NVDA", 14)
        clock[0] += timedelta(seconds=601)
        result = await adapter.collect("NVDA", 14)

    assert result.status == SourceStatus.STALE
    assert result.degraded is True
    assert len(result.evidence) == 1
    assert "HTTPStatusError" in result.warnings[0]


@pytest.mark.asyncio
async def test_issuer_feed_malformed_xml_is_schema_error(tmp_path):
    def transport(request):
        return httpx.Response(200, content=b"<not-a-feed>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await IssuerFeedAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": FEED},
            client=client,
            clock=lambda: AS_OF,
        ).collect("NVDA", 14)

    assert result.status == SourceStatus.SCHEMA_ERROR
    assert result.evidence == []


@pytest.mark.asyncio
async def test_unregistered_issuer_makes_no_request(tmp_path):
    def transport(request):
        raise AssertionError("unregistered feeds must not be requested")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        adapter = IssuerFeedAdapter(
            str(tmp_path / "events.sqlite3"), registry={}, client=client, clock=lambda: AS_OF
        )
        result = await adapter.collect("RKLB", 14)

    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert result.evidence == []
    assert "No reviewed issuer feed" in result.warnings[0]
    assert not (tmp_path / "events.sqlite3").exists()


@pytest.mark.asyncio
async def test_issuer_feed_rejects_entry_links_outside_reviewed_hosts(tmp_path):
    content = FIXTURE.read_bytes().replace(
        b"https://nvidianews.nvidia.com/news/nvidia-announces-new-platform?utm_source=rss",
        b"https://attacker.example/fake-release",
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=content))
    ) as client:
        result = await IssuerFeedAdapter(
            str(tmp_path / "events.sqlite3"),
            registry={"NVDA": FEED},
            client=client,
            clock=lambda: AS_OF,
        ).collect("NVDA", 14)

    assert result.status == SourceStatus.SCHEMA_ERROR
    assert result.evidence == []


def test_event_store_does_not_retain_feed_bodies(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    assert "secret-body-marker" not in store.export_event_graph()
