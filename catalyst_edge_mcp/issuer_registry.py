"""Default reviewed issuer-feed registry loaded from local configuration."""

from __future__ import annotations

from catalyst_edge_mcp.registry_config import load_registry_bundle
from catalyst_edge_mcp.registry_models import IssuerFeed

_DEFAULTS = load_registry_bundle()
ISSUER_FEEDS = _DEFAULTS.issuer_feeds
ISSUER_FEED_INDEX = _DEFAULTS.issuer_feed_index


def reviewed_issuer_feed(ticker: str) -> IssuerFeed | None:
    return ISSUER_FEED_INDEX.get(ticker.replace(".", "-"))
