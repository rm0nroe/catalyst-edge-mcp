"""Automatic bounded collection lifecycle and operator freshness health."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from catalyst_edge_mcp.adapters.bluesky import BlueskyAdapter
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.gdelt_web_ngrams import (
    GdeltWebNgramsRefresher,
    GdeltWebNgramsResult,
)
from catalyst_edge_mcp.models import AdapterResult, SourceStatus
from catalyst_edge_mcp.registry_config import RegistryBundle, load_registry_bundle
from catalyst_edge_mcp.registry_models import DiscoveryIssuer, SocialIssuer
from catalyst_edge_mcp.settings import Settings
from catalyst_edge_mcp.source_policy import source_attributions
from catalyst_edge_mcp.validation import normalize_ticker

LOGGER = logging.getLogger(__name__)


class FreshnessState(str, Enum):
    """Operator-facing state derived from persisted collection attempts."""

    FRESH = "fresh"
    STALE = "stale"
    NEVER_REFRESHED = "never_refreshed"
    FAILED = "failed"
    UNREGISTERED = "unregistered"


@dataclass(frozen=True, slots=True)
class CollectionHealth:
    ticker: str
    issuer_key: str | None
    freshness: FreshnessState
    source_status: SourceStatus | None
    last_checked_at: datetime | None
    last_success_at: datetime | None
    last_success_age_seconds: int | None
    error_class: str | None

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["freshness"] = self.freshness.value
        payload["source_status"] = (
            self.source_status.value if self.source_status is not None else None
        )
        payload["last_checked_at"] = (
            self.last_checked_at.isoformat() if self.last_checked_at is not None else None
        )
        payload["last_success_at"] = (
            self.last_success_at.isoformat() if self.last_success_at is not None else None
        )
        return payload


def collection_health_from_state(
    ticker: str,
    issuer_key: str,
    state: Mapping[str, Any] | None,
    *,
    now: datetime,
    max_age_seconds: int,
) -> CollectionHealth:
    """Project one persisted collector row into explicit freshness health."""
    now = _as_utc(now)
    if state is None:
        return CollectionHealth(
            ticker=ticker,
            issuer_key=issuer_key,
            freshness=FreshnessState.NEVER_REFRESHED,
            source_status=None,
            last_checked_at=None,
            last_success_at=None,
            last_success_age_seconds=None,
            error_class=None,
        )

    last_checked = _parse_datetime(state.get("last_checked_at"))
    last_success = _parse_datetime(state.get("last_success_at"))
    source_status = _source_status(state.get("status"))
    error_class = str(state["error_class"]) if state.get("error_class") else None
    age = (
        max(0, int((now - last_success).total_seconds()))
        if last_success is not None
        else None
    )
    failed_after_success = (
        last_checked is not None
        and (last_success is None or last_checked > last_success)
        and source_status not in {SourceStatus.FRESH, SourceStatus.NO_OBSERVATIONS}
    )
    if failed_after_success:
        freshness = FreshnessState.FAILED
    elif last_success is None:
        freshness = FreshnessState.NEVER_REFRESHED
    elif age is not None and age > max_age_seconds:
        freshness = FreshnessState.STALE
    else:
        freshness = FreshnessState.FRESH
    return CollectionHealth(
        ticker=ticker,
        issuer_key=issuer_key,
        freshness=freshness,
        source_status=source_status,
        last_checked_at=last_checked,
        last_success_at=last_success,
        last_success_age_seconds=age,
        error_class=error_class,
    )


def default_refresh_tickers(
    issuers: Sequence[DiscoveryIssuer],
) -> tuple[str, ...]:
    """Return one deterministic canonical ticker per reviewed issuer."""
    return tuple(issuer.tickers[0] for issuer in issuers)


class GdeltCollectionLifecycle:
    """Run one bounded startup catch-up and periodic refreshes out of band."""

    def __init__(
        self,
        settings: Settings,
        *,
        tickers: Sequence[str] | None = None,
        refresher: GdeltWebNgramsRefresher | None = None,
        store: EvidenceStore | None = None,
        registry: RegistryBundle | None = None,
        clock=None,
    ) -> None:
        self.settings = settings
        self.registry = registry or load_registry_bundle(settings.registry_path)
        self.discovery_index = self.registry.discovery_index
        self.tickers = tuple(
            tickers or default_refresh_tickers(self.registry.discovery_issuers)
        )
        self.store = store or EvidenceStore(settings.evidence_store_path)
        self.refresher = refresher or GdeltWebNgramsRefresher(
            settings.evidence_store_path,
            registry=self.discovery_index,
            store=self.store,
        )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._task: asyncio.Task[None] | None = None
        self.last_results: dict[str, GdeltWebNgramsResult] = {}

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.running:
            return
        self._task = asyncio.create_task(
            self._run_loop(),
            name="catalyst-edge-gdelt-refresh",
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self.store.close()

    async def run_once(self) -> dict[str, GdeltWebNgramsResult]:
        results = await self.refresher.refresh(
            self.tickers,
            self.settings.gdelt_refresh_lookback_days,
        )
        self.last_results = results
        return results

    def health(self, tickers: Sequence[str] | None = None) -> list[CollectionHealth]:
        now = _as_utc(self._clock())
        reports: list[CollectionHealth] = []
        for ticker in tickers or self.tickers:
            issuer = self._issuer(ticker)
            if issuer is None:
                reports.append(
                    CollectionHealth(
                        ticker=ticker,
                        issuer_key=None,
                        freshness=FreshnessState.UNREGISTERED,
                        source_status=SourceStatus.NO_OBSERVATIONS,
                        last_checked_at=None,
                        last_success_at=None,
                        last_success_age_seconds=None,
                        error_class=None,
                    )
                )
                continue
            state = self.store.collector_state("gdelt", issuer.issuer_key)
            reports.append(
                collection_health_from_state(
                    ticker,
                    issuer.issuer_key,
                    state,
                    now=now,
                    max_age_seconds=self.settings.gdelt_freshness_max_age_seconds,
                )
            )
        return reports

    def seconds_until_refresh(self) -> float:
        """Delay until the earliest issuer is due; missing state is due now."""
        now = _as_utc(self._clock())
        delays: list[float] = []
        seen: set[str] = set()
        for ticker in self.tickers:
            issuer = self._issuer(ticker)
            if issuer is None or issuer.issuer_key in seen:
                continue
            seen.add(issuer.issuer_key)
            state = self.store.collector_state("gdelt", issuer.issuer_key)
            last_checked = _parse_datetime(state.get("last_checked_at")) if state else None
            if last_checked is None:
                return 0.0
            due_at = last_checked + timedelta(
                seconds=self.settings.gdelt_refresh_interval_seconds
            )
            delays.append(max(0.0, (due_at - now).total_seconds()))
        return min(delays, default=float(self.settings.gdelt_refresh_interval_seconds))

    def _issuer(self, ticker: str) -> DiscoveryIssuer | None:
        try:
            canonical = normalize_ticker(ticker)
        except ValueError:
            return None
        return self.discovery_index.get(canonical) or self.discovery_index.get(
            canonical.replace(".", "-")
        )

    async def _run_loop(self) -> None:
        initial_delay = self.seconds_until_refresh()
        if initial_delay:
            await asyncio.sleep(initial_delay)
        while True:
            try:
                await self.run_once()
            except Exception as exc:  # pragma: no cover - refresher normally types failures
                LOGGER.warning(
                    "GDELT lifecycle refresh failed with %s",
                    type(exc).__name__,
                )
            await asyncio.sleep(self.settings.gdelt_refresh_interval_seconds)


class BlueskyCollectionLifecycle:
    """Collect one completed UTC day at a bounded out-of-band cadence."""

    def __init__(
        self,
        settings: Settings,
        *,
        tickers: Sequence[str] | None = None,
        collector: BlueskyAdapter | None = None,
        store: EvidenceStore | None = None,
        registry: RegistryBundle | None = None,
        clock=None,
    ) -> None:
        self.settings = settings
        self.registry = registry or load_registry_bundle(settings.registry_path)
        self.social_index = self.registry.social_index
        self.tickers = tuple(
            tickers or (issuer.tickers[0] for issuer in self.registry.social_issuers)
        )
        self.store = store or EvidenceStore(settings.evidence_store_path)
        self.collector = collector or BlueskyAdapter(
            settings.evidence_store_path,
            registry=self.social_index,
            store=self.store,
            live_refresh=True,
            max_cache_age_seconds=settings.bluesky_freshness_max_age_seconds,
        )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._task: asyncio.Task[None] | None = None
        self.last_results: dict[str, AdapterResult] = {}

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.running:
            return
        self._task = asyncio.create_task(
            self._run_loop(),
            name="catalyst-edge-bluesky-refresh",
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self.store.close()

    async def run_once(self) -> dict[str, AdapterResult]:
        results: dict[str, AdapterResult] = {}
        for ticker in self.tickers:
            if self._issuer(ticker) is not None:
                results[ticker] = await self.collector.collect(ticker, 14)
        self.last_results = results
        return results

    def health(self, tickers: Sequence[str] | None = None) -> list[CollectionHealth]:
        now = _as_utc(self._clock())
        reports: list[CollectionHealth] = []
        for ticker in tickers or self.tickers:
            issuer = self._issuer(ticker)
            if issuer is None:
                reports.append(
                    CollectionHealth(
                        ticker=ticker,
                        issuer_key=None,
                        freshness=FreshnessState.UNREGISTERED,
                        source_status=SourceStatus.NO_OBSERVATIONS,
                        last_checked_at=None,
                        last_success_at=None,
                        last_success_age_seconds=None,
                        error_class=None,
                    )
                )
                continue
            reports.append(
                collection_health_from_state(
                    ticker,
                    issuer.issuer_key,
                    self.store.collector_state("bluesky", issuer.issuer_key),
                    now=now,
                    max_age_seconds=self.settings.bluesky_freshness_max_age_seconds,
                )
            )
        return reports

    def seconds_until_refresh(self) -> float:
        now = _as_utc(self._clock())
        delays: list[float] = []
        seen: set[str] = set()
        for ticker in self.tickers:
            issuer = self._issuer(ticker)
            if issuer is None or issuer.issuer_key in seen:
                continue
            seen.add(issuer.issuer_key)
            state = self.store.collector_state("bluesky", issuer.issuer_key)
            last_checked = _parse_datetime(state.get("last_checked_at")) if state else None
            if last_checked is None:
                return 0.0
            due_at = last_checked + timedelta(
                seconds=self.settings.bluesky_refresh_interval_seconds
            )
            delays.append(max(0.0, (due_at - now).total_seconds()))
        return min(
            delays,
            default=float(self.settings.bluesky_refresh_interval_seconds),
        )

    def _issuer(self, ticker: str) -> SocialIssuer | None:
        try:
            canonical = normalize_ticker(ticker)
        except ValueError:
            return None
        return self.social_index.get(canonical) or self.social_index.get(
            canonical.replace(".", "-")
        )

    async def _run_loop(self) -> None:
        initial_delay = self.seconds_until_refresh()
        if initial_delay:
            await asyncio.sleep(initial_delay)
        while True:
            try:
                await self.run_once()
            except Exception as exc:  # pragma: no cover - collector types normal failures
                LOGGER.warning(
                    "Bluesky lifecycle refresh failed with %s",
                    type(exc).__name__,
                )
            await asyncio.sleep(self.settings.bluesky_refresh_interval_seconds)


class CollectionLifecycleGroup:
    """Own every enabled out-of-band collector under one server lifespan."""

    def __init__(self, lifecycles: Sequence[Any]) -> None:
        self.lifecycles = tuple(lifecycles)

    def start(self) -> None:
        for lifecycle in self.lifecycles:
            lifecycle.start()

    async def stop(self) -> None:
        for lifecycle in reversed(self.lifecycles):
            await lifecycle.stop()


def build_collection_lifecycle(settings: Settings) -> CollectionLifecycleGroup | None:
    lifecycles = []
    if settings.gdelt_enabled:
        lifecycles.append(GdeltCollectionLifecycle(settings))
    if settings.bluesky_enabled:
        lifecycles.append(BlueskyCollectionLifecycle(settings))
    return CollectionLifecycleGroup(lifecycles) if lifecycles else None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return _as_utc(parsed)


def _source_status(value: object) -> SourceStatus | None:
    try:
        return SourceStatus(str(value))
    except ValueError:
        return SourceStatus.UNAVAILABLE if value is not None else None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def health_main() -> None:
    parser = argparse.ArgumentParser(description="Report GDELT collection freshness health")
    parser.add_argument("tickers", nargs="*", help="Reviewed public-company tickers")
    args = parser.parse_args()
    settings = Settings.from_env()
    lifecycle = GdeltCollectionLifecycle(settings)
    try:
        reports = lifecycle.health(args.tickers or None)
        print(
            json.dumps(
                {
                    "provider": "gdelt",
                    "attributions": [
                        item.model_dump(mode="json")
                        for item in source_attributions(["gdelt"])
                    ],
                    "observed_at": _as_utc(lifecycle._clock()).isoformat(),
                    "results": [report.as_dict() for report in reports],
                },
                indent=2,
            )
        )
    finally:
        lifecycle.store.close()
    raise SystemExit(
        0 if reports and all(item.freshness is FreshnessState.FRESH for item in reports) else 1
    )
