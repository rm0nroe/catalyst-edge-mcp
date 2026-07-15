"""Bounded out-of-band refresh for the request-time GDELT discovery cache."""

from __future__ import annotations

import argparse
import asyncio
import json

from catalyst_edge_mcp.discovery_registry import reviewed_discovery_issuer
from catalyst_edge_mcp.gdelt_web_ngrams import GdeltWebNgramsRefresher
from catalyst_edge_mcp.models import SourceStatus, ToolInput
from catalyst_edge_mcp.settings import Settings


async def _run(tickers: list[str], lookback_days: int) -> int:
    settings = Settings.from_env()
    reports: list[dict[str, object]] = []
    reviewed: list[str] = []
    for raw_ticker in tickers:
        ticker = ToolInput(ticker=raw_ticker, lookback_days=lookback_days).ticker
        issuer = reviewed_discovery_issuer(ticker)
        if issuer is None:
            reports.append(
                {
                    "ticker": ticker,
                    "status": SourceStatus.NO_OBSERVATIONS.value,
                    "evidence_count": 0,
                    "warning": "No reviewed GDELT aliases are registered.",
                }
            )
            continue
        reviewed.append(ticker)

    refresher = GdeltWebNgramsRefresher(settings.evidence_store_path)
    results = await refresher.refresh(reviewed, lookback_days)
    failed = False
    for ticker in reviewed:
        result = results[ticker]
        failed = failed or result.status in {
            SourceStatus.RATE_LIMITED,
            SourceStatus.TIMEOUT,
            SourceStatus.SCHEMA_ERROR,
            SourceStatus.STALE,
            SourceStatus.UNAVAILABLE,
        }
        reports.append(
            {
                "ticker": ticker,
                "status": result.status.value,
                "evidence_count": result.evidence_count,
                "files_processed": result.files_processed,
                "matched_documents": result.matched_documents,
                "degraded": result.degraded,
                "warnings": list(result.warnings),
            }
        )
    print(json.dumps({"provider": "gdelt", "results": reports}, indent=2))
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the GDELT discovery cache")
    parser.add_argument("tickers", nargs="+", help="Reviewed public-company tickers")
    parser.add_argument("--lookback-days", type=int, default=14)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.tickers, args.lookback_days)))


if __name__ == "__main__":
    main()
