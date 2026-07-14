"""Reviewed exact aliases for public social-attention collection."""

from __future__ import annotations

from dataclasses import dataclass


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


SOCIAL_ISSUERS = (
    SocialIssuer("CIK0000320193", "Apple Inc.", ("AAPL",), ("Apple Inc",)),
    SocialIssuer("CIK0001045810", "NVIDIA Corporation", ("NVDA",), ("NVIDIA",)),
    SocialIssuer("CIK0001318605", "Tesla, Inc.", ("TSLA",), ("Tesla Inc",)),
    SocialIssuer("CIK0001819994", "Rocket Lab USA, Inc.", ("RKLB",), ("Rocket Lab",)),
    SocialIssuer(
        "CIK0001067983",
        "Berkshire Hathaway Inc.",
        ("BRK-A", "BRK-B"),
        ("Berkshire Hathaway",),
    ),
)

SOCIAL_ISSUER_INDEX = {
    ticker: issuer for issuer in SOCIAL_ISSUERS for ticker in issuer.tickers
}
