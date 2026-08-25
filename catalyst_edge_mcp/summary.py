"""Deterministic, evidence-specific dossier synthesis."""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urlsplit

from catalyst_edge_mcp.models import Direction, Evidence, RiskMode, ScopedReason, Source, Summary

FAMILY_LABELS = {
    "filings_news": "Filings and news",
    "insider_trading": "Insider activity",
    "options_flow": "Options activity",
    "technical": "Technical transitions",
    "social": "Social attention",
    "alternative": "Alternative evidence",
}
SIGNAL_LABELS = {
    "sec_form_8_k": "A new SEC Form 8-K was observed.",
    "sec_form_8_k_a": "An amended SEC Form 8-K was observed.",
    "insider_purchase_cluster": "Multiple insiders reported open-market acquisitions.",
    "insider_purchase_strong_cluster": (
        "Three or more insiders reported open-market acquisitions."
    ),
    "insider_sale_cluster": "Multiple insiders reported open-market dispositions.",
    "insider_sale_strong_cluster": ("Three or more insiders reported open-market dispositions."),
    "insider_proposed_sale_intent": ("A Form 144 reported proposed sale intent, not execution."),
    "social_sentiment_increase": ("Sentiment strengthened while attention held or increased."),
    "social_sentiment_decrease": ("Sentiment weakened while attention held or increased."),
    "call_activity_increase": "Call-side options activity increased versus its baseline.",
    "put_activity_increase": "Put-side options activity increased versus its baseline.",
}
PROHIBITED = re.compile(
    r"\b(buy|sell|guaranteed|alpha|expected[ -]return|should purchase)\b", re.IGNORECASE
)


def safe_text(value: str) -> str:
    return PROHIBITED.sub("restricted term", value)[:500]


def describe(item: Evidence) -> str:
    if item.change is not None:
        return safe_text(item.change.description)
    return SIGNAL_LABELS.get(
        item.signal,
        f"{FAMILY_LABELS.get(item.family, 'Evidence')} changed during the requested window.",
    )


def _label(item: Evidence) -> str:
    return (
        item.context.event_label
        if item.context is not None
        else FAMILY_LABELS.get(item.family, "Catalyst evidence")
    )


def _directional_leader(ranked: list[Evidence]) -> Evidence | None:
    return next((item for item in ranked if item.direction != Direction.NEUTRAL), None)


def _opposing(ranked: list[Evidence], leader: Evidence | None) -> list[Evidence]:
    if leader is None:
        return []
    return [item for item in ranked if item.direction not in {Direction.NEUTRAL, leader.direction}]


def _support_statement(item: Evidence) -> str | None:
    context = item.context
    if context is None:
        return None
    if context.corroborating_source_count:
        return (
            f"The canonical event has {context.corroborating_source_count} additional "
            f"source record{'s' if context.corroborating_source_count != 1 else ''}."
        )
    if context.source_record_count > 1:
        return f"The observation is supported by {context.source_record_count} source records."
    return None


def _why_it_matters(
    leading: Evidence,
    opposing: list[Evidence],
    missing: set[str],
) -> str:
    parts = [
        leading.context.why_it_matters
        if leading.context is not None
        else "The leading observation is the strongest normalized change in the current window."
    ]
    support = _support_statement(leading)
    if support:
        parts.append(support)
    if opposing:
        parts.append(
            f"Conflicting {opposing[0].direction.value} evidence is also present: "
            f"{describe(opposing[0])}"
        )
    if missing:
        parts.append(
            "Confidence remains constrained by missing " + ", ".join(sorted(missing)) + "."
        )
    return safe_text(" ".join(parts))


def _invalidation(item: Evidence) -> str:
    context = item.context
    event_type = context.event_type if context is not None else ""
    if context is not None and context.novelty == "correction":
        return "A later canonical version supersedes or reverses the reported correction."
    if event_type.startswith("open_market_"):
        return (
            "A later Form 4 amendment changes the transaction code, shares, price, "
            "ownership form, or 10b5-1 context."
        )
    if event_type == "proposed_insider_sale":
        return (
            "A later filing changes the proposed terms, or no completed disposition is "
            "subsequently reported."
        )
    if item.family == "filings_news" and item.sources:
        return "A later SEC amendment or issuer-primary disclosure changes the filed facts."
    checks = {
        "options_flow": "Options activity normalizes during the requested horizon.",
        "technical": "The observed technical transition reverses on daily data.",
        "social": "Attention or sentiment normalizes during the next comparison window.",
    }
    return checks.get(
        item.family,
        "A later primary-source record changes the normalized facts.",
    )


