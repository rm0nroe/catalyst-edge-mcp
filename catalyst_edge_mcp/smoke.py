"""Opt-in live provider and provenance readiness check."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from catalyst_edge_mcp.models import (
    CatalystEdgeResponse,
    Direction,
    Evidence,
    PolicyDecision,
    ToolInput,
)
from catalyst_edge_mcp.server import build_service
from catalyst_edge_mcp.settings import Settings

ALLOWLISTED_MATERIAL_EVENT_SIGNALS = frozenset(
    {
        "bankruptcy",
        "delisting",
        "restatement",
        "material_agreement",
        "material_contract",
        "earnings_release",
        "guidance_change",
        "acquisition",
        "financing",
        "adverse_filing",
    }
)


def _evidence_providers(item: Evidence) -> set[str]:
    """Attribute normalized evidence using only stable, public source labels."""
    providers: set[str] = set()
    for source in item.sources:
        if source.source_id:
            providers.add(source.source_id)
            continue
        name = source.name.casefold()
        if name == "sec edgar":
            providers.add("sec")
        elif name.startswith("fmp "):
            providers.add("fmp")
        elif name.startswith("finnhub "):
            providers.add("finnhub")
        elif name in {"flowalgo", "cheddarflow"}:
            providers.add(name)
        elif name == "yfinance chain snapshot":
            providers.add("yfinance")
    return providers


def _has_sec_provenance(item: Evidence) -> bool:
    return any(
        source.source_id == "sec" or source.name.casefold() == "sec edgar"
        for source in item.sources
    )


def _is_readiness_directional(item: Evidence) -> bool:
    """Qualify direction by evidence semantics and reviewed policy, never name alone."""
    if item.direction == Direction.NEUTRAL:
        return False
    if item.family == "insider_trading" and _has_sec_provenance(item):
        return True
    if (
        item.family == "filings_news"
        and item.signal in ALLOWLISTED_MATERIAL_EVENT_SIGNALS
        and any(source.source_id in {"sec", "issuer_feed"} for source in item.sources)
    ):
        return True
    return any(
        source.policy_decision == PolicyDecision.APPROVED
        and source.source_id not in {None, "sec", "gdelt", "bluesky", "mastodon"}
        for source in item.sources
    )


def readiness_report(
    response: CatalystEdgeResponse, adapters: Sequence[Any]
) -> dict[str, Any]:
    """Build a secret-free readiness report from normalized response provenance."""
    evidence_by_provider: dict[str, int] = defaultdict(int)
    for item in response.evidence:
        for provider in _evidence_providers(item):
            evidence_by_provider[provider] += 1

    configured: dict[str, set[str]] = defaultdict(set)
    for adapter in adapters:
        provider = str(getattr(adapter, "provider", type(adapter).__name__)).casefold()
        configured[provider].add(str(getattr(adapter, "family", "unknown")))

    provider_status = [
        {
            "provider": provider,
            "families": sorted(families),
            "status": "fresh_evidence" if evidence_by_provider[provider] else "no_fresh_evidence",
            "evidence_count": evidence_by_provider[provider],
        }
        for provider, families in sorted(configured.items())
    ]
    sec_provenance = any(_has_sec_provenance(item) for item in response.evidence)
    qualifying = [item for item in response.evidence if _is_readiness_directional(item)]
    fresh_directional_providers = sorted(
        {provider for item in qualifying for provider in _evidence_providers(item)}
    )
    ready = sec_provenance and bool(qualifying)
    return {
        "ticker": response.ticker,
        "as_of": response.as_of.isoformat(),
        "providers": provider_status,
        "coverage": response.data_quality.coverage,
        "missing_families": response.data_quality.missing_families,
        "sec_provenance": sec_provenance,
        "fresh_directional_family": bool(qualifying),
        "fresh_directional_providers": fresh_directional_providers,
        "launch_ready": ready,
        "warnings": response.data_quality.warnings,
    }


async def _run(ticker: str, lookback_days: int) -> int:
    settings = Settings.from_env()
    configuration = settings.launch_configuration()
    if not configuration["configuration_ready"]:
        print(
            json.dumps(
                {
                    **configuration,
                    "ticker": ToolInput(ticker=ticker, lookback_days=lookback_days).ticker,
                    "launch_ready": False,
                    "message": "Populate and export the listed environment variables.",
                },
                indent=2,
            )
        )
        return 2
    service = build_service(settings)
    response = await service.evaluate(ToolInput(ticker=ticker, lookback_days=lookback_days))
    report = readiness_report(response, service.adapters)
    report = {**configuration, **report}
    print(json.dumps(report, indent=2))
    return 0 if report["launch_ready"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Catalyst Edge credential/provenance check")
    parser.add_argument("ticker")
    parser.add_argument("--lookback-days", type=int, default=14)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.ticker, args.lookback_days)))


if __name__ == "__main__":
    main()
