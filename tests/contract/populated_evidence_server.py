"""Test-only MCP server that always returns one populated evidence item."""

from datetime import datetime

from catalyst_edge_mcp import server
from catalyst_edge_mcp.adapters.base import StaticAdapter
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import AdapterResult, Direction, Evidence, Source
from catalyst_edge_mcp.service import CatalystService

AS_OF = datetime(2026, 7, 12, 16, 0, tzinfo=UTC)


def main() -> None:
    evidence = Evidence(
        family="filings_news",
        signal="material_filing",
        direction=Direction.BULLISH,
        strength=0.8,
        confidence=0.75,
        source_quality=0.9,
        timestamp=AS_OF,
        sources=[
            Source(
                name="filings_news_fixture",
                url="https://example.com/filings_news/material_filing",
                observed_at=AS_OF,
            )
        ],
        notes="Normalized material_filing evidence.",
    )
    adapter = StaticAdapter(
        family="filings_news",
        result=AdapterResult(family="filings_news", evidence=[evidence]),
    )
    server._service = CatalystService([adapter], clock=lambda: AS_OF)
    server.main()


if __name__ == "__main__":
    main()
