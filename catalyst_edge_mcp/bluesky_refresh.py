"""Manual bounded refresh for the forward-only Bluesky attention cache."""

from __future__ import annotations

import argparse
import asyncio
import json

from catalyst_edge_mcp.collection_lifecycle import BlueskyCollectionLifecycle
from catalyst_edge_mcp.models import SourceStatus, ToolInput
from catalyst_edge_mcp.settings import Settings


async def _run(tickers: list[str]) -> int:
    settings = Settings.from_env()
    reviewed = [ToolInput(ticker=ticker).ticker for ticker in tickers]
    lifecycle = BlueskyCollectionLifecycle(settings, tickers=reviewed)
    try:
        results = await lifecycle.run_once()
        reports = []
        failed = False
        for ticker in reviewed:
            result = results.get(ticker)
            if result is None:
                reports.append(
                    {
                        "ticker": ticker,
                        "status": SourceStatus.NO_OBSERVATIONS.value,
                        "warning": "No reviewed Bluesky aliases are registered.",
                    }
                )
                continue
            failed = failed or result.degraded
            reports.append(
                {
                    "ticker": ticker,
                    "status": result.status.value if result.status else None,
                    "evidence_count": len(result.evidence),
                    "degraded": result.degraded,
                    "warnings": list(result.warnings),
                }
            )
        print(json.dumps({"provider": "bluesky", "results": reports}, indent=2))
        return 1 if failed else 0
    finally:
        await lifecycle.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the Bluesky forward cache")
    parser.add_argument("tickers", nargs="+", help="Reviewed public-company tickers")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.tickers)))


if __name__ == "__main__":
    main()
