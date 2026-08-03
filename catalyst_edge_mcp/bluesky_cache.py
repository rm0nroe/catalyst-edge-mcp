"""Operator deletion command for locally retained Bluesky-derived cache data."""

from __future__ import annotations

import argparse
import json

from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.models import ToolInput
from catalyst_edge_mcp.registry_config import load_registry_bundle
from catalyst_edge_mcp.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete local Bluesky-derived cache data")
    parser.add_argument("tickers", nargs="+", help="Reviewed public-company tickers")
    args = parser.parse_args()
    settings = Settings.from_env()
    registry = load_registry_bundle(settings.registry_path)
    store = EvidenceStore(settings.evidence_store_path)
    reports = []
    try:
        for raw_ticker in args.tickers:
            ticker = ToolInput(ticker=raw_ticker).ticker
            issuer = registry.social_index.get(ticker) or registry.social_index.get(
                ticker.replace(".", "-")
            )
            if issuer is None:
                reports.append({"ticker": ticker, "status": "unregistered"})
                continue
            reports.append(
                {
                    "ticker": ticker,
                    "status": "deleted",
                    **store.delete_social_cache(issuer.issuer_key, "bluesky"),
                }
            )
    finally:
        store.close()
    print(json.dumps({"provider": "bluesky", "results": reports}, indent=2))


if __name__ == "__main__":
    main()
