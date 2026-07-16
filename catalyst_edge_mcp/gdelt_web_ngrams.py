"""Bounded batch ingestion for GDELT's downloadable Web NGrams feed."""

from __future__ import annotations

import hashlib
import json
import re
import zlib
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.discovery_registry import DISCOVERY_ISSUER_INDEX, DiscoveryIssuer
from catalyst_edge_mcp.evidence_store import EventObservation, EvidenceStore, normalize_title
from catalyst_edge_mcp.models import PolicyDecision, SourceStatus

GDELT_WEB_NGRAMS_BASE = (
    "https://storage.googleapis.com/data.gdeltproject.org/"
    "gdeltv5/weblegacy/ngrams"
)
PARSER_VERSION = "gdelt-web-ngrams-v1"
DISCOVERY_DELAY_MINUTES = 5
DISCOVERY_LOOKBACK_MINUTES = 20
MAX_FILES_PER_RUN = 5
MAX_ARTICLES_PER_ISSUER = 50
MAX_NGRAM_COMPRESSED_BYTES = 20_000_000
MAX_TOC_COMPRESSED_BYTES = 5_000_000
MAX_NGRAM_DECOMPRESSED_BYTES = 200_000_000
MAX_TOC_DECOMPRESSED_BYTES = 25_000_000
MAX_LINE_BYTES = 64_000
_FILE_PATH = re.compile(
    r"^/data\.gdeltproject\.org/gdeltv5/weblegacy/ngrams/"
    r"\d{14}\.(?:ngrams\.txt|toc\.json)\.gz$"
)


@dataclass(frozen=True, slots=True)
class GdeltWebNgramsResult:
    """Secret-free result for one requested issuer."""

    ticker: str
    status: SourceStatus
    evidence_count: int
    files_processed: int
    matched_documents: int
    degraded: bool = False
    warnings: tuple[str, ...] = ()


class NoRecentWebNgramsFile(RuntimeError):
    """Raised when the bounded discovery window contains no published file."""


