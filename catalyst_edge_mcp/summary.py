"""Deterministic, mode-aware dossier synthesis."""

from __future__ import annotations

import re

from catalyst_edge_mcp.models import Direction, Evidence, RiskMode, Summary

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
    "insider_purchase_strong_cluster": "Three or more insiders reported open-market acquisitions.",
    "insider_sale_cluster": "Multiple insiders reported open-market dispositions.",
    "insider_sale_strong_cluster": "Three or more insiders reported open-market dispositions.",
    "insider_proposed_sale_intent": "A Form 144 reported proposed sale intent, not execution.",
    "social_sentiment_increase": "Sentiment strengthened while attention held or increased.",
    "social_sentiment_decrease": "Sentiment weakened while attention held or increased.",
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
    opposing = [
        item for item in ranked if item.direction not in {Direction.NEUTRAL, leading.direction}
    ]

    if risk_mode == RiskMode.ALERT_TRIAGE:
        headline = (
            f"Newest material change: {describe(newest)} Observed {newest.timestamp.isoformat()}."
        )
        why = "The change may warrant a prompt check against its closest primary source."
    elif risk_mode == RiskMode.THESIS_REVIEW:
        headline = f"Potential thesis-changing evidence: {describe(leading)}"
        why = (
            "Treat the evidence as thesis-relevant only when provenance holds and opposing "
            "observations do not explain the change."
        )
    else:
        headline = (
            f"{FAMILY_LABELS.get(leading.family, 'Evidence')} has the largest recent "
            f"{leading.direction.value} contribution."
        )
        why = (
            "Source independence and agreement can strengthen confidence; missing families and "
            "lower-quality observations constrain it."
        )

    changes = [describe(item) for item in ranked[:4]]
    if opposing:
        changes.append(f"Contradicting evidence: {describe(opposing[0])}")
    elif missing:
        changes.append(f"Missing confirmation: {', '.join(sorted(missing))}.")

    present = {item.family for item in evidence}
    invalidation: list[str] = []
    checks = {
        "filings_news": "A primary filing or company record contradicts the normalized event.",
        "insider_trading": "The reported insider cluster reverses in a subsequent equal window.",
        "options_flow": "Options activity normalizes during the requested horizon.",
        "technical": "The observed technical transition reverses on daily data.",
        "social": "Attention or sentiment normalizes during the next comparison window.",
    }
    invalidation.extend(checks[family] for family in checks if family in present)
    if missing:
        invalidation.append(f"Obtain missing confirmation from {', '.join(sorted(missing))}.")
    invalidation.append("A sector-wide event fully explains the ticker-specific observations.")
    return Summary(
        headline=safe_text(headline),
        what_changed=[safe_text(value) for value in changes[:5]],
        why_it_matters=safe_text(why),
        what_would_invalidate=[safe_text(value) for value in invalidation[:5]],
    )


def next_checks(risk_mode: RiskMode) -> list[str]:
    checks = [
        "Verify the closest primary filing or company announcement.",
        "Check whether a sector-wide event explains the observation.",
        "Review timestamps, source independence, and comparison baselines.",
    ]
    if risk_mode == RiskMode.THESIS_REVIEW:
        checks.append("Compare the evidence with the prior thesis invalidation criteria.")
    elif risk_mode == RiskMode.ALERT_TRIAGE:
        checks.append("Confirm the newest event timestamp before escalating the alert.")
    return checks[:5]