def build_summary(evidence: list[Evidence], missing: set[str], risk_mode: RiskMode) -> Summary:
    if not evidence:
        return Summary(
            headline="No recent catalyst evidence was available from configured sources.",
            what_changed=["No fresh normalized evidence was collected."],
            why_it_matters="Missing observations prevent a directional assessment.",
            what_would_invalidate=["Fresh primary-source evidence becomes available."],
        )

    ranked = sorted(
        evidence, key=lambda item: (-abs(item.contribution), -item.timestamp.timestamp())
    )
    leading = ranked[0]
    newest = max(evidence, key=lambda item: item.timestamp)
    directional_leader = _directional_leader(ranked)
    opposing = _opposing(ranked, directional_leader)

    if risk_mode == RiskMode.ALERT_TRIAGE:
        headline = f"{_label(newest)}: {describe(newest)} Observed {newest.timestamp.isoformat()}."
    elif risk_mode == RiskMode.THESIS_REVIEW:
        headline = f"Thesis-review evidence — {_label(leading)}: {describe(leading)}"
    else:
        headline = f"{_label(leading)}: {describe(leading)}"

    changes: list[str] = []
    for item in ranked:
        description = describe(item)
        if description not in changes:
            changes.append(description)
        support = _support_statement(item)
        if support and support not in changes:
            changes.append(support)
        if len(changes) >= 4:
            break
    if opposing:
        changes.append(f"Conflicting evidence: {describe(opposing[0])}")
    elif missing:
        changes.append(f"Missing confirmation: {', '.join(sorted(missing))}.")

    invalidation = [_invalidation(leading)]
    if opposing:
        invalidation.append(
            f"The conflicting {opposing[0].direction.value} observation becomes the "
            "better-supported primary-source account."
        )
    if missing:
        invalidation.append(f"Obtain missing confirmation from {', '.join(sorted(missing))}.")
    if any(item.family != "filings_news" for item in evidence):
        invalidation.append("A sector-wide event fully explains the ticker-specific observations.")

    return Summary(
        headline=safe_text(headline),
        what_changed=[safe_text(value) for value in changes[:5]],
        why_it_matters=_why_it_matters(leading, opposing, missing),
        what_would_invalidate=[safe_text(value) for value in invalidation[:5]],
    )


def _is_sec_source(source: Source) -> bool:
    url = source.canonical_url or source.url
    host = (urlsplit(str(url)).hostname or "").lower() if url else ""
    return source.source_id in {"sec", "sec_funds"} and (
        host == "sec.gov" or host.endswith(".sec.gov")
    )


def evidence_check(item: Evidence) -> str | None:
    source = item.sources[0] if item.sources else None
    accession = source.accession_or_record_id if source is not None else None
    context = item.context
    if item.family == "filings_news" and accession and source and _is_sec_source(source):
        return f"Open SEC accession {accession} and review the filed item text and exhibits."
    if source is not None and (
        source.source_id == "gdelt"
        or source.source_tier == "discovery"
        or (context is not None and context.materiality == "discovery_only")
    ):
        return (
            "Open the publisher source and verify the underlying event against an issuer or "
            "regulator primary source."
        )
    if context is not None and context.event_type.startswith("open_market_"):
        return (
            "Verify each Form 4 transaction code, shares, price, ownership form, and "
            "10b5-1 footnotes."
        )
    if context is not None and context.event_type == "proposed_insider_sale":
        return "Track later Form 4 filings; the Form 144 records proposed intent, not execution."
    if context is not None and context.novelty == "correction":
        return "Compare the correction with the prior canonical event version."
    return None


def _typed_recovery_checks(reason_records: Sequence[ScopedReason]) -> list[str]:
    details = {reason.detail for reason in reason_records if reason.detail}
    if "unsupported_no_series_class" in details:
        return [
            "Use the sponsor-primary fund source; SEC N-CEN/NPORT collection is unsupported "
            "without a verified series/class identity.",
            "Confirm the fund's current series/class identity against official SEC records.",
        ]
    if "unsupported_non_investment_company" in details:
        return [
            "Use the sponsor-primary trust source; this product is outside the SEC "
            "N-CEN/NPORT fund lane.",
            "Verify material trust disclosures on the sponsor-primary notice surface.",
        ]
    if details & {"fund_uses_distinct_sec_lane", "fund_has_no_corporate_insider_semantics"}:
        return [
            "Check recent N-CEN/NPORT filings and sponsor-primary fund notices; corporate "
            "filing and insider checks do not apply.",
            "Confirm the reviewed fund series/class identity before changing its SEC lane.",
        ]
    if "cik_unresolved" in details:
        return [
            "Resolve the ticker's current issuer lifecycle (renamed, acquired, delisted, "
            "bankrupt, or otherwise inactive) before retrying SEC collection.",
            "Search issuer or acquirer SEC filings by legal name or CIK, not the stale ticker.",
        ]
    if "ticker_not_current_for_sec_issuer" in details:
        return [
            "The requested ticker is no longer current for the SEC issuer; review acquisition, "
            "delisting, renaming, or other lifecycle records before widening the lookback.",
            "Search the issuer or acquirer by legal name or CIK for the current filing record.",
        ]
    return []


def next_checks(
    evidence: list[Evidence],
    risk_mode: RiskMode,
    lookback_days: int,
    *,
    reason_records: Sequence[ScopedReason] = (),
) -> list[str]:
    if not evidence:
        checks = _typed_recovery_checks(reason_records)
        if checks:
            return checks
        if lookback_days < 30:
            checks.append("Retry with lookback_days=30 to check a wider filing window.")
        checks.extend(
            [
                (
                    "Open the issuer's recent SEC filings and verify whether qualifying "
                    "evidence exists."
                ),
                "Confirm the monitored SEC identity and configured-source statuses.",
            ]
        )
        return checks

    checks: list[str] = []
    for item in sorted(evidence, key=lambda value: -value.timestamp.timestamp()):
        check = evidence_check(item)
        if check:
            checks.append(check)
        if len(checks) >= 3:
            break

    directions = {item.direction for item in evidence if item.direction != Direction.NEUTRAL}
    if len(directions) > 1:
        checks.append(
            "Resolve conflicting evidence against the highest-tier primary source."
        )
    checks.append("Check whether a sector-wide event explains the observation.")
    if risk_mode == RiskMode.THESIS_REVIEW:
        checks.append("Compare the evidence with the prior thesis invalidation criteria.")
    elif risk_mode == RiskMode.ALERT_TRIAGE:
        checks.append("Confirm the newest event timestamp before escalating the alert.")
    return list(dict.fromkeys(safe_text(check) for check in checks))[:5]
