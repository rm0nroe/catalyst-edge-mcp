"""Bounded, versioned semantic rules for SEC primary documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

RULESET_VERSION = "sec-primary-document-v1"
LOCAL_CONTEXT_CHARS = 240


@dataclass(frozen=True)
class SecDocumentRule:
    rule_id: str
    version: str
    priority: int
    event_type: str
    label: str
    why_it_matters: str
    materiality: str
    patterns: tuple[re.Pattern[str], ...]
    exclusions: tuple[re.Pattern[str], ...] = ()
    generic: bool = False

    def matches(self, text: str) -> bool:
        for pattern in self.patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - LOCAL_CONTEXT_CHARS)
                end = min(len(text), match.end() + LOCAL_CONTEXT_CHARS)
                local_context = text[start:end]
                if not any(exclusion.search(local_context) for exclusion in self.exclusions):
                    return True
        return False


@dataclass(frozen=True)
class SecDocumentDecision:
    ruleset_version: str
    status: str
    selected_rule: SecDocumentRule | None
    candidate_rule_ids: tuple[str, ...]


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


SEC_DOCUMENT_RULES = (
    SecDocumentRule(
        rule_id="equity_distribution_agreement",
        version="1",
        priority=20,
        event_type="equity_distribution",
        label="Equity distribution agreement",
        why_it_matters=(
            "An at-the-market or similar equity distribution program can change "
            "share count, financing capacity, and potential dilution."
        ),
        materiality="material",
        patterns=(
            _compile(
                r"\b(?:entered into|executed|established|amended(?: and restated)?)"
                r".{0,100}\bequity distribution agreement\b"
            ),
        ),
        exclusions=(
            _compile(
                r"\b(?:terminated|cancelled|canceled|did not enter into|has not entered into)"
                r".{0,120}\bequity distribution agreement\b"
            ),
        ),
    ),
    SecDocumentRule(
        rule_id="share_repurchase_activity",
        version="1",
        priority=30,
        event_type="share_repurchase",
        label="Share repurchase activity",
        why_it_matters=(
            "Actual or newly disclosed repurchase activity changes outstanding "
            "capital and the issuer's use of cash."
        ),
        materiality="material",
        patterns=(
            _compile(
                r"\b(?:commenced|began|continued|completed)\w*.{0,80}"
                r"\brepurchas\w*.{0,80}\bshares\b"
            ),
            _compile(r"\brepurchased\b.{0,80}\bshares\b"),
        ),
        exclusions=(
            _compile(
                r"\b(?:did not|does not|has not|have not|had not|will not)"
                r".{0,80}\brepurchas\w*\b"
            ),
            _compile(
                r"\b(?:may|might|could|plans? to|intends? to|authorized to)"
                r".{0,80}\brepurchas\w*\b"
            ),
            _compile(r"\bno shares\b.{0,80}\brepurchas\w*\b"),
        ),
    ),
    SecDocumentRule(
        rule_id="completed_debt_offering",
        version="1",
        priority=10,
        event_type="debt_offering",
        label="Debt offering",
        why_it_matters=(
            "A completed debt offering changes liquidity, leverage, interest "
            "expense, and future repayment obligations."
        ),
        materiality="material",
        patterns=(
            _compile(
                r"\bcompleted\b.{0,100}\boffering\b.{0,220}"
                r"\b(?:senior|subordinated|convertible|secured|unsecured)?\s*notes\b"
            ),
            _compile(
                r"\b(?:issued|sold)\b.{0,220}"
                r"\b(?:senior|subordinated|convertible|secured|unsecured)?\s*notes\b"
            ),
        ),
        exclusions=(
            _compile(
                r"\b(?:did not|has not|have not|had not|will not)"
                r".{0,80}\b(?:issue|issued|sell|sold|complete|completed)\b"
            ),
            _compile(
                r"\b(?:proposes?|expects?|intends?|plans?|may|might|could)\b"
                r".{0,100}\b(?:issue|sell|offer|complete)\b"
            ),
        ),
    ),
    SecDocumentRule(
        rule_id="filed_prospectus_supplement",
        version="1",
        priority=100,
        event_type="securities_offering",
        label="Securities offering update",
        why_it_matters=(
            "A prospectus supplement can establish or update the terms and "
            "capacity for a securities offering."
        ),
        materiality="material",
        patterns=(
            _compile(
                r"\b(?:filed|is filing|has filed)\b.{0,100}\bprospectus supplement\b"
            ),
        ),
        exclusions=(
            _compile(
                r"\b(?:did not|has not|have not|had not|will not)\b"
                r".{0,80}\bfil(?:e|ed|ing)\b.{0,100}\bprospectus supplement\b"
            ),
            _compile(r"\bpreviously filed\b.{0,100}\bprospectus supplement\b"),
        ),
        generic=True,
    ),
)


SEC_DOCUMENT_RULES_BY_ID = {rule.rule_id: rule for rule in SEC_DOCUMENT_RULES}


def classify_sec_primary_document(text: str) -> SecDocumentDecision:
    """Classify only explicitly supported events and fail closed on ambiguity."""
    candidates = tuple(rule for rule in SEC_DOCUMENT_RULES if rule.matches(text))
    candidate_ids = tuple(rule.rule_id for rule in candidates)
    if not candidates:
        return SecDocumentDecision(RULESET_VERSION, "no_match", None, ())

    specific = tuple(rule for rule in candidates if not rule.generic)
    if len(specific) > 1:
        return SecDocumentDecision(RULESET_VERSION, "ambiguous", None, candidate_ids)

    selected = min(specific or candidates, key=lambda rule: rule.priority)
    return SecDocumentDecision(RULESET_VERSION, "matched", selected, candidate_ids)
