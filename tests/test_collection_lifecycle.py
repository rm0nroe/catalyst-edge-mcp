import asyncio
import json
import sys
from datetime import timedelta

import httpx
import pytest

from catalyst_edge_mcp.collection_lifecycle import (
    BlueskyCollectionLifecycle,
    FreshnessState,
    GdeltCollectionLifecycle,
    health_main,
)
from catalyst_edge_mcp.discovery_registry import DISCOVERY_ISSUER_INDEX
from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.gdelt_web_ngrams import GdeltWebNgramsRefresher
from catalyst_edge_mcp.models import AdapterResult, SourceStatus
from catalyst_edge_mcp.settings import Settings
from catalyst_edge_mcp.social_registry import SOCIAL_ISSUER_INDEX
from tests.conftest import AS_OF


def _settings(tmp_path, **overrides):
    values = {
        "evidence_store_path": str(tmp_path / "events.sqlite3"),
        "gdelt_refresh_interval_seconds": 300,
        "gdelt_refresh_lookback_days": 14,
        "gdelt_freshness_max_age_seconds": 900,
        "bluesky_refresh_interval_seconds": 21600,
        "bluesky_freshness_max_age_seconds": 43200,
    }
    values.update(overrides)
    return Settings(**values)


def test_collection_health_is_explicit_for_never_fresh_stale_failed_and_unregistered(
    tmp_path,
):
    settings = _settings(tmp_path)
    store = EvidenceStore(settings.evidence_store_path)
    lifecycle = GdeltCollectionLifecycle(settings, store=store, clock=lambda: AS_OF)
    issuer = DISCOVERY_ISSUER_INDEX["NVDA"]

    assert lifecycle.health(["NVDA"])[0].freshness is FreshnessState.NEVER_REFRESHED

    store.update_collector_state(
        source_id="gdelt",
        issuer_key=issuer.issuer_key,
        feed_url="https://storage.googleapis.com/data.gdeltproject.org/gdeltv5/weblegacy/ngrams",
        status=SourceStatus.FRESH.value,
        checked_at=AS_OF - timedelta(seconds=60),
        succeeded=True,
    )
    fresh = lifecycle.health(["NVDA"])[0]
    assert fresh.freshness is FreshnessState.FRESH
    assert fresh.last_success_age_seconds == 60

    stale_lifecycle = GdeltCollectionLifecycle(
        settings,
        store=store,
        clock=lambda: AS_OF + timedelta(seconds=901),
    )
    stale = stale_lifecycle.health(["NVDA"])[0]
    assert stale.freshness is FreshnessState.STALE
    assert stale.last_success_age_seconds == 961

    store.update_collector_state(
        source_id="gdelt",
        issuer_key=issuer.issuer_key,
        feed_url="https://storage.googleapis.com/data.gdeltproject.org/gdeltv5/weblegacy/ngrams",
        status=SourceStatus.TIMEOUT.value,
        checked_at=AS_OF,
        succeeded=False,
        error_class="ReadTimeout",
    )
    failed = lifecycle.health(["NVDA"])[0]
    assert failed.freshness is FreshnessState.FAILED
    assert failed.source_status is SourceStatus.TIMEOUT
    assert failed.error_class == "ReadTimeout"

    unregistered = lifecycle.health(["UNKNOWN"])[0]
    assert unregistered.freshness is FreshnessState.UNREGISTERED
    assert unregistered.issuer_key is None


def test_restart_schedules_from_persisted_last_check_without_duplicate_startup_refresh(
    tmp_path,
):
    settings = _settings(tmp_path)
    store = EvidenceStore(settings.evidence_store_path)
    issuer = DISCOVERY_ISSUER_INDEX["NVDA"]
    store.update_collector_state(
        source_id="gdelt",
        issuer_key=issuer.issuer_key,
        feed_url="https://storage.googleapis.com/data.gdeltproject.org/gdeltv5/weblegacy/ngrams",
        status=SourceStatus.FRESH.value,
        checked_at=AS_OF - timedelta(seconds=60),
        succeeded=True,
    )

    lifecycle = GdeltCollectionLifecycle(
        settings,
        tickers=["NVDA"],
        store=store,
        clock=lambda: AS_OF,
    )

    assert lifecycle.seconds_until_refresh() == 240


