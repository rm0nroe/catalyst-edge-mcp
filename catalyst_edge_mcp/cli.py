"""Direct local invocation for smoke testing the service."""

from __future__ import annotations

import argparse
import asyncio

from catalyst_edge_mcp.models import RiskMode, ToolInput
from catalyst_edge_mcp.server import build_service
from catalyst_edge_mcp.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a catalyst edge dossier")
    parser.add_argument("ticker")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument(
        "--risk-mode",
        choices=[mode.value for mode in RiskMode],
        default="research",
    )
    parser.add_argument("--include-raw-signals", action="store_true")
    parser.add_argument("--no-sources", action="store_true")
    args = parser.parse_args()
    request = ToolInput(
        ticker=args.ticker,
        lookback_days=args.lookback_days,
        include_sources=not args.no_sources,
        include_raw_signals=args.include_raw_signals,
        risk_mode=args.risk_mode,
    )
    response = asyncio.run(build_service(Settings.from_env()).evaluate(request))
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
