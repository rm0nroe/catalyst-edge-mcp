"""Bounded out-of-band refresh for the request-time GDELT discovery cache."""

from __future__ import annotations

import argparse
import asyncio
import json

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.adapters.gdelt import GdeltAdapter
from catalyst_edge_mcp.discovery_registry import reviewed_discovery_issuer
from catalyst_edge_mcp.models import SourceStatus, ToolInput
from catalyst_edge_mcp.settings import Settings


async def _run(tickers: list[str], lookback_days: int) -> int:
    settings = Settings.from_env()
    gate = ProviderGate(concurrency=1, requests_per_second=1 / 6)
    reports: list[dict[str, object]] = []
    failed = False
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
        adapter = GdeltAdapter(
            settings.evidence_store_path,
            registry={ticker: issuer},
            gate=gate,
            live_refresh=True,
            request_timeout_seconds=30.0,
        )
        try:
            result = await adapter.collect(ticker, lookback_days)
        except Exception as exc:
            failed = True
            reports.append(
                {
                    "ticker": ticker,
                    "status": SourceStatus.UNAVAILABLE.value,
                    "evidence_count": 0,
                    "degraded": True,
                    "error_class": type(exc).__name__,
                }
            )
            continue
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
                "status": result.status.value if result.status else None,
                "evidence_count": len(result.evidence),
                "degraded": result.degraded,
                "warnings": result.warnings,
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
