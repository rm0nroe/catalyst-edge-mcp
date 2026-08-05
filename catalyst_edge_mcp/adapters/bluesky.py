"""Forward-only Bluesky collector and cache-only partial-attention adapter."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.models import (
    AdapterResult,
    Change,
    Direction,
    Evidence,
    PolicyDecision,
    Source,
    SourceStatus,
)
from catalyst_edge_mcp.social_registry import SOCIAL_ISSUER_INDEX, SocialIssuer

APPVIEW_HOSTS = ("public.api.bsky.app", "api.bsky.app")
SEARCH_PATH = "/xrpc/app.bsky.feed.searchPosts"
MAX_RESPONSE_BYTES = 2_000_000
MAX_POSTS_PER_PAGE = 100
MIN_POSTS_PER_WINDOW = 5
MIN_AUTHORS_PER_WINDOW = 3
COMPARISON_DAYS = 7
PARSER_VERSION = "bluesky-forward-attention-v2"
BLUESKY_GATE = ProviderGate(name="bluesky", concurrency=1, requests_per_second=1.0)


class BlueskyAdapter:
    family = "social"
    provider = "bluesky"

    def __init__(
        self,
        store_path: str,
        *,
        registry: Mapping[str, SocialIssuer] = SOCIAL_ISSUER_INDEX,
        store: EvidenceStore | None = None,
        client: httpx.AsyncClient | None = None,
        gate: ProviderGate = BLUESKY_GATE,
        clock=None,
        live_refresh: bool = True,
        max_cache_age_seconds: int = 43_200,
    ) -> None:
        self.store = store or EvidenceStore(str(Path(store_path).expanduser()))
        self.registry = registry
        self._client = client
        self._gate = gate
        self._clock = clock or (lambda: datetime.now(UTC))
        self._preferred_host = APPVIEW_HOSTS[0]
        self.live_refresh = live_refresh
        self.max_cache_age_seconds = max_cache_age_seconds

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        del lookback_days
        issuer = self.registry.get(ticker) or self.registry.get(ticker.replace(".", "-"))
        now = self._as_utc(self._clock())
        if issuer is None:
            return self._result(
                status=SourceStatus.NO_OBSERVATIONS,
                now=now,
                warning=f"No reviewed Bluesky aliases are registered for {ticker}.",
            )
        if not self.live_refresh:
            return self._cache_only_result(issuer, now)
        if self._client is not None:
            return await self._collect(self._client, issuer, now)
        headers = {
            "User-Agent": "CatalystEdgeMCP/0.1 bluesky-attention",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(
            headers=headers, timeout=3.0, follow_redirects=True
        ) as client:
            return await self._collect(client, issuer, now)

    async def _collect(
        self,
        client: httpx.AsyncClient,
        issuer: SocialIssuer,
        now: datetime,
    ) -> AdapterResult:
        window_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        window_start = window_end - timedelta(days=1)
        try:
            metrics, adequate = await self._fetch_window(
                client, issuer, window_start, window_end, now
            )
            previous = self._bucket_at(issuer, window_start)
            previous_hashes = set(previous.get("uri_sha256s", [])) if previous else set()
            current_hashes = set(metrics["uri_sha256s"])
            deletion_uncertain = bool(previous_hashes - current_hashes)
            coverage_state = (
                "deletion_uncertain"
                if deletion_uncertain
                else "adequate"
                if adequate
                else "truncated"
            )
            successful = adequate and not deletion_uncertain
            self._record_window(
                issuer,
                window_start,
                window_end,
                metrics,
                coverage_state=coverage_state,
            )
            status = SourceStatus.FRESH if successful else SourceStatus.STALE
            self._record_state(issuer, now, status, succeeded=successful)
            if not successful:
                reason = (
                    "previously observed URI hashes disappeared on recheck"
                    if deletion_uncertain
                    else "the ranked first page reported truncation"
                )
                return self._result(
                    status=status,
                    now=now,
                    warning=(
                        f"Bluesky forward bucket failed closed because {reason}; "
                        "no attention trend was inferred."
                    ),
                    degraded=True,
                )
            return self._cache_only_result(issuer, now)
        except httpx.HTTPStatusError as exc:
            status = (
                SourceStatus.RATE_LIMITED
                if exc.response.status_code == 429
                else SourceStatus.PERMISSION_REQUIRED
                if exc.response.status_code in {401, 403}
                else SourceStatus.UNAVAILABLE
            )
            return self._failure(issuer, now, window_start, status, type(exc).__name__)
        except httpx.TimeoutException as exc:
            return self._failure(
                issuer, now, window_start, SourceStatus.TIMEOUT, type(exc).__name__
            )
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            return self._failure(
                issuer, now, window_start, SourceStatus.SCHEMA_ERROR, type(exc).__name__
            )
        except httpx.HTTPError as exc:
            return self._failure(
                issuer, now, window_start, SourceStatus.UNAVAILABLE, type(exc).__name__
            )

    async def _fetch_window(
        self,
        client: httpx.AsyncClient,
        issuer: SocialIssuer,
        start: datetime,
        end: datetime,
        now: datetime,
    ) -> tuple[dict[str, Any], bool]:
        params = {
            "q": issuer.bluesky_query,
            "limit": str(MAX_POSTS_PER_PAGE),
            "sort": "latest",
            "since": start.isoformat(),
            "until": end.isoformat(),
        }
        response = await self._request_with_fallback(client, params)
        if response.status_code == 429:
            retry_after = self._retry_delay(response, now)
            if retry_after is not None:
                await self._gate.defer_for(min(retry_after, 300.0))
        response.raise_for_status()
        content = response.content
        if len(content) > MAX_RESPONSE_BYTES:
            raise ValueError("Bluesky response exceeded the bounded response size")
        payload = json.loads(content)
        posts = payload.get("posts") if isinstance(payload, dict) else None
        if not isinstance(posts, list):
            raise ValueError("Bluesky response did not contain a post list")
        metrics = self._metrics(posts, issuer, start=start, end=end)
        metrics["raw_sha256"] = hashlib.sha256(content).hexdigest()
        raw_hits_total = payload.get("hitsTotal")
        hits_total = raw_hits_total if isinstance(raw_hits_total, int) else None
        cursor = payload.get("cursor")
        metrics["reported_hits_total"] = hits_total
        metrics["cursor_present"] = bool(cursor)
        # AppView currently emits a cursor even when hitsTotal equals the returned
        # page. Treat only a reported overflow (or a full page without a total) as
        # truncation; the collector still never follows the cursor.
        truncated = (
            hits_total > len(posts)
            if hits_total is not None
            else len(posts) >= MAX_POSTS_PER_PAGE
        )
        return metrics, not truncated

    async def _request_with_fallback(
        self, client: httpx.AsyncClient, params: dict[str, str]
    ) -> httpx.Response:
        last_error: Exception | None = None
        hosts = (
            self._preferred_host,
            *(host for host in APPVIEW_HOSTS if host != self._preferred_host),
        )
        for index, host in enumerate(hosts):
            try:
                async with self._gate.request():
                    response = await client.get(f"https://{host}{SEARCH_PATH}", params=params)
                self._require_appview_url(str(response.url))
                fallback_status = response.status_code >= 500 or response.status_code in {
                    401,
                    403,
                }
                if not fallback_status or index == len(APPVIEW_HOSTS) - 1:
                    if response.is_success:
                        self._preferred_host = host
                    return response
                last_error = httpx.HTTPStatusError(
                    "Bluesky AppView unavailable",
                    request=response.request,
                    response=response,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if index == len(APPVIEW_HOSTS) - 1:
                    raise
        if last_error is not None:
            raise last_error
        raise httpx.NetworkError("No Bluesky AppView host was attempted")

    def _metrics(
        self,
        posts: list[Any],
        issuer: SocialIssuer,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, Any]:
        seen_uris: set[str] = set()
        authors: set[str] = set()
        representative_urls: list[str] = []
        newest_at: datetime | None = None
        for post in posts:
            if not isinstance(post, Mapping):
                continue
            record = post.get("record")
            author = post.get("author")
            if not isinstance(record, Mapping) or not isinstance(author, Mapping):
                continue
            text = str(record.get("text") or "")
            if not self._matches(text, issuer):
                continue
            created_at = self._parse_datetime(record.get("createdAt") or post.get("indexedAt"))
            if created_at is None:
                continue
            if start is not None and created_at < start:
                continue
            if end is not None and created_at >= end:
                continue
            uri = str(post.get("uri") or "")
            if not uri.startswith("at://") or uri in seen_uris:
                continue
            seen_uris.add(uri)
            identity = str(author.get("did") or author.get("handle") or "")
            if identity:
                authors.add(identity)
            if newest_at is None or created_at > newest_at:
                newest_at = created_at
            url = self._post_url(uri, str(author.get("handle") or ""))
            if url and len(representative_urls) < 3:
                representative_urls.append(url)
        return {
            "post_count": len(seen_uris),
            "unique_authors": len(authors),
            "uri_sha256s": sorted(self._sha256(value) for value in seen_uris),
            "author_sha256s": sorted(self._sha256(value) for value in authors),
            "representative_urls": representative_urls,
            "newest_at": newest_at.isoformat() if newest_at else None,
        }

    def _record_window(
        self,
        issuer: SocialIssuer,
        start: datetime,
        end: datetime,
        metrics: dict[str, Any],
        *,
        coverage_state: str,
    ) -> None:
        self.store.record_social_bucket(
            issuer_key=issuer.issuer_key,
            source_id=self.provider,
            bucket_at=start,
            metrics={
                **metrics,
                "coverage": 1.0 if coverage_state == "adequate" else 0.0,
                "coverage_state": coverage_state,
                "partial_population": True,
                "search_model": "ranked_incomplete",
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
            },
        )
        self.store.prune_social_buckets(
            issuer.issuer_key,
            self.provider,
            before=start - timedelta(days=13),
        )

    def _cache_only_result(self, issuer: SocialIssuer, now: datetime) -> AdapterResult:
        state = self.store.collector_state(self.provider, issuer.issuer_key)
        if state is None:
            return self._warm_up_result(now, 0)
        status = self._status(state.get("status"))
        last_checked = self._parse_datetime(state.get("last_checked_at"))
        if status not in {SourceStatus.FRESH, SourceStatus.NO_OBSERVATIONS}:
            error_class = str(state.get("error_class") or "collector_failure")
            return self._result(
                status=status,
                now=now,
                warning=(
                    f"Bluesky forward collection is unavailable: {error_class} "
                    f"({status.value}); cached attention remains neutral."
                ),
                degraded=True,
            )
        if last_checked is None:
            return self._warm_up_result(now, 0)
        age_seconds = max(0, int((now - last_checked).total_seconds()))
        if age_seconds > self.max_cache_age_seconds:
            return self._result(
                status=SourceStatus.STALE,
                now=now,
                warning=(
                    f"Bluesky forward cache was last checked {age_seconds} seconds ago; "
                    "cached attention remains neutral."
                ),
                degraded=True,
            )

        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=COMPARISON_DAYS * 2)
        buckets = self.store.social_buckets(issuer.issuer_key, self.provider, start)
        by_day = {self._as_utc(bucket["bucket_at"]): bucket for bucket in buckets}
        expected_days = [start + timedelta(days=index) for index in range(14)]
        present = [by_day[day] for day in expected_days if day in by_day]
        adequate = [
            bucket
            for bucket in present
            if bucket.get("coverage_state") == "adequate"
            and float(bucket.get("coverage", 0.0)) == 1.0
        ]
        if len(present) < 14:
            oldest = min((bucket["bucket_at"] for bucket in buckets), default=None)
            if oldest is not None and self._as_utc(oldest) <= start:
                return self._coverage_gap_result(now, len(adequate))
            return self._warm_up_result(now, len(adequate))
        if len(adequate) < 14:
            return self._coverage_gap_result(now, len(adequate))
        baseline = self._combine_buckets(present[:COMPARISON_DAYS])
        current = self._combine_buckets(present[COMPARISON_DAYS:])
        return self._attention_result(issuer, now, baseline, current)

    def _warm_up_result(self, now: datetime, adequate_days: int) -> AdapterResult:
        return self._result(
            status=SourceStatus.NO_OBSERVATIONS,
            now=now,
            warning=(
                f"Bluesky partial public attention warm_up: {adequate_days} of 14 "
                "adequate forward daily buckets; no trend was inferred."
            ),
        )

    def _coverage_gap_result(self, now: datetime, adequate_days: int) -> AdapterResult:
        return self._result(
            status=SourceStatus.STALE,
            now=now,
            warning=(
                f"Bluesky forward coverage gap: {adequate_days} of 14 daily buckets "
                "were adequate; no trend was inferred."
            ),
            degraded=True,
        )

    @staticmethod
    def _combine_buckets(buckets: list[dict[str, Any]]) -> dict[str, Any]:
        author_hashes: set[str] = set()
        representative_urls: list[str] = []
        raw_hashes: list[str] = []
        newest_at: datetime | None = None
        post_count = 0
        for bucket in reversed(buckets):
            post_count += int(bucket.get("post_count", 0))
            author_hashes.update(str(value) for value in bucket.get("author_sha256s", []))
            raw_hash = str(bucket.get("raw_sha256") or "")
            if raw_hash:
                raw_hashes.append(raw_hash)
            parsed = BlueskyAdapter._parse_datetime(bucket.get("newest_at"))
            if parsed is not None and (newest_at is None or parsed > newest_at):
                newest_at = parsed
            for url in bucket.get("representative_urls", []):
                if url not in representative_urls and len(representative_urls) < 3:
                    representative_urls.append(str(url))
        return {
            "post_count": post_count,
            "unique_authors": len(author_hashes),
            "representative_urls": representative_urls,
            "newest_at": newest_at.isoformat() if newest_at else None,
            "raw_sha256": (
                BlueskyAdapter._sha256("".join(sorted(raw_hashes)))
                if raw_hashes
                else None
            ),
        }

    def _attention_result(
        self,
        issuer: SocialIssuer,
        now: datetime,
        baseline: dict[str, Any],
        current: dict[str, Any],
    ) -> AdapterResult:
        baseline_count = int(baseline.get("post_count", 0))
        current_count = int(current.get("post_count", 0))
        baseline_authors = int(baseline.get("unique_authors", 0))
        current_authors = int(current.get("unique_authors", 0))
        if (
            baseline_count < MIN_POSTS_PER_WINDOW
            or current_count < MIN_POSTS_PER_WINDOW
            or baseline_authors < MIN_AUTHORS_PER_WINDOW
            or current_authors < MIN_AUTHORS_PER_WINDOW
        ):
            return self._result(
                status=SourceStatus.NO_OBSERVATIONS,
                now=now,
                warning=(
                    "Bluesky partial public attention sample_insufficient across the "
                    "two locally observed 7-day windows; no trend was inferred."
                ),
            )
        urls = [str(url) for url in current.get("representative_urls", [])[:3]]
        newest_at = self._parse_datetime(current.get("newest_at")) or now
        evidence = Evidence(
            family=self.family,
            signal="attention_change",
            direction=Direction.NEUTRAL,
            strength=min(1.0, abs(current_count - baseline_count) / max(baseline_count, 1)),
            confidence=0.55,
            timestamp=newest_at,
            source_quality=0.55,
            change=Change(
                description=(
                    f"Bluesky exact-match posts changed from {baseline_count} to "
                    f"{current_count} across adequate locally observed 7-day windows."
                ),
                current_value=float(current_count),
                baseline_value=float(baseline_count),
                delta=float(current_count - baseline_count),
                unit="posts",
                comparison_window=(
                    "current 7 completed UTC days vs preceding equal window"
                ),
            ),
            sources=[
                Source(
                    name="Bluesky public AppView",
                    source_id=self.provider,
                    source_tier="partial_attention",
                    url=url,
                    canonical_url=url,
                    observed_at=now,
                    retrieved_at=now,
                    raw_sha256=str(current.get("raw_sha256") or "") or None,
                    parser_version=PARSER_VERSION,
                    policy_decision=PolicyDecision.APPROVED_PARTIAL_ATTENTION,
                )
                for url in (urls or [None])
            ],
            notes=(
                "Ranked, incomplete partial public attention from locally observed "
                "forward buckets only; no sentiment or market-wide inference is made "
                "and post bodies are never retained."
            ),
            raw_signal={
                "post_count": current_count,
                "baseline_post_count": baseline_count,
                "unique_authors": current_authors,
                "baseline_unique_authors": baseline_authors,
                "adequate_daily_bucket_ratio": 1.0,
            },
        )
        return self._result(status=SourceStatus.FRESH, now=now, evidence=[evidence])

    def _failure(
        self,
        issuer: SocialIssuer,
        now: datetime,
        bucket_at: datetime,
        status: SourceStatus,
        error_class: str,
    ) -> AdapterResult:
        self.store.record_social_bucket(
            issuer_key=issuer.issuer_key,
            source_id=self.provider,
            bucket_at=bucket_at,
            metrics={
                "post_count": 0,
                "unique_authors": 0,
                "uri_sha256s": [],
                "author_sha256s": [],
                "representative_urls": [],
                "coverage": 0.0,
                "coverage_state": status.value,
                "partial_population": True,
                "search_model": "ranked_incomplete",
                "window_start": bucket_at.isoformat(),
                "window_end": (bucket_at + timedelta(days=1)).isoformat(),
            },
        )
        self.store.prune_social_buckets(
            issuer.issuer_key,
            self.provider,
            before=bucket_at - timedelta(days=13),
        )
        self._record_state(
            issuer,
            now,
            status,
            succeeded=False,
            error_class=error_class,
        )
        return self._result(
            status=status,
            now=now,
            warning=f"Bluesky refresh failed: {error_class} ({status.value}).",
            degraded=True,
        )

    def _record_state(
        self,
        issuer: SocialIssuer,
        now: datetime,
        status: SourceStatus,
        *,
        succeeded: bool,
        error_class: str | None = None,
    ) -> None:
        self.store.update_collector_state(
            source_id=self.provider,
            issuer_key=issuer.issuer_key,
            feed_url=f"https://{self._preferred_host}{SEARCH_PATH}",
            status=status.value,
            checked_at=now,
            succeeded=succeeded,
            error_class=error_class,
        )

    def _bucket_at(
        self, issuer: SocialIssuer, bucket_at: datetime
    ) -> dict[str, Any] | None:
        for bucket in self.store.social_buckets(
            issuer.issuer_key, self.provider, bucket_at
        ):
            if self._as_utc(bucket["bucket_at"]) == self._as_utc(bucket_at):
                return bucket
        return None

    def _result(
        self,
        *,
        status: SourceStatus,
        now: datetime,
        evidence: list[Evidence] | None = None,
        warning: str | None = None,
        degraded: bool = False,
    ) -> AdapterResult:
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence or [],
            warnings=[warning] if warning else [],
            status=status,
            policy_decision=PolicyDecision.APPROVED_PARTIAL_ATTENTION,
            degraded=degraded,
            collected_at=now,
        )

    @staticmethod
    def _matches(text: str, issuer: SocialIssuer) -> bool:
        if any(
            re.search(rf"(?i)(?<!\w)\${re.escape(ticker)}(?!\w)", text)
            for ticker in issuer.tickers
        ):
            return True
        return any(
            re.search(rf"(?i)(?<!\w){re.escape(alias)}(?!\w)", text)
            for alias in issuer.exact_aliases
        )

    @staticmethod
    def _post_url(uri: str, handle: str) -> str | None:
        parts = uri.split("/")
        if len(parts) < 5 or not handle:
            return None
        return f"https://bsky.app/profile/{quote(handle, safe='.-')}/post/{quote(parts[-1])}"

    @staticmethod
    def _require_appview_url(url: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower().rstrip(".") not in APPVIEW_HOSTS
            or parsed.path.rstrip("/") != SEARCH_PATH
        ):
            raise ValueError("Bluesky request URL is outside documented AppView hosts")

    @staticmethod
    def _retry_delay(response: httpx.Response, now: datetime) -> float | None:
        value = response.headers.get("retry-after")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                pass
        reset = response.headers.get("ratelimit-reset")
        if reset:
            try:
                return max(0.0, float(reset) - now.timestamp())
            except ValueError:
                pass
        return None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    @staticmethod
    def _status(value: object) -> SourceStatus:
        try:
            return SourceStatus(str(value))
        except ValueError:
            return SourceStatus.UNAVAILABLE

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
