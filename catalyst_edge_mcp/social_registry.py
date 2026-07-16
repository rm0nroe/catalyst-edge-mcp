"""Default reviewed social registry loaded from local configuration."""

from __future__ import annotations

from catalyst_edge_mcp.registry_config import load_registry_bundle
from catalyst_edge_mcp.registry_models import SocialIssuer

__all__ = ["SOCIAL_ISSUERS", "SOCIAL_ISSUER_INDEX", "SocialIssuer"]

_DEFAULTS = load_registry_bundle()
SOCIAL_ISSUERS = _DEFAULTS.social_issuers
SOCIAL_ISSUER_INDEX = _DEFAULTS.social_index
