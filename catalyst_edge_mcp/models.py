"""Validated input, evidence, provenance, and response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, HttpUrl, computed_field

from catalyst_edge_mcp.validation import normalize_ticker

Ticker = Annotated[
    str,
    BeforeValidator(normalize_ticker),
    Field(pattern=r"^[A-Z][A-Z0-9.-]{0,11}$", min_length=1, max_length=12),
]


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class RiskMode(str, Enum):
    RESEARCH = "research"
    ALERT_TRIAGE = "alert_triage"
    THESIS_REVIEW = "thesis_review"


class SourceStatus(str, Enum):
    FRESH = "fresh"
    NO_OBSERVATIONS = "no_observations"
    STALE = "stale"
    RATE_LIMITED = "rate_limited"
    PERMISSION_REQUIRED = "permission_required"
    LICENSED_FEED_REQUIRED = "licensed_feed_required"
    TIMEOUT = "timeout"
    SCHEMA_ERROR = "schema_error"
    UNAVAILABLE = "unavailable"


class PolicyDecision(str, Enum):
    APPROVED = "approved"
    APPROVED_PER_REGISTRY = "approved_per_registry"
    APPROVED_DISCOVERY = "approved_discovery"
    APPROVED_PARTIAL_ATTENTION = "approved_partial_attention"
    PERMISSION_REQUIRED = "permission_required"
    LICENSED_FEED_REQUIRED = "licensed_feed_required"
    DEVELOPMENT_PRIVATE_ONLY = "development_private_only"


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: Ticker
    lookback_days: int = Field(default=14, ge=1, le=90, strict=True)
    include_sources: bool = Field(default=True, strict=True)
    include_raw_signals: bool = Field(default=False, strict=True)
    risk_mode: RiskMode = RiskMode.RESEARCH


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    source_id: str | None = Field(default=None, min_length=1, max_length=80)
    source_tier: str | None = Field(default=None, min_length=1, max_length=40)
    url: HttpUrl | None = None
    canonical_url: HttpUrl | None = None
    accession_or_record_id: str | None = Field(default=None, max_length=160)
    published_at: datetime | None = None
    observed_at: datetime
    retrieved_at: datetime | None = None
    raw_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    parser_version: str | None = Field(default=None, max_length=80)
    policy_decision: PolicyDecision | None = None
    model_or_lexicon_revision: str | None = Field(default=None, max_length=120)
    related_sources: list[HttpUrl] = Field(default_factory=list, max_length=20)


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    description: str = Field(min_length=1, max_length=240)
    current_value: float | None = None
    baseline_value: float | None = None
    delta: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    comparison_window: str | None = Field(default=None, max_length=80)


class EvidenceContext(BaseModel):
    """Factual product meaning attached to a normalized observation."""

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1, max_length=80)
    event_label: str = Field(min_length=1, max_length=160)
    novelty: str = Field(min_length=1, max_length=40)
    materiality: str = Field(min_length=1, max_length=40)
    why_it_matters: str = Field(min_length=1, max_length=500)
    source_record_count: int = Field(default=1, ge=0, le=100)
    corroborating_source_count: int = Field(default=0, ge=0, le=100)
    source_tiers: list[str] = Field(default_factory=list, max_length=10)
    correction_of_event_id: int | None = Field(default=None, ge=1)


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str = Field(min_length=1, max_length=64)
    signal: str = Field(min_length=1, max_length=120)
    direction: Direction
    strength: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    timestamp: datetime
    source_quality: float = Field(default=0.5, ge=0, le=1)
    change: Change | None = None
    context: EvidenceContext | None = None
    sources: list[Source] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)
    contribution: float = 0.0
    raw_signal: Any | None = None

    @computed_field
    @property
    def source_count(self) -> int:
        return len(self.sources)


class AdapterResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str
    provider: str = "unknown"
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: SourceStatus | None = None
    policy_decision: PolicyDecision | None = None
    degraded: bool = False
    collected_at: datetime | None = None


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    direction: Direction
    confidence: float = Field(ge=0, le=1)
    horizon_days: int = 5
    scoring_method: str = "deterministic_v1"
    model_status: str = "not_trained"


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str
    what_changed: list[str]
    why_it_matters: str
    what_would_invalidate: list[str]


class FamilyStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str = Field(min_length=1, max_length=64)
    available: bool
    status: SourceStatus
    reason: str = Field(min_length=1, max_length=160)
    observed_at: datetime | None = None
    coverage_ratio: float = Field(default=0.0, ge=0, le=1)


class DataQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage: str
    missing_families: list[str]
    stale_families: list[str]
    warnings: list[str]
    family_statuses: list[FamilyStatus] = Field(default_factory=list)


class CatalystEdgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str
    as_of: datetime
    lookback_days: int
    edge: Edge
    summary: Summary
    evidence: list[Evidence]
    data_quality: DataQuality
    next_checks: list[str]
