"""Bounded Bluesky AppView attention collector with official-host fallback."""

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
MAX_PAGES_PER_WINDOW = 3
MIN_POSTS_PER_WINDOW = 5
PARSER_VERSION = "bluesky-attention-v1"
BLUESKY_GATE = ProviderGate(concurrency=1, requests_per_second=1.0)


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
    ) -> None:
        self.store = store or EvidenceStore(str(Path(store_path).expanduser()))
        self.registry = registry
        self._client = client
        self._gate = gate
        self._clock = clock or (lambda: datetime.now(UTC))
        self._preferred_host = APPVIEW_HOSTS[0]

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        issuer = self.registry.get(ticker) or self.registry.get(ticker.replace(".", "-"))
        now = self._as_utc(self._clock())
        if issuer is None:
            return self._result(
                status=SourceStatus.NO_OBSERVATIONS,
                now=now,
                warning=f"No reviewed Bluesky aliases are registered for {ticker}.",
            )
        if self._client is not None:
            return await self._collect(self._client, issuer, lookback_days, now)
        headers = {
            "User-Agent": "CatalystEdgeMCP/0.1 bluesky-attention",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(
            headers=headers, timeout=3.0, follow_redirects=True
        ) as client:
            return await self._collect(client, issuer, lookback_days, now)

    async def _collect(
        self,
        client: httpx.AsyncClient,
        issuer: SocialIssuer,
        lookback_days: int,
        now: datetime,
    ) -> AdapterResult:
        window_days = min(lookback_days, 90)
        split = now - timedelta(days=max(1, window_days / 2))
        baseline_start = now - timedelta(days=window_days)
        try:
            baseline, baseline_complete = await self._fetch_window(
                client, issuer, baseline_start, split, now
            )
            current, current_complete = await self._fetch_window(
                client, issuer, split, now, now
            )
            self._record_window(issuer, split, baseline_start, split, baseline, baseline_complete)
            self._record_window(issuer, now, split, now, current, current_complete)
            if not baseline_complete or not current_complete:
                return self._result(
                    status=SourceStatus.STALE,
                    now=now,
                    warning=(
                        "Bluesky search pagination did not complete both comparison windows; "
                        "no attention trend was inferred."
                    ),
                    degraded=True,
                )
            return self._attention_result(
                issuer,
                now,
                baseline,
                current,
                comparison_days=window_days / 2,
            )
        except httpx.HTTPStatusError as exc:
            status = (
                SourceStatus.RATE_LIMITED
                if exc.response.status_code == 429
                else SourceStatus.PERMISSION_REQUIRED
                if exc.response.status_code in {401, 403}
                else SourceStatus.UNAVAILABLE
            )
            return self._failure(issuer, now, status, type(exc).__name__)
        except httpx.TimeoutException as exc:
            return self._failure(issuer, now, SourceStatus.TIMEOUT, type(exc).__name__)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            return self._failure(issuer, now, SourceStatus.SCHEMA_ERROR, type(exc).__name__)
        except httpx.HTTPError as exc:
            return self._failure(issuer, now, SourceStatus.UNAVAILABLE, type(exc).__name__)

    async def _fetch_window(
        self,
        client: httpx.AsyncClient,
        issuer: SocialIssuer,
        start: datetime,
        end: datetime,
        now: datetime,
    ) -> tuple[dict[str, Any], bool]:
        posts: list[Any] = []
        content_hashes: list[str] = []
        cursor: str | None = None
        hits_total: int | None = None
        complete = False
        for _ in range(MAX_PAGES_PER_WINDOW):
            params = {
                "q": issuer.bluesky_query,
                "limit": str(MAX_POSTS_PER_PAGE),
                "sort": "latest",
                "since": start.isoformat(),
                "until": end.isoformat(),
            }
            if cursor:
                params["cursor"] = cursor
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
            page = payload.get("posts") if isinstance(payload, dict) else None
            if not isinstance(page, list):
                raise ValueError("Bluesky response did not contain a post list")
            posts.extend(page)
            content_hashes.append(hashlib.sha256(content).hexdigest())
            raw_hits_total = payload.get("hitsTotal")
            hits_total = raw_hits_total if isinstance(raw_hits_total, int) else hits_total
            raw_cursor = payload.get("cursor")
            cursor = raw_cursor if isinstance(raw_cursor, str) and raw_cursor else None
            if not cursor or (hits_total is not None and hits_total <= len(posts)):
                complete = True
                break
        metrics = self._metrics(posts, issuer, start=start, end=end)
        metrics["raw_sha256"] = hashlib.sha256("".join(content_hashes).encode()).hexdigest()
        return metrics, complete

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
            "representative_urls": representative_urls,
            "newest_at": newest_at.isoformat() if newest_at else None,
        }

    def _record_window(
        self,
        issuer: SocialIssuer,
        bucket_at: datetime,
        start: datetime,
        end: datetime,
        metrics: dict[str, Any],
        complete: bool,
    ) -> None:
        self.store.record_social_bucket(
            issuer_key=issuer.issuer_key,
            source_id=self.provider,
            bucket_at=bucket_at.replace(hour=0, minute=0, second=0, microsecond=0),
            metrics={
                **metrics,
                "coverage": 1.0 if complete else 0.0,
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
            },
        )

    def _attention_result(
        self,
        issuer: SocialIssuer,
        now: datetime,
        baseline: dict[str, Any],
        current: dict[str, Any],
        *,
        comparison_days: float,
    ) -> AdapterResult:
        baseline_count = int(baseline.get("post_count", 0))
        current_count = int(current.get("post_count", 0))
        if baseline_count < MIN_POSTS_PER_WINDOW or current_count < MIN_POSTS_PER_WINDOW:
            return self._result(
                status=SourceStatus.NO_OBSERVATIONS,
                now=now,
                warning=(
                    "Bluesky attention sample is insufficient for a 7-day comparison; "
                    "collector outages remain in coverage."
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
                    f"{current_count} across complete {comparison_days:g}-day windows."
                ),
                current_value=float(current_count),
                baseline_value=float(baseline_count),
                delta=float(current_count - baseline_count),
                unit="posts",
                comparison_window=(
                    f"current {comparison_days:g} days vs preceding equal window"
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
                "Source-scoped partial attention only; no sentiment or market-wide "
                "inference is made and post bodies are not retained."
            ),
            raw_signal={
                "post_count": current_count,
                "baseline_post_count": baseline_count,
                "coverage_ratio": 1.0,
            },
        )
        return self._result(status=SourceStatus.FRESH, now=now, evidence=[evidence])

    def _failure(
        self,
        issuer: SocialIssuer,
        now: datetime,
        status: SourceStatus,
        error_class: str,
    ) -> AdapterResult:
        self.store.record_social_bucket(
            issuer_key=issuer.issuer_key,
            source_id=self.provider,
            bucket_at=now,
            metrics={"post_count": 0, "unique_authors": 0, "coverage": 0.0},
        )
        return self._result(
            status=status,
            now=now,
            warning=f"Bluesky refresh failed: {error_class} ({status.value}).",
            degraded=True,
        )

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
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
