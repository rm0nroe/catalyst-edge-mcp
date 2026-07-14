"""Reviewed company aliases for bounded discovery-source queries."""

from __future__ import annotations

from dataclasses import dataclass


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


DISCOVERY_ISSUERS = (
    DiscoveryIssuer(
        "CIK0000320193", "Apple Inc.", ("AAPL",), ("Apple Inc", "Apple Incorporated")
    ),
    DiscoveryIssuer(
        "CIK0001045810", "NVIDIA Corporation", ("NVDA",), ("NVIDIA", "NVIDIA Corporation")
    ),
    DiscoveryIssuer(
        "CIK0001318605", "Tesla, Inc.", ("TSLA",), ("Tesla Inc", "Tesla Motors")
    ),
    DiscoveryIssuer(
        "CIK0001819994", "Rocket Lab USA, Inc.", ("RKLB",), ("Rocket Lab", "Rocket Lab USA")
    ),
    DiscoveryIssuer(
        "CIK0001067983",
        "Berkshire Hathaway Inc.",
        ("BRK-A", "BRK-B"),
        ("Berkshire Hathaway",),
    ),
)

DISCOVERY_ISSUER_INDEX = {
    ticker: issuer for issuer in DISCOVERY_ISSUERS for ticker in issuer.tickers
}


def reviewed_discovery_issuer(ticker: str) -> DiscoveryIssuer | None:
    return DISCOVERY_ISSUER_INDEX.get(ticker.replace(".", "-"))
