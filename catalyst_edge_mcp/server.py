"""FastMCP registration and local stdio/streamable-HTTP transports."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from catalyst_edge_mcp.adapters.bluesky import BlueskyAdapter
from catalyst_edge_mcp.adapters.gdelt import GdeltAdapter
from catalyst_edge_mcp.adapters.issuer_feeds import IssuerFeedAdapter
from catalyst_edge_mcp.collection_lifecycle import build_collection_lifecycle
from catalyst_edge_mcp.models import CatalystEdgeResponse, RiskMode, Ticker, ToolInput
from catalyst_edge_mcp.registry_config import RegistryBundle, load_registry_bundle
from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from catalyst_edge_mcp.sec_ownership import SecInsiderAdapter
from catalyst_edge_mcp.service import CatalystService
from catalyst_edge_mcp.settings import Settings

# Provider credentials can be carried in request query strings. FastMCP configures
# application logging at INFO, while httpx's INFO message includes the full URL.
# Keep transport internals below that threshold so credentials never reach MCP
# stderr or CLI smoke output.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_service(
    settings: Settings,
    registry: RegistryBundle | None = None,
) -> CatalystService:
    """The sole production composition root for provider adapters."""
    registry = registry or load_registry_bundle(settings.registry_path)
    adapters = []
    if settings.sec_user_agent:
        adapters.extend(
            [
                SecFilingsAdapter(settings.sec_user_agent),
                SecInsiderAdapter(settings.sec_user_agent),
            ]
        )
    if settings.issuer_feeds_enabled:
        adapters.append(
            IssuerFeedAdapter(
                settings.evidence_store_path,
                registry=registry.issuer_feed_index,
            )
        )
    if settings.gdelt_enabled:
        # GDELT's legacy search API is not reliable within the request deadline.
        # Production requests read its cache; the bounded refresh CLI owns network I/O.
        adapters.append(
            GdeltAdapter(
                settings.evidence_store_path,
                registry=registry.discovery_index,
                live_refresh=False,
                max_cache_age_seconds=settings.gdelt_freshness_max_age_seconds,
                publisher_quality_registry=registry.publisher_quality_index,
            )
        )
    if settings.bluesky_enabled:
        adapters.append(
            BlueskyAdapter(
                settings.evidence_store_path,
                registry=registry.social_index,
            )
        )
    # Conditional vendor keys are intentionally not composed until a deployed
    # source-policy approval can be bound to the account/plan. Credentials alone
    # never establish commercial rights.
    # Phase 5 entitlement review found no production-ready options provider.
    # Keep adapters available for isolated fixtures/private diagnostics, but do
    # not call a provider before its automation, storage, and output rights pass.
    # Sentiment likewise has no production composition path while every audited
    # candidate is gate-incomplete.
    return CatalystService(adapters)


_initial_settings = Settings.from_env()
_service = build_service(_initial_settings)


@asynccontextmanager
async def server_lifespan(_server):
    """Own automatic collectors outside every MCP request path."""
    lifecycle = build_collection_lifecycle(Settings.from_env())
    if lifecycle is not None:
        lifecycle.start()
    try:
        yield {"collection_lifecycle": lifecycle}
    finally:
        if lifecycle is not None:
            await lifecycle.stop()


mcp = FastMCP(
    "Catalyst Edge",
    instructions=(
        "Produces source-linked catalyst evidence dossiers using deterministic, "
        "unbacktested scoring. It does not provide investment recommendations."
    ),
    host=_initial_settings.host,
    port=_initial_settings.port,
    json_response=True,
    stateless_http=True,
    lifespan=server_lifespan,
)


@mcp.tool()
async def catalyst_edge_score(
    ticker: Ticker,
    lookback_days: Annotated[int, Field(ge=1, le=90, strict=True)] = 14,
    include_sources: Annotated[bool, Field(strict=True)] = True,
    include_raw_signals: Annotated[bool, Field(strict=True)] = False,
    risk_mode: RiskMode = RiskMode.RESEARCH,
) -> CatalystEdgeResponse:
    """Assess recent catalyst evidence, provenance, confidence, and next checks for a ticker."""
    request = ToolInput(
        ticker=ticker,
        lookback_days=lookback_days,
        include_sources=include_sources,
        include_raw_signals=include_raw_signals,
        risk_mode=risk_mode,
    )
    return await _service.evaluate(request)


# The v1 SDK's generated argument model otherwise ignores unknown JSON fields.
_registered_tool = mcp._tool_manager._tools["catalyst_edge_score"]
_registered_tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
_registered_tool.fn_metadata.arg_model.model_rebuild(force=True)
_registered_tool.parameters = _registered_tool.fn_metadata.arg_model.model_json_schema(
    by_alias=True
)
# Computed public fields such as Evidence.source_count exist only in Pydantic's
# serialization schema. FastMCP validates serialized tool output against this
# object, so the validation-mode schema would reject otherwise valid responses.
_registered_tool.fn_metadata.output_schema = CatalystEdgeResponse.model_json_schema(
    mode="serialization"
)


def main() -> None:
    settings = Settings.from_env()
    mcp.settings.host = settings.host
    mcp.settings.port = settings.port
    with suppress(KeyboardInterrupt, asyncio.CancelledError):
        mcp.run(transport=settings.transport)


if __name__ == "__main__":
    main()
