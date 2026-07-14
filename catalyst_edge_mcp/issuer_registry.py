"""Reviewed issuer-controlled RSS and Atom feed registry."""

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


ISSUER_FEEDS = (
    IssuerFeed(
        issuer_key="CIK0000320193",
        issuer_name="Apple Inc.",
        tickers=("AAPL",),
        feed_url="https://www.apple.com/newsroom/rss-feed.rss",
        official_hosts=("www.apple.com", "apple.com"),
    ),
    IssuerFeed(
        issuer_key="CIK0001045810",
        issuer_name="NVIDIA Corporation",
        tickers=("NVDA",),
        feed_url="https://nvidianews.nvidia.com/cats/press_release.xml",
        official_hosts=("nvidianews.nvidia.com", "investor.nvidia.com"),
    ),
)

ISSUER_FEED_INDEX = {
    ticker: feed for feed in ISSUER_FEEDS for ticker in feed.tickers
}


def reviewed_issuer_feed(ticker: str) -> IssuerFeed | None:
    return ISSUER_FEED_INDEX.get(ticker.replace(".", "-"))
