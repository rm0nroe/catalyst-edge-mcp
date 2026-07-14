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
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.discovery_registry import DISCOVERY_ISSUER_INDEX, DiscoveryIssuer
from catalyst_edge_mcp.evidence_store import EventObservation, EvidenceStore, StoredEvent
from catalyst_edge_mcp.models import (
    AdapterResult,
    Change,
    Direction,
    Evidence,
    PolicyDecision,
    Source,
    SourceStatus,
)

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
PARSER_VERSION = "gdelt-doc-v1"
MAX_RESPONSE_BYTES = 2_000_000
MAX_ARTICLES = 50
MAX_RETRY_AFTER_SECONDS = 300.0
GDELT_GATE = ProviderGate(concurrency=1, requests_per_second=0.2)


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
    ) -> None:
        self.store = store or EvidenceStore(str(Path(store_path).expanduser()))
        self.registry = registry
        self._client = client
        self._gate = gate
        self._clock = clock or (lambda: datetime.now(UTC))
        self.endpoint = endpoint

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
        self._require_endpoint(self.endpoint)
        if self._client is not None:
            return await self._collect(self._client, issuer, lookback_days, now)
        headers = {
            "User-Agent": "CatalystEdgeMCP/0.1 gdelt-discovery",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(
            headers=headers, timeout=6.0, follow_redirects=True
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
        if state and state.get("last_checked_at"):
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
            record_id=url[:500],
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

    @staticmethod
    def _evidence(event: StoredEvent) -> Evidence:
        source = event.primary_source
        return Evidence(
            family="filings_news",
            signal="publisher_link_discovery",
            direction=Direction.NEUTRAL,
            strength=0.35,
            confidence=0.60,
            timestamp=event.published_at,
            source_quality=0.65,
            change=Change(description=f"Publisher coverage discovered: {event.title}"[:240]),
            sources=[
                Source(
                    name=source.source_name,
                    source_id=source.source_id,
                    source_tier=source.source_tier,
                    url=source.canonical_url,
                    canonical_url=source.canonical_url,
                    accession_or_record_id=source.record_id,
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
                "fetched nor retained and discovery cannot establish launch readiness."
            ),
            raw_signal={
                "canonical_event_id": event.event_id,
                "version": event.version,
                "title": event.title,
                "record_id": source.record_id,
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
