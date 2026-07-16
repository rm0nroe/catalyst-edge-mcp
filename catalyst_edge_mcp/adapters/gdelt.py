"""Serialized GDELT DOC 2.0 publisher-metadata discovery adapter."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.collection_lifecycle import (
    FreshnessState,
    collection_health_from_state,
)
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.discovery_registry import DISCOVERY_ISSUER_INDEX, DiscoveryIssuer
from catalyst_edge_mcp.evidence_store import EventObservation, EvidenceStore, StoredEvent
from catalyst_edge_mcp.models import (
    AdapterResult,
    Change,
    Direction,
    Evidence,
    EvidenceContext,
    PolicyDecision,
    Source,
    SourceStatus,
)
from catalyst_edge_mcp.registry_config import publisher_quality_for_domain
from catalyst_edge_mcp.registry_models import PublisherDomainQuality

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
PARSER_VERSION = "gdelt-doc-v1"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ARTICLES = 50
MAX_RETRY_AFTER_SECONDS = 300.0
GDELT_GATE = ProviderGate(concurrency=1, requests_per_second=1 / 6)


class GdeltAdapter:
    """Discover recent publisher links without fetching or retaining article bodies."""

    family = "filings_news"
    provider = "gdelt"

    def __init__(
        self,
        store_path: str,
        *,
        registry: Mapping[str, DiscoveryIssuer] = DISCOVERY_ISSUER_INDEX,
        store: EvidenceStore | None = None,
        client: httpx.AsyncClient | None = None,
        gate: ProviderGate = GDELT_GATE,
        clock=None,
        endpoint: str = GDELT_ENDPOINT,
        live_refresh: bool = True,
        request_timeout_seconds: float = 6.0,
        max_cache_age_seconds: int = 900,
        publisher_quality_registry: Mapping[str, PublisherDomainQuality] | None = None,
    ) -> None:
        self.store = store or EvidenceStore(str(Path(store_path).expanduser()))
        self.registry = registry
        self._client = client
        self._gate = gate
        self._clock = clock or (lambda: datetime.now(UTC))
        self.endpoint = endpoint
        self.live_refresh = live_refresh
        self.request_timeout_seconds = request_timeout_seconds
        self.max_cache_age_seconds = max_cache_age_seconds
        self.publisher_quality_registry = publisher_quality_registry or {}

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        issuer = self.registry.get(ticker) or self.registry.get(ticker.replace(".", "-"))
        now = self._as_utc(self._clock())
        if issuer is None:
            return AdapterResult(
                family=self.family,
                provider=self.provider,
                warnings=[f"No reviewed GDELT query aliases are registered for {ticker}."],
                status=SourceStatus.NO_OBSERVATIONS,
                policy_decision=PolicyDecision.APPROVED_DISCOVERY,
                collected_at=now,
            )
        if not self.live_refresh:
            return self._cache_only_result(issuer, lookback_days, now)
        self._require_endpoint(self.endpoint)
        if self._client is not None:
            return await self._collect(self._client, issuer, lookback_days, now)
        headers = {
            "User-Agent": "CatalystEdgeMCP/0.1 gdelt-discovery",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(
                self.request_timeout_seconds,
                connect=self.request_timeout_seconds,
            ),
            follow_redirects=True,
        ) as client:
            return await self._collect(client, issuer, lookback_days, now)

    async def _collect(
        self,
        client: httpx.AsyncClient,
        issuer: DiscoveryIssuer,
        lookback_days: int,
        now: datetime,
    ) -> AdapterResult:
        state = self.store.collector_state(self.provider, issuer.issuer_key)
        if (
            state
            and state.get("status") == SourceStatus.FRESH.value
            and state.get("last_checked_at")
        ):
            last_checked = self._parse_datetime(state["last_checked_at"])
            if last_checked and (now - last_checked).total_seconds() < issuer.refresh_seconds:
                return self._cached_result(issuer, lookback_days, now)
        params = {
            "query": issuer.gdelt_query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": str(MAX_ARTICLES),
            "timespan": f"{min(lookback_days, 90)}d",
            "sort": "datedesc",
        }
        try:
            async with self._gate.request():
                response = await client.get(self.endpoint, params=params)
            self._require_endpoint(str(response.url).split("?", 1)[0])
            if response.status_code == 429:
                retry_after = self._retry_after(response.headers.get("retry-after"), now)
                if retry_after is not None:
                    await self._gate.defer_for(min(retry_after, MAX_RETRY_AFTER_SECONDS))
            response.raise_for_status()
            content = response.content
            if len(content) > MAX_RESPONSE_BYTES:
                raise ValueError("GDELT response exceeded the bounded response size")
            payload = json.loads(content)
            articles = payload.get("articles") if isinstance(payload, dict) else None
            if not isinstance(articles, list):
                raise ValueError("GDELT response did not contain an article list")
            raw_sha256 = hashlib.sha256(content).hexdigest()
            for article in articles[:MAX_ARTICLES]:
                if not isinstance(article, Mapping):
                    raise ValueError("GDELT article metadata was malformed")
                observation = self._observation(article, issuer, now, raw_sha256)
                if observation is not None:
                    self.store.ingest_event(observation)
            self.store.update_collector_state(
                source_id=self.provider,
                issuer_key=issuer.issuer_key,
                feed_url=self.endpoint,
                status=SourceStatus.FRESH.value,
                checked_at=now,
                succeeded=True,
            )
            return self._cached_result(issuer, lookback_days, now)
        except httpx.HTTPStatusError as exc:
            status = (
                SourceStatus.RATE_LIMITED
                if exc.response.status_code == 429
                else SourceStatus.PERMISSION_REQUIRED
                if exc.response.status_code in {401, 403}
                else SourceStatus.STALE
            )
            return self._failure_result(issuer, lookback_days, now, status, type(exc).__name__)
        except httpx.TimeoutException as exc:
            return self._failure_result(
                issuer, lookback_days, now, SourceStatus.TIMEOUT, type(exc).__name__
            )
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            return self._failure_result(
                issuer, lookback_days, now, SourceStatus.SCHEMA_ERROR, type(exc).__name__
            )
        except httpx.HTTPError as exc:
            return self._failure_result(
                issuer, lookback_days, now, SourceStatus.STALE, type(exc).__name__
            )

    def _cache_only_result(
        self,
        issuer: DiscoveryIssuer,
        lookback_days: int,
        now: datetime,
    ) -> AdapterResult:
        """Serve request-time discovery from cache while refresh runs out of band."""
        state = self.store.collector_state(self.provider, issuer.issuer_key)
        health = collection_health_from_state(
            issuer.tickers[0],
            issuer.issuer_key,
            state,
            now=now,
            max_age_seconds=self.max_cache_age_seconds,
        )
        if health.freshness is FreshnessState.FRESH:
            return self._cached_result(issuer, lookback_days, now)
        if health.freshness is FreshnessState.FAILED:
            status = health.source_status or SourceStatus.STALE
            age = (
                f"; last success was {health.last_success_age_seconds} seconds ago"
                if health.last_success_age_seconds is not None
                else "; no successful refresh has completed"
            )
            return self._cached_result(
                issuer,
                lookback_days,
                now,
                status=status,
                warning=(
                    f"GDELT background refresh failed with "
                    f"{health.error_class or 'unknown error'} ({status.value}){age}."
                ),
                degraded=True,
            )
        if health.freshness is FreshnessState.STALE:
            return self._cached_result(
                issuer,
                lookback_days,
                now,
                status=SourceStatus.STALE,
                warning=(
                    "GDELT background cache is stale; last successful refresh was "
                    f"{health.last_success_age_seconds} seconds ago."
                ),
                degraded=True,
            )
        return self._cached_result(
            issuer,
            lookback_days,
            now,
            status=SourceStatus.STALE,
            warning=(
                "GDELT automatic background lifecycle has not completed a successful "
                "refresh; catalyst-edge-refresh-gdelt remains available for manual recovery."
            ),
            degraded=True,
        )

    def _observation(
        self,
        article: Mapping[str, Any],
        issuer: DiscoveryIssuer,
        now: datetime,
        raw_sha256: str,
    ) -> EventObservation | None:
        title = " ".join(str(article.get("title") or "").split())[:240]
        url = str(article.get("url") or "").strip()
        published_at = self._article_datetime(article.get("seendate"))
        if not title or not url or published_at is None:
            return None
        parsed = urlsplit(url)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            return None
        domain = str(article.get("domain") or parsed.hostname).strip()[:100]
        return EventObservation(
            source_id=self.provider,
            source_name=f"GDELT discovery ({domain})",
            source_tier="discovery",
            issuer_key=issuer.issuer_key,
            record_id=url[:160],
            canonical_url=url,
            title=title,
            published_at=published_at,
            observed_at=now,
            retrieved_at=now,
            raw_sha256=raw_sha256,
            parser_version=PARSER_VERSION,
            policy_decision=PolicyDecision.APPROVED_DISCOVERY,
        )

    def _cached_result(
        self,
        issuer: DiscoveryIssuer,
        lookback_days: int,
        now: datetime,
        *,
        status: SourceStatus | None = None,
        warning: str | None = None,
        degraded: bool = False,
    ) -> AdapterResult:
        events = self.store.list_events_for_source(
            issuer.issuer_key, self.provider, now - timedelta(days=lookback_days)
        )
        evidence = [self._evidence(event) for event in events]
        effective_status = status or (
            SourceStatus.FRESH if evidence else SourceStatus.NO_OBSERVATIONS
        )
        warnings = [warning] if warning else []
        if not evidence and not warning:
            warnings.append(
                f"No GDELT publisher links found for {issuer.tickers[0]} in the window."
            )
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=warnings,
            status=effective_status,
            policy_decision=PolicyDecision.APPROVED_DISCOVERY,
            degraded=degraded,
            collected_at=now,
        )

    def _failure_result(
        self,
        issuer: DiscoveryIssuer,
        lookback_days: int,
        now: datetime,
        status: SourceStatus,
        error_class: str,
    ) -> AdapterResult:
        self.store.update_collector_state(
            source_id=self.provider,
            issuer_key=issuer.issuer_key,
            feed_url=self.endpoint,
            status=status.value,
            checked_at=now,
            succeeded=False,
            error_class=error_class,
        )
        return self._cached_result(
            issuer,
            lookback_days,
            now,
            status=status,
            warning=f"GDELT refresh failed: {error_class} ({status.value}).",
            degraded=True,
        )

    def _evidence(self, event: StoredEvent) -> Evidence:
        source = event.primary_source
        domain = (urlsplit(source.canonical_url).hostname or "").lower().rstrip(".")
        publisher_quality = publisher_quality_for_domain(
            domain,
            self.publisher_quality_registry,
        )
        quality = publisher_quality.quality if publisher_quality else 0.60
        quality_tier = publisher_quality.tier if publisher_quality else "unreviewed"
        return Evidence(
            family="filings_news",
            signal="publisher_link_discovery",
            direction=Direction.NEUTRAL,
            strength=0.35,
            confidence=0.60,
            timestamp=event.published_at,
            source_quality=quality,
            change=Change(description=f"Publisher coverage discovered: {event.title}"[:240]),
            context=EvidenceContext(
                event_type="publisher_coverage",
                event_label="Publisher coverage discovery",
                novelty="correction" if event.version > 1 else "new_coverage",
                materiality="discovery_only",
                why_it_matters=(
                    "Publisher metadata can corroborate awareness or lead to a primary "
                    "source, but it does not establish the underlying event by itself."
                ),
                source_record_count=event.source_count,
                corroborating_source_count=max(0, event.source_count - 1),
                source_tiers=list(event.source_tiers),
                correction_of_event_id=event.correction_of_event_id,
            ),
            sources=[
                Source(
                    name=source.source_name,
                    source_id=source.source_id,
                    source_tier=source.source_tier,
                    url=source.canonical_url,
                    canonical_url=source.canonical_url,
                    accession_or_record_id=source.record_id[:160],
                    published_at=source.published_at,
                    observed_at=source.observed_at,
                    retrieved_at=source.retrieved_at,
                    raw_sha256=source.raw_sha256,
                    parser_version=source.parser_version,
                    policy_decision=source.policy_decision,
                    related_sources=list(event.related_urls),
                )
            ],
            notes=(
                "GDELT is neutral discovery metadata only; publisher bodies are neither "
                "fetched nor retained and discovery cannot establish launch readiness. "
                f"Publisher domain quality tier: {quality_tier}."
            ),
            raw_signal={
                "canonical_event_id": event.event_id,
                "version": event.version,
                "title": event.title,
                "record_id": source.record_id,
                "source_count": event.source_count,
                "source_tiers": list(event.source_tiers),
                "publisher_domain": domain,
                "publisher_quality_tier": quality_tier,
            },
        )

    @staticmethod
    def _article_datetime(value: object) -> datetime | None:
        text = str(value or "").strip()
        for pattern in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
            try:
                return datetime.strptime(text, pattern).replace(tzinfo=UTC)
            except ValueError:
                pass
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    @staticmethod
    def _retry_after(value: str | None, now: datetime) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return None
            parsed = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
            return max(0.0, (parsed - now).total_seconds())

    @staticmethod
    def _require_endpoint(url: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower().rstrip(".") != "api.gdeltproject.org"
            or parsed.path.rstrip("/") != "/api/v2/doc/doc"
        ):
            raise ValueError("GDELT request URL is outside the reviewed official endpoint")

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
