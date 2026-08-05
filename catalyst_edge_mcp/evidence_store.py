"""SQLite/WAL evidence state and canonical event graph."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from rapidfuzz import fuzz

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import ClaimSourcePage, ClaimSourceReference, PolicyDecision
from catalyst_edge_mcp.source_policy import SOURCE_POLICIES, source_attributions

TRACKING_QUERY_KEYS = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source"})
SOURCE_RANKS = {
    "primary_regulator": 100,
    "issuer_primary": 95,
    "authorized_vendor": 80,
    "discovery": 50,
}
CORRECTION_PATTERN = re.compile(r"\b(correction|corrected|revision|revised|update|updated)\b")
NUMBER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)*%?\b")


def canonicalize_url(value: str) -> str:
    """Normalize an HTTPS source URL without inventing a replacement location."""
    parts = urlsplit(value.strip())
    if parts.scheme.lower() != "https" or not parts.hostname:
        raise ValueError("Source URL must be absolute HTTPS")
    host = parts.hostname.lower().rstrip(".")
    port = f":{parts.port}" if parts.port and parts.port != 443 else ""
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
        )
    )
    return urlunsplit(("https", host + port, path, query, ""))


def normalize_title(value: str) -> str:
    text = value.casefold().replace("&", " and ")
    normalized = "".join(
        character if character.isalnum() or character == "%" else " "
        for character in text
    )
    return " ".join(normalized.split())


@dataclass(frozen=True, slots=True)
class EventObservation:
    source_id: str
    source_name: str
    source_tier: str
    issuer_key: str
    record_id: str
    canonical_url: str
    title: str
    published_at: datetime
    observed_at: datetime
    retrieved_at: datetime
    raw_sha256: str | None
    parser_version: str
    policy_decision: PolicyDecision


@dataclass(frozen=True, slots=True)
class EntityMatchAudit:
    source_id: str
    issuer_key: str
    document_id: str
    canonical_url: str
    published_at: datetime
    observed_at: datetime
    retrieved_at: datetime
    toc_sha256: str
    context_sha256: str
    ruleset_version: str
    accepted: bool
    reason_code: str
    selected_rule_id: str | None
    selected_rule_version: str | None
    candidate_rule_ids: tuple[str, ...]
    matched_aliases: tuple[str, ...]
    required_context_matches: tuple[str, ...]
    negative_context_matches: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoredSource:
    source_id: str
    source_name: str
    source_tier: str
    record_id: str
    canonical_url: str
    published_at: datetime
    observed_at: datetime
    retrieved_at: datetime
    raw_sha256: str | None
    parser_version: str
    policy_decision: PolicyDecision


@dataclass(frozen=True, slots=True)
class StoredEvent:
    event_id: int
    issuer_key: str
    title: str
    normalized_title: str
    published_at: datetime
    version: int
    correction_of_event_id: int | None
    primary_source: StoredSource
    related_urls: tuple[str, ...]
    source_count: int
    source_tiers: tuple[str, ...]
    claim_id: str
    supporting_source_ids: tuple[str, ...]


class EvidenceStore:
    """Small synchronous state store used inside bounded collector calls."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def _connect(self) -> sqlite3.Connection:
        if self._connection is not None:
            return self._connection
        if self.path != ":memory:":
            Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            str(Path(self.path).expanduser()) if self.path != ":memory:" else self.path,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS source_observation (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_tier TEXT NOT NULL,
                issuer_key TEXT NOT NULL,
                record_id TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                raw_sha256 TEXT,
                parser_version TEXT NOT NULL,
                policy_decision TEXT NOT NULL,
                observation_fingerprint TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS canonical_event (
                id INTEGER PRIMARY KEY,
                issuer_key TEXT NOT NULL,
                exact_fingerprint TEXT NOT NULL UNIQUE,
                normalized_title TEXT NOT NULL,
                display_title TEXT NOT NULL,
                published_at TEXT NOT NULL,
                correction_of_event_id INTEGER REFERENCES canonical_event(id),
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_event_issuer_time
                ON canonical_event(issuer_key, published_at);
            CREATE TABLE IF NOT EXISTS event_source (
                event_id INTEGER NOT NULL REFERENCES canonical_event(id),
                observation_id INTEGER NOT NULL REFERENCES source_observation(id),
                source_rank INTEGER NOT NULL,
                is_primary INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(event_id, observation_id)
            );
            CREATE TABLE IF NOT EXISTS event_claim (
                event_id INTEGER PRIMARY KEY REFERENCES canonical_event(id),
                claim_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS claim_source (
                id INTEGER PRIMARY KEY,
                claim_id TEXT NOT NULL REFERENCES event_claim(claim_id),
                observation_id INTEGER NOT NULL REFERENCES source_observation(id),
                source_reference_id TEXT NOT NULL,
                UNIQUE(claim_id, observation_id)
            );
            CREATE INDEX IF NOT EXISTS idx_claim_source_page
                ON claim_source(claim_id, id);
            CREATE TABLE IF NOT EXISTS insider_transaction (
                id INTEGER PRIMARY KEY, issuer_key TEXT NOT NULL, accession TEXT NOT NULL,
                transaction_json TEXT NOT NULL, observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS insider_cluster (
                id INTEGER PRIMARY KEY, issuer_key TEXT NOT NULL, cluster_json TEXT NOT NULL,
                observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS social_bucket (
                id INTEGER PRIMARY KEY, issuer_key TEXT NOT NULL, source_id TEXT NOT NULL,
                bucket_at TEXT NOT NULL, metrics_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS collector_state (
                source_id TEXT NOT NULL,
                issuer_key TEXT NOT NULL,
                feed_url TEXT NOT NULL,
                etag TEXT,
                last_modified TEXT,
                last_checked_at TEXT,
                last_success_at TEXT,
                status TEXT NOT NULL,
                error_class TEXT,
                PRIMARY KEY(source_id, issuer_key)
            );
            CREATE TABLE IF NOT EXISTS source_policy (
                source_id TEXT PRIMARY KEY,
                decision TEXT NOT NULL,
                tier TEXT NOT NULL,
                retention TEXT NOT NULL,
                reviewed_on TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entity_match_audit (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                issuer_key TEXT NOT NULL,
                document_id TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                published_at TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                toc_sha256 TEXT NOT NULL,
                context_sha256 TEXT NOT NULL,
                ruleset_version TEXT NOT NULL,
                accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
                reason_code TEXT NOT NULL,
                selected_rule_id TEXT,
                selected_rule_version TEXT,
                candidate_rule_ids_json TEXT NOT NULL,
                matched_aliases_json TEXT NOT NULL,
                required_context_json TEXT NOT NULL,
                negative_context_json TEXT NOT NULL,
                audit_fingerprint TEXT NOT NULL UNIQUE
            );
            CREATE INDEX IF NOT EXISTS idx_entity_match_audit_issuer_time
                ON entity_match_audit(issuer_key, observed_at);
            """
        )
        for policy in SOURCE_POLICIES.values():
            connection.execute(
                """
                INSERT INTO source_policy(source_id, decision, tier, retention, reviewed_on)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    decision=excluded.decision, tier=excluded.tier,
                    retention=excluded.retention, reviewed_on=excluded.reviewed_on
                """,
                (
                    policy.source_id,
                    policy.decision.value,
                    policy.tier,
                    policy.retention,
                    policy.reviewed_on,
                ),
            )
        self._backfill_claim_sources(connection)
        connection.commit()
        self._connection = connection
        return connection

    def journal_mode(self) -> str:
        with self._lock:
            return str(self._connect().execute("PRAGMA journal_mode").fetchone()[0]).lower()

    def table_names(self) -> set[str]:
        with self._lock:
            rows = (
                self._connect()
                .execute("SELECT name FROM sqlite_master WHERE type='table'")
                .fetchall()
            )
            return {str(row[0]) for row in rows}

    def collector_state(self, source_id: str, issuer_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = (
                self._connect()
                .execute(
                    "SELECT * FROM collector_state WHERE source_id=? AND issuer_key=?",
                    (source_id, issuer_key),
                )
                .fetchone()
            )
            return dict(row) if row is not None else None

    def update_collector_state(
        self,
        *,
        source_id: str,
        issuer_key: str,
        feed_url: str,
        status: str,
        checked_at: datetime,
        succeeded: bool,
        etag: str | None = None,
        last_modified: str | None = None,
        error_class: str | None = None,
    ) -> None:
        with self._lock:
            connection = self._connect()
            previous = self.collector_state(source_id, issuer_key) or {}
            connection.execute(
                """
                INSERT INTO collector_state(
                    source_id, issuer_key, feed_url, etag, last_modified,
                    last_checked_at, last_success_at, status, error_class
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, issuer_key) DO UPDATE SET
                    feed_url=excluded.feed_url, etag=excluded.etag,
                    last_modified=excluded.last_modified,
                    last_checked_at=excluded.last_checked_at,
                    last_success_at=excluded.last_success_at,
                    status=excluded.status, error_class=excluded.error_class
                """,
                (
                    source_id,
                    issuer_key,
                    feed_url,
                    etag if etag is not None else previous.get("etag"),
                    last_modified if last_modified is not None else previous.get("last_modified"),
                    self._iso(checked_at),
                    self._iso(checked_at) if succeeded else previous.get("last_success_at"),
                    status,
                    error_class,
                ),
            )
            connection.commit()

    def ingest_event(
        self, observation: EventObservation, *, group_event_id: int | None = None
    ) -> StoredEvent:
        with self._lock:
            connection = self._connect()
            if group_event_id is not None:
                grouped_event = connection.execute(
                    "SELECT issuer_key FROM canonical_event WHERE id=?", (group_event_id,)
                ).fetchone()
                if (
                    grouped_event is None
                    or str(grouped_event["issuer_key"]) != observation.issuer_key
                ):
                    raise ValueError("Grouped source must reference an event for the same issuer")
            canonical_url = canonicalize_url(observation.canonical_url)
            normalized = normalize_title(observation.title)
            if not normalized:
                raise ValueError("Event title is empty after normalization")
            observation_fingerprint = self._hash(
                observation.source_id, observation.record_id, canonical_url, normalized
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO source_observation(
                    source_id, source_name, source_tier, issuer_key, record_id,
                    canonical_url, title, published_at, observed_at, retrieved_at,
                    raw_sha256, parser_version, policy_decision, observation_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.source_id,
                    observation.source_name,
                    observation.source_tier,
                    observation.issuer_key,
                    observation.record_id,
                    canonical_url,
                    observation.title,
                    self._iso(observation.published_at),
                    self._iso(observation.observed_at),
                    self._iso(observation.retrieved_at),
                    observation.raw_sha256,
                    observation.parser_version,
                    observation.policy_decision.value,
                    observation_fingerprint,
                ),
            )
            observation_id = int(
                connection.execute(
                    "SELECT id FROM source_observation WHERE observation_fingerprint=?",
                    (observation_fingerprint,),
                ).fetchone()[0]
            )
            if group_event_id is not None:
                event_id = group_event_id
            else:
                exact_fingerprint = self._hash(observation.issuer_key, normalized, canonical_url)
                event = connection.execute(
                    "SELECT * FROM canonical_event WHERE exact_fingerprint=?",
                    (exact_fingerprint,),
                ).fetchone()
                if event is None:
                    event = self._fuzzy_candidate(
                        connection,
                        observation.issuer_key,
                        normalized,
                        observation.published_at,
                    )
                    correction = event is not None and self._is_correction(
                        normalized, str(event["normalized_title"])
                    )
                    if event is None or correction:
                        now = self._iso(observation.retrieved_at)
                        correction_of = int(event["id"]) if correction else None
                        version = int(event["version"]) + 1 if correction else 1
                        cursor = connection.execute(
                            """
                            INSERT INTO canonical_event(
                                issuer_key, exact_fingerprint, normalized_title, display_title,
                                published_at, correction_of_event_id, version,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                observation.issuer_key,
                                exact_fingerprint,
                                normalized,
                                observation.title,
                                self._iso(observation.published_at),
                                correction_of,
                                version,
                                now,
                                now,
                            ),
                        )
                        event_id = int(cursor.lastrowid)
                    else:
                        event_id = int(event["id"])
                else:
                    event_id = int(event["id"])
            rank = SOURCE_RANKS.get(observation.source_tier, 10)
            connection.execute(
                """
                INSERT OR IGNORE INTO event_source(event_id, observation_id, source_rank)
                VALUES (?, ?, ?)
                """,
                (event_id, observation_id, rank),
            )
            claim_id = self._ensure_claim(connection, event_id)
            self._link_claim_source(connection, claim_id, observation_id)
            self._rank_primary_source(connection, event_id)
            connection.commit()
            return self._stored_event(connection, event_id)

    def record_entity_match_audit(self, audit: EntityMatchAudit) -> bool:
        """Append one idempotent metadata-only entity decision."""
        with self._lock:
            connection = self._connect()
            canonical_url = canonicalize_url(audit.canonical_url)
            fingerprint = self._hash(
                audit.source_id,
                audit.issuer_key,
                audit.document_id,
                audit.toc_sha256,
                audit.context_sha256,
                audit.ruleset_version,
            )
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO entity_match_audit(
                    source_id, issuer_key, document_id, canonical_url,
                    published_at, observed_at, retrieved_at, toc_sha256,
                    context_sha256, ruleset_version, accepted, reason_code,
                    selected_rule_id, selected_rule_version,
                    candidate_rule_ids_json, matched_aliases_json,
                    required_context_json, negative_context_json, audit_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit.source_id,
                    audit.issuer_key,
                    audit.document_id,
                    canonical_url,
                    self._iso(audit.published_at),
                    self._iso(audit.observed_at),
                    self._iso(audit.retrieved_at),
                    audit.toc_sha256,
                    audit.context_sha256,
                    audit.ruleset_version,
                    int(audit.accepted),
                    audit.reason_code,
                    audit.selected_rule_id,
                    audit.selected_rule_version,
                    json.dumps(audit.candidate_rule_ids, separators=(",", ":")),
                    json.dumps(audit.matched_aliases, separators=(",", ":")),
                    json.dumps(audit.required_context_matches, separators=(",", ":")),
                    json.dumps(audit.negative_context_matches, separators=(",", ":")),
                    fingerprint,
                ),
            )
            connection.commit()
            return cursor.rowcount == 1

    def entity_match_audits(
        self,
        issuer_key: str | None = None,
        *,
        since: datetime | None = None,
        accepted: bool | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Return bounded decision metadata for diagnostics and fixed audit tests."""
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._lock:
            connection = self._connect()
            clauses: list[str] = []
            parameters: list[Any] = []
            if issuer_key is not None:
                clauses.append("issuer_key=?")
                parameters.append(issuer_key)
            if since is not None:
                clauses.append("observed_at>=?")
                parameters.append(self._iso(since))
            if accepted is not None:
                clauses.append("accepted=?")
                parameters.append(int(accepted))
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            parameters.append(limit)
            rows = connection.execute(
                f"SELECT * FROM entity_match_audit {where} ORDER BY id ASC LIMIT ?",
                tuple(parameters),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["accepted"] = bool(item["accepted"])
                for source, target in (
                    ("candidate_rule_ids_json", "candidate_rule_ids"),
                    ("matched_aliases_json", "matched_aliases"),
                    ("required_context_json", "required_context_matches"),
                    ("negative_context_json", "negative_context_matches"),
                ):
                    item[target] = tuple(json.loads(str(item.pop(source))))
                result.append(item)
            return result

    def entity_match_audit_summary(
        self, issuer_key: str, *, since: datetime | None = None
    ) -> dict[str, Any]:
        """Return aggregate decision counts without source URLs or matched text."""
        with self._lock:
            connection = self._connect()
            since_clause = " AND observed_at>=?" if since is not None else ""
            parameters: tuple[Any, ...] = (
                (issuer_key, self._iso(since)) if since is not None else (issuer_key,)
            )
            totals = connection.execute(
                f"""
                SELECT COUNT(*) AS candidates,
                    COALESCE(SUM(accepted), 0) AS accepted
                FROM entity_match_audit WHERE issuer_key=?{since_clause}
                """,
                parameters,
            ).fetchone()
            reasons = connection.execute(
                f"""
                SELECT reason_code, COUNT(*) AS count
                FROM entity_match_audit
                WHERE issuer_key=? AND accepted=0{since_clause}
                GROUP BY reason_code ORDER BY reason_code ASC
                """,
                parameters,
            ).fetchall()
            candidates = int(totals["candidates"])
            accepted = int(totals["accepted"])
            return {
                "candidate_documents": candidates,
                "accepted_documents": accepted,
                "rejected_documents": candidates - accepted,
                "rejection_reasons": {
                    str(row["reason_code"]): int(row["count"]) for row in reasons
                },
            }

    def claim_sources(self, claim_id: str, *, cursor: int = 0, limit: int = 20) -> ClaimSourcePage:
        """Return one bounded immutable claim/source relation page."""
        if not re.fullmatch(r"clm_[0-9a-f]{64}", claim_id):
            raise ValueError("claim_id must be a canonical immutable claim ID")
        if cursor < 0:
            raise ValueError("cursor must be nonnegative")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        with self._lock:
            connection = self._connect()
            exists = connection.execute(
                "SELECT 1 FROM event_claim WHERE claim_id=?", (claim_id,)
            ).fetchone()
            if exists is None:
                raise ValueError("Unknown claim_id")
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM claim_source WHERE claim_id=?", (claim_id,)
                ).fetchone()[0]
            )
            claim_source_ids = [
                str(row[0])
                for row in connection.execute(
                    """
                    SELECT DISTINCT observation.source_id
                    FROM claim_source AS relation
                    JOIN source_observation AS observation
                        ON observation.id=relation.observation_id
                    WHERE relation.claim_id=?
                    """,
                    (claim_id,),
                ).fetchall()
            ]
            rows = connection.execute(
                """
                SELECT relation.id AS relation_id, relation.source_reference_id,
                    observation.*
                FROM claim_source AS relation
                JOIN source_observation AS observation
                    ON observation.id=relation.observation_id
                WHERE relation.claim_id=? AND relation.id>?
                ORDER BY relation.id ASC LIMIT ?
                """,
                (claim_id, cursor, limit + 1),
            ).fetchall()
            page_rows = rows[:limit]
            sources = [
                ClaimSourceReference(
                    source_reference_id=str(row["source_reference_id"]),
                    source_id=str(row["source_id"]),
                    source_name=str(row["source_name"]),
                    source_tier=str(row["source_tier"]),
                    accession_or_record_id=str(row["record_id"]),
                    canonical_url=str(row["canonical_url"]),
                    published_at=self._datetime(row["published_at"]),
                    observed_at=self._datetime(row["observed_at"]),
                    retrieved_at=self._datetime(row["retrieved_at"]),
                    raw_sha256=str(row["raw_sha256"]) if row["raw_sha256"] else None,
                    parser_version=str(row["parser_version"]),
                    policy_decision=PolicyDecision(str(row["policy_decision"])),
                )
                for row in page_rows
            ]
            next_cursor = (
                int(page_rows[-1]["relation_id"])
                if len(rows) > limit and page_rows
                else None
            )
            return ClaimSourcePage(
                claim_id=claim_id,
                sources=sources,
                total_sources=total,
                cursor=cursor,
                next_cursor=next_cursor,
                attributions=source_attributions(claim_source_ids),
            )

    def list_events(self, issuer_key: str, since: datetime) -> list[StoredEvent]:
        with self._lock:
            connection = self._connect()
            rows = connection.execute(
                """
                SELECT id FROM canonical_event
                WHERE issuer_key=? AND published_at>=?
                ORDER BY published_at DESC, id DESC LIMIT 100
                """,
                (issuer_key, self._iso(since)),
            ).fetchall()
            return [self._stored_event(connection, int(row["id"])) for row in rows]

    def list_events_for_source(
        self,
        issuer_key: str,
        source_id: str,
        since: datetime,
        *,
        title_predicate: Callable[[str, datetime], bool] | None = None,
    ) -> list[StoredEvent]:
        """List canonical events observed by one source without changing global ranking."""
        with self._lock:
            connection = self._connect()
            rows = connection.execute(
                """
                SELECT DISTINCT event.id FROM canonical_event AS event
                JOIN event_source ON event_source.event_id=event.id
                JOIN source_observation AS observation
                    ON observation.id=event_source.observation_id
                WHERE event.issuer_key=? AND observation.source_id=?
                    AND event.published_at>=?
                ORDER BY event.published_at DESC, event.id DESC LIMIT 100
                """,
                (issuer_key, source_id, self._iso(since)),
            ).fetchall()
            events = (
                self._stored_event(
                    connection,
                    int(row["id"]),
                    source_id=source_id,
                    title_predicate=title_predicate,
                )
                for row in rows
            )
            return [event for event in events if event is not None]

    def source_observation_title_records(
        self,
        issuer_key: str,
        source_id: str,
        since: datetime,
        *,
        limit: int = 500,
    ) -> tuple[tuple[str, datetime], ...]:
        """Return bounded stored titles and publication times for policy checks."""
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._lock:
            rows = self._connect().execute(
                """
                SELECT observation.title, observation.published_at
                FROM canonical_event AS event
                JOIN event_source ON event_source.event_id=event.id
                JOIN source_observation AS observation
                    ON observation.id=event_source.observation_id
                WHERE event.issuer_key=? AND observation.source_id=?
                    AND event.published_at>=?
                ORDER BY event.published_at DESC, event.id DESC, observation.id ASC
                LIMIT ?
                """,
                (issuer_key, source_id, self._iso(since), limit),
            ).fetchall()
            return tuple(
                (str(row["title"]), self._datetime(row["published_at"]))
                for row in rows
            )

    def record_social_bucket(
        self,
        *,
        issuer_key: str,
        source_id: str,
        bucket_at: datetime,
        metrics: dict[str, Any],
    ) -> None:
        """Persist one bounded derived attention bucket, never post bodies."""
        with self._lock:
            connection = self._connect()
            bucket = self._iso(bucket_at)
            connection.execute(
                "DELETE FROM social_bucket WHERE issuer_key=? AND source_id=? AND bucket_at=?",
                (issuer_key, source_id, bucket),
            )
            connection.execute(
                """
                INSERT INTO social_bucket(issuer_key, source_id, bucket_at, metrics_json)
                VALUES (?, ?, ?, ?)
                """,
                (issuer_key, source_id, bucket, json.dumps(metrics, sort_keys=True)),
            )
            connection.commit()

    def social_buckets(
        self, issuer_key: str, source_id: str, since: datetime
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = (
                self._connect()
                .execute(
                    """
                SELECT bucket_at, metrics_json FROM social_bucket
                WHERE issuer_key=? AND source_id=? AND bucket_at>=?
                ORDER BY bucket_at ASC
                """,
                    (issuer_key, source_id, self._iso(since)),
                )
                .fetchall()
            )
            return [
                {
                    "bucket_at": self._datetime(row["bucket_at"]),
                    **json.loads(str(row["metrics_json"])),
                }
                for row in rows
            ]

    def prune_social_buckets(
        self,
        issuer_key: str,
        source_id: str,
        *,
        before: datetime,
    ) -> int:
        """Delete derived social buckets outside the rolling product window."""
        with self._lock:
            connection = self._connect()
            cursor = connection.execute(
                """
                DELETE FROM social_bucket
                WHERE issuer_key=? AND source_id=? AND bucket_at<?
                """,
                (issuer_key, source_id, self._iso(before)),
            )
            connection.commit()
            return max(0, int(cursor.rowcount))

    def delete_social_cache(self, issuer_key: str, source_id: str) -> dict[str, int]:
        """Delete one issuer's social buckets and collector state on request."""
        with self._lock:
            connection = self._connect()
            bucket_cursor = connection.execute(
                "DELETE FROM social_bucket WHERE issuer_key=? AND source_id=?",
                (issuer_key, source_id),
            )
            state_cursor = connection.execute(
                "DELETE FROM collector_state WHERE issuer_key=? AND source_id=?",
                (issuer_key, source_id),
            )
            connection.commit()
            return {
                "buckets_deleted": max(0, int(bucket_cursor.rowcount)),
                "collector_states_deleted": max(0, int(state_cursor.rowcount)),
            }

    def _fuzzy_candidate(
        self,
        connection: sqlite3.Connection,
        issuer_key: str,
        normalized_title_value: str,
        published_at: datetime,
    ) -> sqlite3.Row | None:
        lower = self._iso(published_at - timedelta(hours=48))
        upper = self._iso(published_at + timedelta(hours=48))
        rows = connection.execute(
            """
            SELECT * FROM canonical_event
            WHERE issuer_key=? AND published_at BETWEEN ? AND ?
            """,
            (issuer_key, lower, upper),
        ).fetchall()
        matches = [
            (fuzz.token_set_ratio(normalized_title_value, str(row["normalized_title"])), row)
            for row in rows
        ]
        matches = [match for match in matches if match[0] >= 92]
        return max(matches, key=lambda match: match[0])[1] if matches else None

    @staticmethod
    def _is_correction(current: str, previous: str) -> bool:
        if CORRECTION_PATTERN.search(current):
            return True
        current_numbers = NUMBER_PATTERN.findall(current)
        previous_numbers = NUMBER_PATTERN.findall(previous)
        if current_numbers == previous_numbers:
            return False
        current_without_numbers = NUMBER_PATTERN.sub("", current)
        previous_without_numbers = NUMBER_PATTERN.sub("", previous)
        return fuzz.token_set_ratio(current_without_numbers, previous_without_numbers) >= 92

    @staticmethod
    def _rank_primary_source(connection: sqlite3.Connection, event_id: int) -> None:
        connection.execute("UPDATE event_source SET is_primary=0 WHERE event_id=?", (event_id,))
        row = connection.execute(
            """
            SELECT observation_id FROM event_source
            WHERE event_id=? ORDER BY source_rank DESC, observation_id ASC LIMIT 1
            """,
            (event_id,),
        ).fetchone()
        if row is not None:
            connection.execute(
                "UPDATE event_source SET is_primary=1 WHERE event_id=? AND observation_id=?",
                (event_id, int(row["observation_id"])),
            )

    def _backfill_claim_sources(self, connection: sqlite3.Connection) -> None:
        events = connection.execute("SELECT id FROM canonical_event ORDER BY id ASC").fetchall()
        for event in events:
            event_id = int(event["id"])
            claim_id = self._ensure_claim(connection, event_id)
            observations = connection.execute(
                "SELECT observation_id FROM event_source WHERE event_id=? ORDER BY observation_id",
                (event_id,),
            ).fetchall()
            for observation in observations:
                self._link_claim_source(connection, claim_id, int(observation["observation_id"]))

    def _ensure_claim(self, connection: sqlite3.Connection, event_id: int) -> str:
        existing = connection.execute(
            "SELECT claim_id FROM event_claim WHERE event_id=?", (event_id,)
        ).fetchone()
        if existing is not None:
            return str(existing["claim_id"])
        event = connection.execute(
            "SELECT issuer_key, exact_fingerprint, created_at FROM canonical_event WHERE id=?",
            (event_id,),
        ).fetchone()
        if event is None:
            raise ValueError("Cannot create a claim for a missing canonical event")
        claim_id = f"clm_{self._hash(str(event['issuer_key']), str(event['exact_fingerprint']))}"
        connection.execute(
            "INSERT INTO event_claim(event_id, claim_id, created_at) VALUES (?, ?, ?)",
            (event_id, claim_id, str(event["created_at"])),
        )
        return claim_id

    def _link_claim_source(
        self, connection: sqlite3.Connection, claim_id: str, observation_id: int
    ) -> None:
        observation = connection.execute(
            "SELECT observation_fingerprint FROM source_observation WHERE id=?",
            (observation_id,),
        ).fetchone()
        if observation is None:
            raise ValueError("Cannot link a missing source observation")
        source_reference_id = f"src_{self._hash(str(observation['observation_fingerprint']))}"
        connection.execute(
            """
            INSERT OR IGNORE INTO claim_source(
                claim_id, observation_id, source_reference_id
            ) VALUES (?, ?, ?)
            """,
            (claim_id, observation_id, source_reference_id),
        )

    def _stored_event(
        self,
        connection: sqlite3.Connection,
        event_id: int,
        *,
        source_id: str | None = None,
        title_predicate: Callable[[str, datetime], bool] | None = None,
    ) -> StoredEvent | None:
        event = connection.execute(
            "SELECT * FROM canonical_event WHERE id=?", (event_id,)
        ).fetchone()
        if source_id is None:
            source = connection.execute(
                """
                SELECT observation.* FROM event_source
                JOIN source_observation AS observation
                    ON observation.id=event_source.observation_id
                WHERE event_source.event_id=? AND event_source.is_primary=1
                """,
                (event_id,),
            ).fetchone()
        else:
            source_rows = connection.execute(
                """
                SELECT observation.* FROM event_source
                JOIN source_observation AS observation
                    ON observation.id=event_source.observation_id
                WHERE event_source.event_id=? AND observation.source_id=?
                ORDER BY observation.id ASC
                """,
                (event_id, source_id),
            ).fetchall()
            source = next(
                (
                    row
                    for row in source_rows
                    if title_predicate is None
                    or title_predicate(
                        str(row["title"]), self._datetime(row["published_at"])
                    )
                ),
                None,
            )
        related_rows = connection.execute(
            """
            SELECT observation.* FROM event_source
            JOIN source_observation AS observation ON observation.id=event_source.observation_id
            WHERE event_source.event_id=?
            ORDER BY event_source.source_rank DESC, observation.id ASC
            """,
            (event_id,),
        ).fetchall()
        claim = connection.execute(
            "SELECT claim_id FROM event_claim WHERE event_id=?", (event_id,)
        ).fetchone()
        if event is None or source is None:
            if source_id is not None and title_predicate is not None:
                return None
            raise ValueError("Canonical event graph is incomplete")
        if claim is None:
            raise ValueError("Canonical event claim is incomplete")
        related = [
            row
            for row in related_rows
            if int(row["id"]) != int(source["id"])
            and not (
                source_id is not None
                and str(row["source_id"]) == source_id
                and title_predicate is not None
                and not title_predicate(
                    str(row["title"]), self._datetime(row["published_at"])
                )
            )
        ][:20]
        claim_id = str(claim["claim_id"])
        source_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM claim_source WHERE claim_id=?", (claim_id,)
            ).fetchone()[0]
        )
        supporting_rows = connection.execute(
            """
            SELECT source_reference_id FROM claim_source
            WHERE claim_id=? ORDER BY id ASC LIMIT 20
            """,
            (claim_id,),
        ).fetchall()
        tier_rows = connection.execute(
            """
            SELECT DISTINCT observation.source_tier FROM claim_source AS relation
            JOIN source_observation AS observation
                ON observation.id=relation.observation_id
            WHERE relation.claim_id=? ORDER BY observation.source_tier ASC
            """,
            (claim_id,),
        ).fetchall()
        primary = StoredSource(
            source_id=str(source["source_id"]),
            source_name=str(source["source_name"]),
            source_tier=str(source["source_tier"]),
            record_id=str(source["record_id"]),
            canonical_url=str(source["canonical_url"]),
            published_at=self._datetime(source["published_at"]),
            observed_at=self._datetime(source["observed_at"]),
            retrieved_at=self._datetime(source["retrieved_at"]),
            raw_sha256=str(source["raw_sha256"]) if source["raw_sha256"] else None,
            parser_version=str(source["parser_version"]),
            policy_decision=PolicyDecision(str(source["policy_decision"])),
        )
        return StoredEvent(
            event_id=int(event["id"]),
            issuer_key=str(event["issuer_key"]),
            title=str(source["title"]),
            normalized_title=str(event["normalized_title"]),
            published_at=self._datetime(event["published_at"]),
            version=int(event["version"]),
            correction_of_event_id=(
                int(event["correction_of_event_id"])
                if event["correction_of_event_id"] is not None
                else None
            ),
            primary_source=primary,
            related_urls=tuple(str(row["canonical_url"]) for row in related),
            source_count=source_count,
            source_tiers=tuple(str(row["source_tier"]) for row in tier_rows),
            claim_id=claim_id,
            supporting_source_ids=tuple(
                str(row["source_reference_id"]) for row in supporting_rows
            ),
        )

    @staticmethod
    def _hash(*parts: str) -> str:
        return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _datetime(value: object) -> datetime:
        parsed = datetime.fromisoformat(str(value))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    def export_event_graph(self) -> str:
        """Return bounded structural diagnostics without retained publisher bodies."""
        with self._lock:
            connection = self._connect()
            counts = {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in (
                    "source_observation",
                    "canonical_event",
                    "event_source",
                    "event_claim",
                    "claim_source",
                    "entity_match_audit",
                )
            }
            return json.dumps(counts, sort_keys=True)
