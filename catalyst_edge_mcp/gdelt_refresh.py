"""Bounded out-of-band refresh for the request-time GDELT discovery cache."""

from __future__ import annotations

import argparse
import asyncio
import json

from catalyst_edge_mcp.gdelt_web_ngrams import GdeltWebNgramsRefresher
from catalyst_edge_mcp.models import SourceStatus, ToolInput
from catalyst_edge_mcp.registry_config import load_registry_bundle
from catalyst_edge_mcp.settings import Settings
from catalyst_edge_mcp.source_policy import source_attributions


async def _run(tickers: list[str], lookback_days: int) -> int:
    settings = Settings.from_env()
    registry = load_registry_bundle(settings.registry_path)
    reports: list[dict[str, object]] = []
    reviewed: list[str] = []
    for raw_ticker in tickers:
        ticker = ToolInput(ticker=raw_ticker, lookback_days=lookback_days).ticker
        issuer = registry.discovery_index.get(ticker) or registry.discovery_index.get(
            ticker.replace(".", "-")
        )
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

    refresher = GdeltWebNgramsRefresher(
        settings.evidence_store_path,
        registry=registry.discovery_index,
    )
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
                "candidate_documents": result.candidate_documents,
                "accepted_documents": result.accepted_documents,
                "ingested_documents": result.ingested_documents,
                "accepted_overflow_documents": result.accepted_overflow_documents,
                "rejected_documents": result.rejected_documents,
                "rejection_reasons": dict(result.rejection_reasons),
                "degraded": result.degraded,
                "warnings": list(result.warnings),
            }
        )
    print(
        json.dumps(
            {
                "provider": "gdelt",
                "attributions": [
                    item.model_dump(mode="json")
                    for item in source_attributions(["gdelt"])
                ],
                "results": reports,
            },
            indent=2,
        )
    )
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the GDELT discovery cache")
    parser.add_argument("tickers", nargs="+", help="Reviewed public-company tickers")
    parser.add_argument("--lookback-days", type=int, default=14)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.tickers, args.lookback_days)))


if __name__ == "__main__":
    main()