@pytest.mark.asyncio
async def test_missing_state_runs_bounded_startup_catchup_and_stops_cleanly(tmp_path):
    settings = _settings(tmp_path)
    started = asyncio.Event()

    class RecordingRefresher:
        async def refresh(self, tickers, lookback_days):
            assert tickers == ("NVDA",)
            assert lookback_days == 14
            started.set()
            return {}

    lifecycle = GdeltCollectionLifecycle(
        settings,
        tickers=["NVDA"],
        refresher=RecordingRefresher(),
        clock=lambda: AS_OF,
    )
    lifecycle.start()
    await asyncio.wait_for(started.wait(), timeout=1)

    assert lifecycle.running is True
    await lifecycle.stop()
    assert lifecycle.running is False


@pytest.mark.asyncio
async def test_periodic_lifecycle_recovers_after_unexpected_failed_cycle(tmp_path):
    settings = _settings(tmp_path, gdelt_refresh_interval_seconds=0.01)
    recovered = asyncio.Event()

    class FlakyRefresher:
        def __init__(self):
            self.calls = 0

        async def refresh(self, tickers, lookback_days):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("fixture failure")
            recovered.set()
            return {}

    refresher = FlakyRefresher()
    lifecycle = GdeltCollectionLifecycle(
        settings,
        tickers=["NVDA"],
        refresher=refresher,
        clock=lambda: AS_OF,
    )
    lifecycle.start()
    await asyncio.wait_for(recovered.wait(), timeout=1)
    await lifecycle.stop()

    assert refresher.calls == 2


@pytest.mark.asyncio
async def test_unregistered_lifecycle_ticker_makes_no_network_request(tmp_path):
    requests = []

    def transport(request):
        requests.append(request)
        raise AssertionError("unregistered ticker must not make a request")

    settings = _settings(tmp_path)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        refresher = GdeltWebNgramsRefresher(settings.evidence_store_path, client=client)
        lifecycle = GdeltCollectionLifecycle(
            settings,
            tickers=["UNKNOWN"],
            refresher=refresher,
            clock=lambda: AS_OF,
        )
        assert await lifecycle.run_once() == {}

    assert requests == []


def test_health_command_emits_machine_readable_never_refreshed_state(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("CATALYST_EDGE_EVIDENCE_STORE", str(tmp_path / "events.sqlite3"))
    monkeypatch.setattr(sys, "argv", ["catalyst-edge-health", "NVDA"])

    with pytest.raises(SystemExit) as exc_info:
        health_main()

    payload = json.loads(capsys.readouterr().out)
    assert exc_info.value.code == 1
    assert payload["provider"] == "gdelt"
    assert payload["attributions"] == [
        {"name": "The GDELT Project", "url": "https://www.gdeltproject.org/"}
    ]
    assert payload["results"][0]["freshness"] == "never_refreshed"
    assert payload["results"][0]["last_success_age_seconds"] is None


@pytest.mark.asyncio
async def test_bluesky_lifecycle_runs_out_of_band_and_tracks_persisted_schedule(tmp_path):
    settings = _settings(tmp_path, bluesky_enabled=True)
    store = EvidenceStore(settings.evidence_store_path)
    calls = []

    class RecordingCollector:
        async def collect(self, ticker, lookback_days):
            calls.append((ticker, lookback_days))
            issuer = SOCIAL_ISSUER_INDEX[ticker]
            store.update_collector_state(
                source_id="bluesky",
                issuer_key=issuer.issuer_key,
                feed_url="https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                status=SourceStatus.FRESH.value,
                checked_at=AS_OF,
                succeeded=True,
            )
            return AdapterResult(
                family="social",
                provider="bluesky",
                status=SourceStatus.NO_OBSERVATIONS,
                collected_at=AS_OF,
            )

    lifecycle = BlueskyCollectionLifecycle(
        settings,
        tickers=["NVDA"],
        collector=RecordingCollector(),
        store=store,
        clock=lambda: AS_OF,
    )
    results = await lifecycle.run_once()

    assert calls == [("NVDA", 14)]
    assert results["NVDA"].provider == "bluesky"
    assert lifecycle.seconds_until_refresh() == 21600
    assert lifecycle.health()[0].freshness is FreshnessState.FRESH
    await lifecycle.stop()


@pytest.mark.asyncio
async def test_bluesky_lifecycle_skips_unregistered_ticker(tmp_path):
    settings = _settings(tmp_path, bluesky_enabled=True)

    class RejectingCollector:
        async def collect(self, ticker, lookback_days):
            raise AssertionError("unregistered ticker must not be collected")

    lifecycle = BlueskyCollectionLifecycle(
        settings,
        tickers=["UNKNOWN"],
        collector=RejectingCollector(),
        clock=lambda: AS_OF,
    )
    try:
        assert await lifecycle.run_once() == {}
        assert lifecycle.health()[0].freshness is FreshnessState.UNREGISTERED
    finally:
        await lifecycle.stop()