class GdeltWebNgramsRefresher:
    """Download each official minute file once and match all reviewed issuers."""

    def __init__(
        self,
        store_path: str,
        *,
        registry: Mapping[str, DiscoveryIssuer] = DISCOVERY_ISSUER_INDEX,
        store: EvidenceStore | None = None,
        client: httpx.AsyncClient | None = None,
        clock=None,
        candidate_minutes: int = DISCOVERY_LOOKBACK_MINUTES,
        max_files: int = MAX_FILES_PER_RUN,
        request_timeout_seconds: float = 30.0,
    ) -> None:
        self.store = store or EvidenceStore(str(Path(store_path).expanduser()))
        self.registry = registry
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))
        self.candidate_minutes = candidate_minutes
        self.max_files = max_files
        self.request_timeout_seconds = request_timeout_seconds

    async def refresh(
        self, tickers: Sequence[str], lookback_days: int
    ) -> dict[str, GdeltWebNgramsResult]:
        """Refresh all requested issuers with one bounded set of shared downloads."""
        requested = self._reviewed_tickers(tickers)
        if not requested:
            return {}
        now = self._as_utc(self._clock())
        if self._client is not None:
            return await self._refresh(self._client, requested, lookback_days, now)
        headers = {
            "User-Agent": "CatalystEdgeMCP/0.1 gdelt-web-ngrams",
            "Accept": "application/gzip, application/octet-stream, application/json",
        }
        async with httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(
                self.request_timeout_seconds,
                connect=self.request_timeout_seconds,
            ),
            follow_redirects=False,
        ) as client:
            return await self._refresh(client, requested, lookback_days, now)

    async def _refresh(
        self,
        client: httpx.AsyncClient,
        requested: Mapping[str, DiscoveryIssuer],
        lookback_days: int,
        now: datetime,
    ) -> dict[str, GdeltWebNgramsResult]:
        issuers = {issuer.issuer_key: issuer for issuer in requested.values()}
        try:
            file_stamps = await self._available_file_stamps(client, now)
            if not file_stamps:
                raise NoRecentWebNgramsFile(
                    "No GDELT Web NGrams file was published in the bounded discovery window"
                )
            matched_counts: dict[str, int] = defaultdict(int)
            for file_stamp in reversed(file_stamps):
                ngrams_url = self._file_url(file_stamp, "ngrams.txt")
                toc_url = self._file_url(file_stamp, "toc.json")
                ngrams = await self._download(
                    client, ngrams_url, MAX_NGRAM_COMPRESSED_BYTES
                )
                toc = await self._download(client, toc_url, MAX_TOC_COMPRESSED_BYTES)
                matched_ids = self._match_document_ids(ngrams, issuers)
                ingested = self._ingest_toc(toc, matched_ids, issuers, now)
                for issuer_key, count in ingested.items():
                    matched_counts[issuer_key] += count

            latest_url = self._file_url(file_stamps[0], "ngrams.txt")
            for issuer in issuers.values():
                self.store.update_collector_state(
                    source_id="gdelt",
                    issuer_key=issuer.issuer_key,
                    feed_url=latest_url,
                    status=SourceStatus.FRESH.value,
                    checked_at=now,
                    succeeded=True,
                )
            return self._results(
                requested,
                lookback_days,
                now,
                files_processed=len(file_stamps),
                matched_counts=matched_counts,
            )
        except Exception as exc:
            status = self._failure_status(exc)
            for issuer in issuers.values():
                self.store.update_collector_state(
                    source_id="gdelt",
                    issuer_key=issuer.issuer_key,
                    feed_url=GDELT_WEB_NGRAMS_BASE,
                    status=status.value,
                    checked_at=now,
                    succeeded=False,
                    error_class=type(exc).__name__,
                )
            return self._results(
                requested,
                lookback_days,
                now,
                status=status,
                degraded=True,
                warning=(
                    f"GDELT Web NGrams refresh failed: {type(exc).__name__} "
                    f"({status.value})."
                ),
            )

    async def _available_file_stamps(
        self, client: httpx.AsyncClient, now: datetime
    ) -> list[str]:
        available: list[str] = []
        start = max(DISCOVERY_DELAY_MINUTES, 1)
        stop = max(self.candidate_minutes, start)
        for minutes_ago in range(start, stop + 1):
            candidate = (now - timedelta(minutes=minutes_ago)).replace(second=0, microsecond=0)
            stamp = candidate.strftime("%Y%m%d%H%M00")
            url = self._file_url(stamp, "toc.json")
            response = await client.head(url)
            self._require_endpoint(str(response.url))
            if response.status_code == 404:
                continue
            response.raise_for_status()
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_TOC_COMPRESSED_BYTES:
                raise ValueError("GDELT TOC file exceeded the compressed size limit")
            available.append(stamp)
            if len(available) >= self.max_files:
                break
        return available

    async def _download(
        self, client: httpx.AsyncClient, url: str, max_compressed_bytes: int
    ) -> bytes:
        response = await client.get(url)
        self._require_endpoint(str(response.url))
        response.raise_for_status()
        content = response.content
        if len(content) > max_compressed_bytes:
            raise ValueError("GDELT Web NGrams file exceeded the compressed size limit")
        return content

    def _match_document_ids(
        self, content: bytes, issuers: Mapping[str, DiscoveryIssuer]
    ) -> dict[str, set[str]]:
        aliases = {
            issuer_key: tuple(
                phrase
                for alias in issuer.query_aliases
                if (phrase := self._normalize_phrase(alias))
            )
            for issuer_key, issuer in issuers.items()
        }
        matched: dict[str, set[str]] = {}
        counts: dict[str, int] = defaultdict(int)
        for line in self._iter_gzip_lines(content, MAX_NGRAM_DECOMPRESSED_BYTES):
            try:
                doc_id, quadgram, _count = line.decode("utf-8").split("\t", 2)
            except (UnicodeDecodeError, ValueError):
                continue
            if not doc_id.isdigit():
                continue
            normalized = f" {self._normalize_phrase(quadgram)} "
            for issuer_key, issuer_aliases in aliases.items():
                if counts[issuer_key] >= MAX_ARTICLES_PER_ISSUER:
                    continue
                if not any(f" {alias} " in normalized for alias in issuer_aliases):
                    continue
                issuer_matches = matched.setdefault(doc_id, set())
                if issuer_key not in issuer_matches:
                    issuer_matches.add(issuer_key)
                    counts[issuer_key] += 1
        return matched

    def _ingest_toc(
        self,
        content: bytes,
        matched_ids: Mapping[str, set[str]],
        issuers: Mapping[str, DiscoveryIssuer],
        now: datetime,
    ) -> dict[str, int]:
        ingested: dict[str, int] = defaultdict(int)
        if not matched_ids:
            return ingested
        for line in self._iter_gzip_lines(content, MAX_TOC_DECOMPRESSED_BYTES):
            try:
                article = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(article, Mapping):
                continue
            issuer_keys = matched_ids.get(str(article.get("ID") or ""))
            if not issuer_keys:
                continue
            for issuer_key in issuer_keys:
                issuer = issuers.get(issuer_key)
                if issuer is None:
                    continue
                observation = self._article_observation(
                    article, issuer.issuer_key, now, line
                )
                if observation is None:
                    continue
                self.store.ingest_event(observation)
                ingested[issuer_key] += 1
        return ingested

    @staticmethod
    def _article_observation(
        article: Mapping[str, Any], issuer_key: str, now: datetime, raw_line: bytes
    ) -> EventObservation | None:
        title = " ".join(str(article.get("title") or "").split())[:240]
        url = str(article.get("url") or "").strip()
        published_at = GdeltWebNgramsRefresher._article_datetime(article.get("date"))
        parsed = urlsplit(url)
        if (
            not title
            or not normalize_title(title)
            or published_at is None
            or parsed.scheme.lower() != "https"
            or not parsed.hostname
        ):
            return None
        domain = parsed.hostname.lower().rstrip(".")[:100]
        return EventObservation(
            source_id="gdelt",
            source_name=f"GDELT discovery ({domain})",
            source_tier="discovery",
            issuer_key=issuer_key,
            record_id=url[:160],
            canonical_url=url,
            title=title,
            published_at=published_at,
            observed_at=now,
            retrieved_at=now,
            raw_sha256=hashlib.sha256(raw_line).hexdigest(),
            parser_version=PARSER_VERSION,
            policy_decision=PolicyDecision.APPROVED_DISCOVERY,
        )

    def _results(
        self,
        requested: Mapping[str, DiscoveryIssuer],
        lookback_days: int,
        now: datetime,
        *,
        files_processed: int = 0,
        matched_counts: Mapping[str, int] | None = None,
        status: SourceStatus | None = None,
        degraded: bool = False,
        warning: str | None = None,
    ) -> dict[str, GdeltWebNgramsResult]:
        counts = matched_counts or {}
        results: dict[str, GdeltWebNgramsResult] = {}
        for ticker, issuer in requested.items():
            evidence_count = len(
                self.store.list_events_for_source(
                    issuer.issuer_key, "gdelt", now - timedelta(days=lookback_days)
                )
            )
            effective_status = status or (
                SourceStatus.FRESH if evidence_count else SourceStatus.NO_OBSERVATIONS
            )
            warnings: tuple[str, ...] = ()
            if warning:
                warnings = (warning,)
            elif not evidence_count:
                warnings = (
                    f"No GDELT publisher links found for {ticker} in processed minute files.",
                )
            results[ticker] = GdeltWebNgramsResult(
                ticker=ticker,
                status=effective_status,
                evidence_count=evidence_count,
                files_processed=files_processed,
                matched_documents=counts.get(issuer.issuer_key, 0),
                degraded=degraded,
                warnings=warnings,
            )
        return results

    def _reviewed_tickers(
        self, tickers: Iterable[str]
    ) -> dict[str, DiscoveryIssuer]:
        reviewed: dict[str, DiscoveryIssuer] = {}
        for ticker in tickers:
            issuer = self.registry.get(ticker) or self.registry.get(ticker.replace(".", "-"))
            if issuer is not None:
                reviewed[ticker] = issuer
        return reviewed

    @staticmethod
    def _iter_gzip_lines(content: bytes, max_decompressed_bytes: int) -> Iterator[bytes]:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        buffer = b""
        decompressed = 0
        for offset in range(0, len(content), 64 * 1024):
            chunk = decompressor.decompress(content[offset : offset + 64 * 1024])
            decompressed += len(chunk)
            if decompressed > max_decompressed_bytes:
                raise ValueError("GDELT file exceeded the decompressed size limit")
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if len(line) > MAX_LINE_BYTES:
                    raise ValueError("GDELT file contained an oversized line")
                if line:
                    yield line
            if len(buffer) > MAX_LINE_BYTES:
                raise ValueError("GDELT file contained an oversized line")
        tail = decompressor.flush()
        decompressed += len(tail)
        if decompressed > max_decompressed_bytes:
            raise ValueError("GDELT file exceeded the decompressed size limit")
        buffer += tail
        if not decompressor.eof:
            raise ValueError("GDELT file was not a complete gzip stream")
        if buffer:
            if len(buffer) > MAX_LINE_BYTES:
                raise ValueError("GDELT file contained an oversized line")
            yield buffer

    @staticmethod
    def _normalize_phrase(value: str) -> str:
        return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())

    @staticmethod
    def _article_datetime(value: object) -> datetime | None:
        text = str(value or "").strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    @staticmethod
    def _file_url(stamp: str, kind: str) -> str:
        if not re.fullmatch(r"\d{14}", stamp) or kind not in {"ngrams.txt", "toc.json"}:
            raise ValueError("invalid GDELT Web NGrams file identifier")
        return f"{GDELT_WEB_NGRAMS_BASE}/{stamp}.{kind}.gz"

    @staticmethod
    def _require_endpoint(url: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme.lower() != "https"
            or (parsed.hostname or "").lower().rstrip(".") != "storage.googleapis.com"
            or not _FILE_PATH.fullmatch(parsed.path)
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("GDELT Web NGrams URL is outside the reviewed official endpoint")

    @staticmethod
    def _failure_status(exc: Exception) -> SourceStatus:
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 429:
                return SourceStatus.RATE_LIMITED
            if exc.response.status_code in {401, 403}:
                return SourceStatus.PERMISSION_REQUIRED
            return SourceStatus.STALE
        if isinstance(exc, httpx.TimeoutException):
            return SourceStatus.TIMEOUT
        if isinstance(exc, NoRecentWebNgramsFile):
            return SourceStatus.STALE
        if isinstance(exc, (ValueError, TypeError, zlib.error)):
            return SourceStatus.SCHEMA_ERROR
        if isinstance(exc, httpx.HTTPError):
            return SourceStatus.STALE
        return SourceStatus.UNAVAILABLE

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
