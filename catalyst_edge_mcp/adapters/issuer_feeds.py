"""Reviewed issuer RSS/Atom adapter with conditional retrieval and cached state."""

from __future__ import annotations

import calendar
import hashlib
from collections.abc import Mapping
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import feedparser
import httpx

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.evidence_store import EventObservation, EvidenceStore, StoredEvent
from catalyst_edge_mcp.issuer_registry import ISSUER_FEED_INDEX, IssuerFeed
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

PARSER_VERSION = "issuer-feed-v1"
MAX_FEED_BYTES = 2_000_000
MAX_ENTRIES = 50


class IssuerFeedAdapter:
    """Collect factual release metadata from explicitly reviewed issuer feeds."""

    family = "filings_news"
    provider = "issuer_feed"

    def __init__(
        self,
        store_path: str,
        *,
        registry: Mapping[str, IssuerFeed] = ISSUER_FEED_INDEX,
        store: EvidenceStore | None = None,
        client: httpx.AsyncClient | None = None,
        clock=None,
    ) -> None:
        self.store = store or EvidenceStore(str(Path(store_path).expanduser()))
        self.registry = registry
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        feed = self.registry.get(ticker) or self.registry.get(ticker.replace(".", "-"))
        now = self._as_utc(self._clock())
        if feed is None:
            return AdapterResult(
                family=self.family,
                provider=self.provider,
                warnings=[f"No reviewed issuer feed is registered for {ticker}."],
                status=SourceStatus.NO_OBSERVATIONS,
                policy_decision=PolicyDecision.APPROVED_PER_REGISTRY,
                collected_at=now,
            )
        self._require_official_url(feed.feed_url, feed)
        if self._client is not None:
            return await self._collect(self._client, feed, lookback_days, now)
        headers = {
            "User-Agent": "CatalystEdgeMCP/0.1 issuer-feed-reader",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        }
        async with httpx.AsyncClient(headers=headers, timeout=6.0, follow_redirects=True) as client:
            return await self._collect(client, feed, lookback_days, now)

    async def _collect(
        self,
        client: httpx.AsyncClient,
        feed: IssuerFeed,
        lookback_days: int,
        now: datetime,
    ) -> AdapterResult:
        state = self.store.collector_state(self.provider, feed.issuer_key)
        if state and state.get("last_checked_at"):
            last_checked = self._parse_datetime(state["last_checked_at"])
            if last_checked and (now - last_checked).total_seconds() < feed.refresh_seconds:
                return self._cached_result(feed, lookback_days, now)
        headers = {}
        if state and state.get("etag"):
            headers["If-None-Match"] = str(state["etag"])
        if state and state.get("last_modified"):
            headers["If-Modified-Since"] = str(state["last_modified"])
        try:
            response = await client.get(feed.feed_url, headers=headers)
            self._require_official_url(str(response.url), feed)
            if response.status_code == 304:
                self.store.update_collector_state(
                    source_id=self.provider,
                    issuer_key=feed.issuer_key,
                    feed_url=feed.feed_url,
                    status=SourceStatus.FRESH.value,
                    checked_at=now,
                    succeeded=True,
                )
                return self._cached_result(feed, lookback_days, now)
            response.raise_for_status()
            content = response.content
            if len(content) > MAX_FEED_BYTES:
                raise ValueError("Issuer feed exceeded the bounded response size")
            parsed = feedparser.parse(content)
            entries = list(parsed.get("entries", []))
            if parsed.get("bozo") and not entries:
                raise ValueError("Issuer feed XML was malformed")
            raw_sha256 = hashlib.sha256(content).hexdigest()
            cutoff = now - timedelta(days=90)
            for entry in entries[:MAX_ENTRIES]:
                observation = self._observation(entry, feed, now, raw_sha256)
                if observation is not None and observation.published_at >= cutoff:
                    self.store.ingest_event(observation)
            self.store.update_collector_state(
                source_id=self.provider,
                issuer_key=feed.issuer_key,
                feed_url=feed.feed_url,
                status=SourceStatus.FRESH.value,
                checked_at=now,
                succeeded=True,
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
            return self._cached_result(feed, lookback_days, now)
        except httpx.HTTPStatusError as exc:
            status = (
                SourceStatus.RATE_LIMITED
                if exc.response.status_code == 429
                else SourceStatus.PERMISSION_REQUIRED
                if exc.response.status_code in {401, 403}
                else SourceStatus.STALE
            )
            return self._failure_result(feed, lookback_days, now, status, type(exc).__name__)
        except httpx.TimeoutException as exc:
            return self._failure_result(
                feed, lookback_days, now, SourceStatus.TIMEOUT, type(exc).__name__
            )
        except ValueError as exc:
            return self._failure_result(
                feed, lookback_days, now, SourceStatus.SCHEMA_ERROR, type(exc).__name__
            )
        except httpx.HTTPError as exc:
            return self._failure_result(
                feed, lookback_days, now, SourceStatus.STALE, type(exc).__name__
            )

    def _observation(
        self,
        entry: Mapping[str, Any],
        feed: IssuerFeed,
        now: datetime,
        raw_sha256: str,
    ) -> EventObservation | None:
        title = " ".join(str(entry.get("title") or "").split())[:240]
        link = str(entry.get("link") or "").strip()
        published_at = self._entry_datetime(entry)
        if not title or not link or published_at is None:
            return None
        self._require_official_url(link, feed)
        record_id = str(entry.get("id") or link)[:500]
        return EventObservation(
            source_id=self.provider,
            source_name=f"{feed.issuer_name} official feed",
            source_tier="issuer_primary",
            issuer_key=feed.issuer_key,
            record_id=record_id,
            canonical_url=link,
            title=title,
            published_at=published_at,
            observed_at=now,
            retrieved_at=now,
            raw_sha256=raw_sha256,
            parser_version=PARSER_VERSION,
            policy_decision=PolicyDecision.APPROVED_PER_REGISTRY,
        )

    def _cached_result(
        self,
        feed: IssuerFeed,
        lookback_days: int,
        now: datetime,
        *,
        status: SourceStatus | None = None,
        warning: str | None = None,
        degraded: bool = False,
    ) -> AdapterResult:
        events = self.store.list_events_for_source(
            feed.issuer_key, self.provider, now - timedelta(days=lookback_days)
        )
        evidence = [self._evidence(event) for event in events]
        effective_status = status or (
            SourceStatus.FRESH if evidence else SourceStatus.NO_OBSERVATIONS
        )
        warnings = [warning] if warning else []
        if not evidence and not warning:
            warnings.append(f"No issuer-feed events found for {feed.tickers[0]} in the window.")
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=warnings,
            status=effective_status,
            policy_decision=PolicyDecision.APPROVED_PER_REGISTRY,
            degraded=degraded,
            collected_at=now,
        )

    def _failure_result(
        self,
        feed: IssuerFeed,
        lookback_days: int,
        now: datetime,
        status: SourceStatus,
        error_class: str,
    ) -> AdapterResult:
        self.store.update_collector_state(
            source_id=self.provider,
            issuer_key=feed.issuer_key,
            feed_url=feed.feed_url,
            status=status.value,
            checked_at=now,
            succeeded=False,
            error_class=error_class,
        )
        return self._cached_result(
            feed,
            lookback_days,
            now,
            status=status,
            warning=f"Issuer feed refresh failed: {error_class} ({status.value}).",
            degraded=True,
        )

    @staticmethod
    def _evidence(event: StoredEvent) -> Evidence:
        source = event.primary_source
        return Evidence(
            family="filings_news",
            signal=("issuer_release_correction" if event.version > 1 else "issuer_release"),
            direction=Direction.NEUTRAL,
            strength=0.72,
            confidence=0.97,
            timestamp=event.published_at,
            source_quality=0.95,
            change=Change(description=f"Issuer published: {event.title}"[:240]),
            context=EvidenceContext(
                event_type="issuer_release_correction" if event.version > 1 else "issuer_release",
                event_label="Issuer release correction" if event.version > 1 else "Issuer release",
                novelty="correction" if event.version > 1 else "new_event",
                materiality="contextual",
                why_it_matters=(
                    "A correction changes a previously canonicalized issuer disclosure "
                    "and should be compared with the prior version."
                    if event.version > 1
                    else "An issuer-primary release adds direct company context to the "
                    "catalyst record."
                ),
                source_record_count=event.source_count,
                corroborating_source_count=max(0, event.source_count - 1),
                source_tiers=list(event.source_tiers),
                correction_of_event_id=event.correction_of_event_id,
                claim_id=event.claim_id,
                supporting_source_ids=list(event.supporting_source_ids),
                supporting_sources_truncated=(
                    event.source_count > len(event.supporting_source_ids)
                ),
            ),
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
                "Reviewed issuer-feed metadata; publisher bodies are not retained. "
                "Direction remains neutral absent an allowlisted event mapping."
            ),
            raw_signal={
                "canonical_event_id": event.event_id,
                "version": event.version,
                "correction_of_event_id": event.correction_of_event_id,
                "title": event.title,
                "record_id": source.record_id,
                "source_count": event.source_count,
                "source_tiers": list(event.source_tiers),
            },
        )

    @staticmethod
    def _entry_datetime(entry: Mapping[str, Any]) -> datetime | None:
        structured = entry.get("published_parsed") or entry.get("updated_parsed")
        if structured:
            return datetime.fromtimestamp(calendar.timegm(structured), tz=UTC)
        for key in ("published", "updated"):
            text = str(entry.get(key) or "").strip()
            if not text:
                continue
            try:
                parsed = parsedate_to_datetime(text)
            except (TypeError, ValueError):
                try:
                    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                except ValueError:
                    continue
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        return None

    @staticmethod
    def _require_official_url(url: str, feed: IssuerFeed) -> None:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        approved = any(
            host == allowed or host.endswith("." + allowed) for allowed in feed.official_hosts
        )
        if parsed.scheme.lower() != "https" or not approved:
            raise ValueError("Issuer feed URL is outside the reviewed official hosts")

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
