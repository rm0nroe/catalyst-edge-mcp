"""Default reviewed discovery registry loaded from local configuration."""

from __future__ import annotations

from catalyst_edge_mcp.registry_config import load_registry_bundle
from catalyst_edge_mcp.registry_models import DiscoveryIssuer

_DEFAULTS = load_registry_bundle()
DISCOVERY_ISSUERS = _DEFAULTS.discovery_issuers
DISCOVERY_ISSUER_INDEX = _DEFAULTS.discovery_index


def reviewed_discovery_issuer(ticker: str) -> DiscoveryIssuer | None:
    return DISCOVERY_ISSUER_INDEX.get(ticker.replace(".", "-"))
