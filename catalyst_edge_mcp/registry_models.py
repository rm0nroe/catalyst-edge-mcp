"""Typed records shared by validated local collector registries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IssuerFeed:
    issuer_key: str
    issuer_name: str
    tickers: tuple[str, ...]
    feed_url: str
    official_hosts: tuple[str, ...]
    refresh_seconds: int = 600
    reviewed_on: str = "2026-07-13"
    review_note: str = "Issuer-controlled public feed; retain metadata and links only."


@dataclass(frozen=True, slots=True)
class DiscoveryIssuer:
    issuer_key: str
    issuer_name: str
    tickers: tuple[str, ...]
    query_aliases: tuple[str, ...]
    refresh_seconds: int = 300
    reviewed_on: str = "2026-07-13"

    @property
    def gdelt_query(self) -> str:
        quoted = [f'"{alias}"' for alias in self.query_aliases]
        return quoted[0] if len(quoted) == 1 else f"({' OR '.join(quoted)})"


@dataclass(frozen=True, slots=True)
class SocialIssuer:
    issuer_key: str
    issuer_name: str
    tickers: tuple[str, ...]
    exact_aliases: tuple[str, ...]
    reviewed_on: str = "2026-07-13"

    @property
    def bluesky_query(self) -> str:
        terms = [
            *(f'"${ticker}"' for ticker in self.tickers),
            *(f'"{alias}"' for alias in self.exact_aliases),
        ]
        return f"({' OR '.join(terms)})"


@dataclass(frozen=True, slots=True)
class PublisherDomainQuality:
    domain: str
    tier: str
    quality: float
    reviewed_on: str
    review_note: str
