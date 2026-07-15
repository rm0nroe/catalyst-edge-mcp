"""Fail-closed source rights, quality, rate, and host policy."""

from __future__ import annotations

from dataclasses import dataclass

from catalyst_edge_mcp.models import PolicyDecision


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    source_id: str
    families: frozenset[str]
    tier: str
    decision: PolicyDecision
    retention: str
    quality_min: float | None
    quality_max: float | None
    requests_per_second: float | None = None
    concurrency: int = 1
    official_hosts: tuple[str, ...] = ()
    reviewed_on: str = "2026-07-13"

    @property
    def production_allowed(self) -> bool:
        return self.decision in {
            PolicyDecision.APPROVED,
            PolicyDecision.APPROVED_PER_REGISTRY,
            PolicyDecision.APPROVED_DISCOVERY,
            PolicyDecision.APPROVED_PARTIAL_ATTENTION,
        }


SOURCE_POLICIES: dict[str, SourcePolicy] = {
    "sec": SourcePolicy(
        "sec",
        frozenset({"filings_news", "insider_trading"}),
        "primary_regulator",
        PolicyDecision.APPROVED,
        "parsed facts, identifiers, hashes, and links",
        1.0,
        1.0,
        requests_per_second=2.0,
        concurrency=2,
        official_hosts=("www.sec.gov", "data.sec.gov"),
    ),
    "issuer_feed": SourcePolicy(
        "issuer_feed",
        frozenset({"filings_news"}),
        "issuer_primary",
        PolicyDecision.APPROVED_PER_REGISTRY,
        "metadata and factual extraction unless reviewed terms allow more",
        0.95,
        0.95,
    ),
    "gdelt": SourcePolicy(
        "gdelt",
        frozenset({"filings_news"}),
        "discovery",
        PolicyDecision.APPROVED_DISCOVERY,
        "publisher metadata and links only",
        0.60,
        0.70,
        official_hosts=("api.gdeltproject.org", "storage.googleapis.com"),
        reviewed_on="2026-07-14",
    ),
    "bluesky": SourcePolicy(
        "bluesky",
        frozenset({"social"}),
        "partial_attention",
        PolicyDecision.APPROVED_PARTIAL_ATTENTION,
        "minimal post metadata, derived windows, and representative links",
        0.50,
        0.60,
        official_hosts=("public.api.bsky.app", "api.bsky.app"),
    ),
    "mastodon": SourcePolicy(
        "mastodon",
        frozenset({"social"}),
        "instance_attention",
        PolicyDecision.APPROVED_PER_REGISTRY,
        "reviewed-instance metadata and derived buckets",
        0.40,
        0.50,
    ),
    "fmp": SourcePolicy(
        "fmp",
        frozenset({"filings_news", "insider_trading", "technical"}),
        "conditional_vendor",
        PolicyDecision.PERMISSION_REQUIRED,
        "disabled until written commercial rights are recorded",
        None,
        0.90,
    ),
    "finnhub": SourcePolicy(
        "finnhub",
        frozenset({"filings_news", "social", "alternative"}),
        "conditional_vendor",
        PolicyDecision.PERMISSION_REQUIRED,
        "disabled until written commercial rights are recorded",
        None,
        0.90,
    ),
    "occ": SourcePolicy(
        "occ",
        frozenset({"options_eod_activity"}),
        "conditional_aggregate",
        PolicyDecision.PERMISSION_REQUIRED,
        "no commercial automation without written permission",
        None,
        None,
    ),
    "opra_vendor": SourcePolicy(
        "opra_vendor",
        frozenset({"options_flow"}),
        "licensed_market_data",
        PolicyDecision.LICENSED_FEED_REQUIRED,
        "requires approved non-display, storage, and output rights",
        None,
        0.90,
    ),
    "flowalgo": SourcePolicy(
        "flowalgo",
        frozenset({"options_flow"}),
        "conditional_options_vendor",
        PolicyDecision.LICENSED_FEED_REQUIRED,
        "requires approved transaction-plus-quote and output rights",
        None,
        0.90,
    ),
    "cheddarflow": SourcePolicy(
        "cheddarflow",
        frozenset({"options_flow"}),
        "conditional_options_vendor",
        PolicyDecision.LICENSED_FEED_REQUIRED,
        "requires approved transaction-plus-quote and output rights",
        None,
        0.90,
    ),
    "user_ohlc": SourcePolicy(
        "user_ohlc",
        frozenset({"technical"}),
        "licensed_market_data",
        PolicyDecision.LICENSED_FEED_REQUIRED,
        "requires user-supplied commercial rights",
        None,
        0.90,
    ),
    "yfinance": SourcePolicy(
        "yfinance",
        frozenset({"options_eod_activity", "technical"}),
        "private_diagnostic",
        PolicyDecision.DEVELOPMENT_PRIVATE_ONLY,
        "never production evidence, coverage, or readiness",
        None,
        None,
    ),
}


def get_source_policy(source_id: str) -> SourcePolicy:
    """Return a reviewed policy; unknown sources fail closed."""
    try:
        return SOURCE_POLICIES[source_id]
    except KeyError as exc:
        raise ValueError(f"source policy is not reviewed: {source_id}") from exc
