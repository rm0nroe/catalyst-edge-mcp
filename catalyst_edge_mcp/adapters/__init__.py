"""Provider adapter interfaces and implementations."""

from catalyst_edge_mcp.adapters.base import CatalystSignalAdapter, StaticAdapter
from catalyst_edge_mcp.adapters.bluesky import BlueskyAdapter
from catalyst_edge_mcp.adapters.gdelt import GdeltAdapter
from catalyst_edge_mcp.adapters.issuer_feeds import IssuerFeedAdapter
from catalyst_edge_mcp.sec_funds import SecFundAdapter

__all__ = [
    "BlueskyAdapter",
    "CatalystSignalAdapter",
    "GdeltAdapter",
    "IssuerFeedAdapter",
    "SecFundAdapter",
    "StaticAdapter",
]
