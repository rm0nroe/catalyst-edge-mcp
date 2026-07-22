"""Strict loader for reviewed local issuer, discovery, and social registries."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import Any
from urllib.parse import urlsplit

from catalyst_edge_mcp.registry_models import (
    DiscoveryAliasRule,
    DiscoveryIssuer,
    IssuerFeed,
    PublisherDomainQuality,
    SocialIssuer,
)
from catalyst_edge_mcp.validation import normalize_ticker

DEFAULT_REGISTRY_PATH = Path(__file__).with_name("data") / "reviewed_registries.json"
MAX_REGISTRY_BYTES = 256_000
CIK_PATTERN = re.compile(r"^CIK\d{10}$")
HOST_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?$")
RULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
RULE_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
DISCOVERY_ALIAS_KINDS = frozenset(
    {"legal_name", "former_name", "brand", "subsidiary", "product", "ticker"}
)
DISCOVERY_MATCH_MODES = frozenset({"phrase", "ticker_token"})


@dataclass(frozen=True, slots=True)
class RegistryBundle:
    issuer_feeds: tuple[IssuerFeed, ...]
    discovery_issuers: tuple[DiscoveryIssuer, ...]
    social_issuers: tuple[SocialIssuer, ...]
    publisher_domains: tuple[PublisherDomainQuality, ...]
    issuer_feed_index: MappingProxyType
    discovery_index: MappingProxyType
    social_index: MappingProxyType
    publisher_quality_index: MappingProxyType


def load_registry_bundle(path: str | Path = DEFAULT_REGISTRY_PATH) -> RegistryBundle:
    registry_path = Path(path).expanduser()
    try:
        content = registry_path.read_bytes()
    except OSError as exc:
        raise ValueError(f"Unable to read collector registry: {registry_path}") from exc
    if len(content) > MAX_REGISTRY_BYTES:
        raise ValueError("Collector registry exceeds the 256000-byte limit")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Collector registry must be valid UTF-8 JSON") from exc
    root = _object(
        payload,
        "registry",
        required={"version", "issuers"},
        optional={"publisher_domains"},
    )
    version = root["version"]
    if type(version) is not int or version not in {1, 2}:
        raise ValueError("Collector registry version must be 1 or 2")
    issuers = root["issuers"]
    if not isinstance(issuers, list) or not 1 <= len(issuers) <= 200:
        raise ValueError("Collector registry issuers must contain 1 to 200 entries")

    feeds: list[IssuerFeed] = []
    discovery: list[DiscoveryIssuer] = []
    social: list[SocialIssuer] = []
    ticker_owners: dict[str, str] = {}
    discovery_alias_owners: dict[str, str] = {}
    social_alias_owners: dict[str, str] = {}
    issuer_keys: set[str] = set()
    for index, raw_issuer in enumerate(issuers):
        label = f"issuers[{index}]"
        discovery_field = "discovery_aliases" if version == 1 else "discovery_rules"
        item = _object(
            raw_issuer,
            label,
            required={
                "issuer_key",
                "issuer_name",
                "tickers",
                "reviewed_on",
                discovery_field,
                "social_aliases",
                "issuer_feed",
            },
        )
        issuer_key = _text(item["issuer_key"], f"{label}.issuer_key", 13)
        if not CIK_PATTERN.fullmatch(issuer_key):
            raise ValueError(f"{label}.issuer_key must match CIK plus 10 digits")
        if issuer_key in issuer_keys:
            raise ValueError(f"Duplicate issuer_key: {issuer_key}")
        issuer_keys.add(issuer_key)
        issuer_name = _text(item["issuer_name"], f"{label}.issuer_name", 120)
        reviewed_on = _review_date(item["reviewed_on"], f"{label}.reviewed_on")
        tickers = _tickers(item["tickers"], f"{label}.tickers")
        for ticker in tickers:
            owner = ticker_owners.setdefault(ticker, issuer_key)
            if owner != issuer_key:
                raise ValueError(f"Ticker {ticker} is assigned to multiple issuers")

        if version == 1:
            discovery_aliases = _aliases(
                item["discovery_aliases"], f"{label}.discovery_aliases"
            )
            discovery_rules: tuple[DiscoveryAliasRule, ...] = ()
        else:
            discovery_rules = _discovery_rules(
                item["discovery_rules"],
                label=f"{label}.discovery_rules",
                issuer_key=issuer_key,
                tickers=tickers,
            )
            discovery_aliases = tuple(dict.fromkeys(rule.alias for rule in discovery_rules))
        social_aliases = _aliases(item["social_aliases"], f"{label}.social_aliases")
        _claim_aliases(discovery_aliases, issuer_key, discovery_alias_owners, "discovery")
        _claim_aliases(social_aliases, issuer_key, social_alias_owners, "social")
        if discovery_aliases:
            discovery.append(
                DiscoveryIssuer(
                    issuer_key=issuer_key,
                    issuer_name=issuer_name,
                    tickers=tickers,
                    query_aliases=discovery_aliases,
                    reviewed_on=reviewed_on,
                    entity_rules=discovery_rules,
                )
            )
        if social_aliases:
            social.append(
                SocialIssuer(
                    issuer_key=issuer_key,
                    issuer_name=issuer_name,
                    tickers=tickers,
                    exact_aliases=social_aliases,
                    reviewed_on=reviewed_on,
                )
            )
        if item["issuer_feed"] is not None:
            feeds.append(
                _issuer_feed(
                    item["issuer_feed"],
                    label=f"{label}.issuer_feed",
                    issuer_key=issuer_key,
                    issuer_name=issuer_name,
                    tickers=tickers,
                    reviewed_on=reviewed_on,
                )
            )
        if not discovery_aliases and not social_aliases and item["issuer_feed"] is None:
            raise ValueError(f"{label} does not enable any reviewed collector")

    publisher_domains = _publisher_domains(root.get("publisher_domains", []))
    return RegistryBundle(
        issuer_feeds=tuple(feeds),
        discovery_issuers=tuple(discovery),
        social_issuers=tuple(social),
        publisher_domains=publisher_domains,
        issuer_feed_index=MappingProxyType(_index(feeds)),
        discovery_index=MappingProxyType(_index(discovery)),
        social_index=MappingProxyType(_index(social)),
        publisher_quality_index=MappingProxyType(
            {record.domain: record for record in publisher_domains}
        ),
    )


def publisher_quality_for_domain(
    domain: str,
    registry: Mapping[str, PublisherDomainQuality],
) -> PublisherDomainQuality | None:
    normalized = domain.lower().rstrip(".")
    matches = [
        record
        for configured, record in registry.items()
        if normalized == configured or normalized.endswith(f".{configured}")
    ]
    return max(matches, key=lambda record: len(record.domain), default=None)


def _publisher_domains(value: object) -> tuple[PublisherDomainQuality, ...]:
    if not isinstance(value, list) or len(value) > 200:
        raise ValueError("publisher_domains must contain at most 200 entries")
    records: list[PublisherDomainQuality] = []
    seen: set[str] = set()
    allowed_tiers = {"wire_service", "financial_press", "release_distribution"}
    for index, raw in enumerate(value):
        label = f"publisher_domains[{index}]"
        item = _object(
            raw,
            label,
            required={"domain", "tier", "quality", "reviewed_on", "review_note"},
        )
        domain = _text(item["domain"], f"{label}.domain", 253).lower().rstrip(".")
        if not HOST_PATTERN.fullmatch(domain) or ".." in domain:
            raise ValueError(f"{label}.domain must be a valid hostname")
        if domain in seen:
            raise ValueError(f"Duplicate publisher domain: {domain}")
        seen.add(domain)
        tier = _text(item["tier"], f"{label}.tier", 40)
        if tier not in allowed_tiers:
            raise ValueError(f"{label}.tier is not a reviewed publisher tier")
        quality = item["quality"]
        if (
            not isinstance(quality, (int, float))
            or isinstance(quality, bool)
            or not 0.60 <= float(quality) <= 0.70
        ):
            raise ValueError(f"{label}.quality must be between 0.60 and 0.70")
        records.append(
            PublisherDomainQuality(
                domain=domain,
                tier=tier,
                quality=float(quality),
                reviewed_on=_review_date(item["reviewed_on"], f"{label}.reviewed_on"),
                review_note=_text(item["review_note"], f"{label}.review_note", 240),
            )
        )
    return tuple(records)


def _issuer_feed(
    value: object,
    *,
    label: str,
    issuer_key: str,
    issuer_name: str,
    tickers: tuple[str, ...],
    reviewed_on: str,
) -> IssuerFeed:
    item = _object(
        value,
        label,
        required={"feed_url", "official_hosts", "refresh_seconds", "review_note"},
    )
    feed_url = _text(item["feed_url"], f"{label}.feed_url", 500)
    parsed = urlsplit(feed_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{label}.feed_url contains an invalid port") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or port not in {None, 443}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{label}.feed_url must be an absolute credential-free HTTPS URL")
    hosts = _hosts(item["official_hosts"], f"{label}.official_hosts")
    if parsed.hostname.lower().rstrip(".") not in hosts:
        raise ValueError(f"{label}.feed_url host must be listed in official_hosts")
    refresh_seconds = item["refresh_seconds"]
    if not isinstance(refresh_seconds, int) or isinstance(refresh_seconds, bool):
        raise ValueError(f"{label}.refresh_seconds must be an integer")
    if not 60 <= refresh_seconds <= 86400:
        raise ValueError(f"{label}.refresh_seconds must be between 60 and 86400")
    return IssuerFeed(
        issuer_key=issuer_key,
        issuer_name=issuer_name,
        tickers=tickers,
        feed_url=feed_url,
        official_hosts=hosts,
        refresh_seconds=refresh_seconds,
        reviewed_on=reviewed_on,
        review_note=_text(item["review_note"], f"{label}.review_note", 240),
    )


def _object(
    value: object,
    label: str,
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    keys = set(value)
    missing = required - keys
    unknown = keys - required - (optional or set())
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
    return value


def _text(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{label} contains unsupported control characters")
    if any(character in value for character in {'"', "\\"}):
        raise ValueError(f"{label} contains unsupported characters")
    normalized = " ".join(value.split())
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters")
    return normalized


def _review_date(value: object, label: str) -> str:
    text = _text(value, label, 10)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD") from exc
    return text


def _tickers(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 10:
        raise ValueError(f"{label} must contain 1 to 10 tickers")
    tickers: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{label} entries must be strings")
        normalized = normalize_ticker(item)
        if item != normalized or "." in item:
            raise ValueError(f"{label} entries must be canonical uppercase dash tickers")
        if normalized in tickers:
            raise ValueError(f"{label} contains duplicate ticker {normalized}")
        tickers.append(normalized)
    return tuple(tickers)


def _aliases(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError(f"{label} must contain at most 20 aliases")
    aliases: list[str] = []
    seen: set[str] = set()
    for item in value:
        alias = _text(item, label, 80)
        if len(alias) < 3 or not any(character.isalpha() for character in alias):
            raise ValueError(f"{label} aliases must contain at least three characters and a letter")
        folded = alias.casefold()
        if folded in seen:
            raise ValueError(f"{label} contains a duplicate case-insensitive alias")
        seen.add(folded)
        aliases.append(alias)
    return tuple(aliases)


def _discovery_rules(
    value: object,
    *,
    label: str,
    issuer_key: str,
    tickers: tuple[str, ...],
) -> tuple[DiscoveryAliasRule, ...]:
    if not isinstance(value, list) or len(value) > 40:
        raise ValueError(f"{label} must contain at most 40 rules")
    rules: list[DiscoveryAliasRule] = []
    rule_ids: set[str] = set()
    for index, raw_rule in enumerate(value):
        rule_label = f"{label}[{index}]"
        item = _object(
            raw_rule,
            rule_label,
            required={
                "rule_id",
                "version",
                "alias",
                "alias_kind",
                "match_mode",
                "required_context",
                "negative_context",
                "valid_from",
                "valid_to",
                "canonical_cik",
                "reviewed_on",
                "review_note",
            },
        )
        rule_id = _text(item["rule_id"], f"{rule_label}.rule_id", 64)
        if not RULE_ID_PATTERN.fullmatch(rule_id):
            raise ValueError(f"{rule_label}.rule_id must use lowercase snake case")
        if rule_id in rule_ids:
            raise ValueError(f"{label} contains duplicate rule_id {rule_id}")
        rule_ids.add(rule_id)
        rule_version = _text(item["version"], f"{rule_label}.version", 32)
        if not RULE_VERSION_PATTERN.fullmatch(rule_version):
            raise ValueError(f"{rule_label}.version contains unsupported characters")
        alias = _text(item["alias"], f"{rule_label}.alias", 80)
        if len(alias) < 2 or not any(character.isalnum() for character in alias):
            raise ValueError(f"{rule_label}.alias must contain at least two characters")
        alias_kind = _text(item["alias_kind"], f"{rule_label}.alias_kind", 20)
        if alias_kind not in DISCOVERY_ALIAS_KINDS:
            raise ValueError(f"{rule_label}.alias_kind is not supported")
        match_mode = _text(item["match_mode"], f"{rule_label}.match_mode", 20)
        if match_mode not in DISCOVERY_MATCH_MODES:
            raise ValueError(f"{rule_label}.match_mode is not supported")
        if match_mode == "ticker_token" and alias not in tickers:
            raise ValueError(f"{rule_label}.ticker_token alias must be a canonical ticker")
        required = _context_terms(
            item["required_context"], f"{rule_label}.required_context"
        )
        negative = _context_terms(
            item["negative_context"], f"{rule_label}.negative_context"
        )
        overlap = {term.casefold() for term in required} & {
            term.casefold() for term in negative
        }
        if overlap:
            raise ValueError(f"{rule_label} required and negative context overlap")
        valid_from = _nullable_review_date(
            item["valid_from"], f"{rule_label}.valid_from"
        )
        valid_to = _nullable_review_date(item["valid_to"], f"{rule_label}.valid_to")
        if valid_from and valid_to and valid_from > valid_to:
            raise ValueError(f"{rule_label} validity window is reversed")
        canonical_cik = _text(
            item["canonical_cik"], f"{rule_label}.canonical_cik", 13
        )
        if canonical_cik != issuer_key:
            raise ValueError(f"{rule_label}.canonical_cik must match the parent issuer_key")
        rules.append(
            DiscoveryAliasRule(
                rule_id=rule_id,
                version=rule_version,
                alias=alias,
                alias_kind=alias_kind,
                match_mode=match_mode,
                required_context=required,
                negative_context=negative,
                valid_from=valid_from,
                valid_to=valid_to,
                canonical_cik=canonical_cik,
                reviewed_on=_review_date(
                    item["reviewed_on"], f"{rule_label}.reviewed_on"
                ),
                review_note=_text(item["review_note"], f"{rule_label}.review_note", 240),
            )
        )
    return tuple(rules)


def _context_terms(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError(f"{label} must contain at most 20 terms")
    terms: list[str] = []
    seen: set[str] = set()
    for item in value:
        term = _text(item, label, 80)
        if len(term) < 2 or not any(character.isalnum() for character in term):
            raise ValueError(f"{label} terms must contain at least two characters")
        folded = term.casefold()
        if folded in seen:
            raise ValueError(f"{label} contains a duplicate case-insensitive term")
        seen.add(folded)
        terms.append(term)
    return tuple(terms)


def _nullable_review_date(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _review_date(value, label)


def _claim_aliases(
    aliases: tuple[str, ...],
    issuer_key: str,
    owners: dict[str, str],
    family: str,
) -> None:
    for alias in aliases:
        folded = alias.casefold()
        owner = owners.setdefault(folded, issuer_key)
        if owner != issuer_key:
            raise ValueError(f"Ambiguous {family} alias is assigned to multiple issuers: {alias}")


def _hosts(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= 10:
        raise ValueError(f"{label} must contain 1 to 10 hosts")
    hosts: list[str] = []
    for item in value:
        host = _text(item, label, 253).lower().rstrip(".")
        if not HOST_PATTERN.fullmatch(host) or ".." in host:
            raise ValueError(f"{label} contains an invalid hostname")
        if host in hosts:
            raise ValueError(f"{label} contains duplicate hosts")
        hosts.append(host)
    return tuple(hosts)


def _index(records) -> dict[str, object]:
    return {ticker: record for record in records for ticker in record.tickers}
