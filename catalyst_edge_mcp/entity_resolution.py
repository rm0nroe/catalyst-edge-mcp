"""Versioned, fail-closed entity decisions for GDELT discovery candidates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from catalyst_edge_mcp.registry_models import DiscoveryAliasRule, DiscoveryIssuer

ENTITY_RULESET_PREFIX = "entity-rules-v2"
ENTITY_DECISION_VERSION = "title-alignment-v1"


@dataclass(frozen=True, slots=True)
class EntityRuleMatch:
    rule: DiscoveryAliasRule
    context_sha256: str
    required_context_matches: tuple[str, ...]
    negative_context_matches: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntityDecision:
    accepted: bool
    reason_code: str
    ruleset_version: str
    selected_rule_id: str | None
    selected_rule_version: str | None
    candidate_rule_ids: tuple[str, ...]
    matched_aliases: tuple[str, ...]
    matched_context_sha256: str
    required_context_matches: tuple[str, ...]
    negative_context_matches: tuple[str, ...]


def ruleset_version(issuer: DiscoveryIssuer) -> str:
    payload = {
        "decision_version": ENTITY_DECISION_VERSION,
        "rules": [asdict(rule) for rule in issuer.effective_entity_rules],
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"{ENTITY_RULESET_PREFIX}:{digest}"


def match_entity_rules(text: str, issuer: DiscoveryIssuer) -> tuple[EntityRuleMatch, ...]:
    normalized = normalize_entity_text(text)
    if not normalized:
        return ()
    context_sha256 = hashlib.sha256(normalized.encode()).hexdigest()
    matches: list[EntityRuleMatch] = []
    for rule in issuer.effective_entity_rules:
        alias = normalize_entity_text(rule.alias)
        if not alias or not _contains_phrase(normalized, alias):
            continue
        required = tuple(
            term
            for term in rule.required_context
            if _contains_phrase(normalized, normalize_entity_text(term))
        )
        negative = tuple(
            term
            for term in rule.negative_context
            if _contains_phrase(normalized, normalize_entity_text(term))
        )
        matches.append(
            EntityRuleMatch(
                rule=rule,
                context_sha256=context_sha256,
                required_context_matches=required,
                negative_context_matches=negative,
            )
        )
    return tuple(matches)


def decide_entity_candidate(
    issuer: DiscoveryIssuer,
    matches: tuple[EntityRuleMatch, ...],
    published_at: datetime,
    *,
    title: str,
) -> EntityDecision:
    if not matches:
        raise ValueError("Entity decision requires at least one matched alias rule")
    evaluations = tuple((_rule_status(match, published_at), match) for match in matches)
    accepted_matches = tuple(match for status, match in evaluations if status == "accepted")
    selected = (
        min(
            accepted_matches,
            key=lambda match: (-len(normalize_entity_text(match.rule.alias)), match.rule.rule_id),
        )
        if accepted_matches
        else None
    )
    statuses = {status for status, _match in evaluations}
    if selected is not None and not title_matches_issuer(
        title, issuer, published_at=published_at
    ):
        selected = None
        reason_code = "title_not_aligned"
    elif selected is not None:
        reason_code = "accepted"
    elif "negative_context" in statuses:
        reason_code = "negative_context"
    else:
        most_specific = min(
            matches,
            key=lambda match: (-len(normalize_entity_text(match.rule.alias)), match.rule.rule_id),
        )
        reason_code = _rule_status(most_specific, published_at)
    context_hashes = sorted({match.context_sha256 for match in matches})
    combined_context_hash = hashlib.sha256("\x1f".join(context_hashes).encode()).hexdigest()
    return EntityDecision(
        accepted=selected is not None,
        reason_code=reason_code,
        ruleset_version=ruleset_version(issuer),
        selected_rule_id=selected.rule.rule_id if selected else None,
        selected_rule_version=selected.rule.version if selected else None,
        candidate_rule_ids=tuple(sorted({match.rule.rule_id for match in matches})),
        matched_aliases=tuple(sorted({match.rule.alias for match in matches}, key=str.casefold)),
        matched_context_sha256=combined_context_hash,
        required_context_matches=tuple(
            sorted(
                {
                    term
                    for match in matches
                    for term in match.required_context_matches
                },
                key=str.casefold,
            )
        ),
        negative_context_matches=tuple(
            sorted(
                {
                    term
                    for match in matches
                    for term in match.negative_context_matches
                },
                key=str.casefold,
            )
        ),
    )


def title_matches_issuer(
    title: str,
    issuer: DiscoveryIssuer,
    *,
    published_at: datetime | None = None,
) -> bool:
    """Require the surfaced publisher title to name the reviewed issuer."""
    normalized_title = normalize_entity_text(title)
    if not normalized_title:
        return False
    ticker_aliases = {
        normalized
        for ticker in issuer.tickers
        if len(normalized := normalize_entity_text(ticker)) >= 2
    }
    if any(_contains_phrase(normalized_title, ticker) for ticker in ticker_aliases):
        return True
    day = published_at.date().isoformat() if published_at is not None else None
    for rule in issuer.effective_entity_rules:
        alias = normalize_entity_text(rule.alias)
        if not alias or not _contains_phrase(normalized_title, alias):
            continue
        if day is not None and (
            (rule.valid_from and day < rule.valid_from)
            or (rule.valid_to and day > rule.valid_to)
        ):
            continue
        if any(
            _contains_phrase(normalized_title, normalize_entity_text(term))
            for term in rule.negative_context
        ):
            continue
        return True
    return False


def normalize_entity_text(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(phrase) and f" {phrase} " in f" {text} "


def _rule_status(match: EntityRuleMatch, published_at: datetime) -> str:
    day = published_at.date().isoformat()
    rule = match.rule
    if rule.valid_from and day < rule.valid_from:
        return "outside_validity"
    if rule.valid_to and day > rule.valid_to:
        return "outside_validity"
    if match.negative_context_matches:
        return "negative_context"
    if rule.required_context and not match.required_context_matches:
        return "missing_required_context"
    return "accepted"
