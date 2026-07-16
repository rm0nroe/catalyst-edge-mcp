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
    if type(root["version"]) is not int or root["version"] != 1:
        raise ValueError("Collector registry version must be 1")
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
        item = _object(
            raw_issuer,
            label,
            required={
                "issuer_key",
                "issuer_name",
                "tickers",
                "reviewed_on",
                "discovery_aliases",
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

        discovery_aliases = _aliases(
            item["discovery_aliases"], f"{label}.discovery_aliases"
        )
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
