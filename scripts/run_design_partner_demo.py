"""Run the bounded five-ticker design-partner demonstration."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from importlib.metadata import version
from pathlib import Path

from pydantic import ValidationError

from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.models import CatalystEdgeResponse, ToolInput
from catalyst_edge_mcp.server import build_service
from catalyst_edge_mcp.settings import Settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run five single-ticker calls and capture bounded acceptance proof"
    )
    parser.add_argument("tickers", nargs=5, metavar="TICKER")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _requests(tickers: list[str], lookback_days: int) -> list[ToolInput]:
    requests = [ToolInput(ticker=ticker, lookback_days=lookback_days) for ticker in tickers]
    normalized = [request.ticker for request in requests]
    if len(set(normalized)) != 5:
        raise ValueError("five unique tickers are required")
    return requests


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _claim_id(responses: list[CatalystEdgeResponse]) -> tuple[str, str] | None:
    for response in responses:
        for evidence in response.evidence:
            if evidence.context and evidence.context.claim_id:
                return response.ticker, evidence.context.claim_id
    return None


def _missing_or_rejected(responses: list[CatalystEdgeResponse]) -> dict[str, object] | None:
    for response in responses:
        if response.data_quality.reason_records:
            reason = response.data_quality.reason_records[0]
            return {
                "ticker": response.ticker,
                "kind": "reason_record",
                "code": reason.code.value,
                "scope": reason.scope.value,
                "scope_id": reason.scope_id,
                "family": reason.family,
            }
        if response.data_quality.missing_families:
            family = response.data_quality.missing_families[0]
            status = next(
                (
                    item
                    for item in response.data_quality.family_statuses
                    if item.family == family
                ),
                None,
            )
            return {
                "ticker": response.ticker,
                "kind": "missing_family",
                "family": family,
                "status": status.status.value if status else None,
                "reason": status.reason if status else None,
            }
    return None


def _paginate_claim(
    store: EvidenceStore, output_dir: Path, ticker: str, claim_id: str
) -> dict[str, object]:
    cursor = 0
    pages: list[str] = []
    source_ids: list[str] = []
    total_sources: int | None = None
    while True:
        page = store.claim_sources(claim_id, cursor=cursor, limit=1)
        page_name = f"claim-{len(pages) + 1:02d}.json"
        _write_json(output_dir / page_name, page.model_dump(mode="json"))
        pages.append(page_name)
        source_ids.extend(source.source_reference_id for source in page.sources)
        total_sources = page.total_sources
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    complete = total_sources == len(source_ids) == len(set(source_ids))
    return {
        "ticker": ticker,
        "claim_id": claim_id,
        "page_size": 1,
        "page_files": pages,
        "total_sources": total_sources,
        "returned_source_count": len(source_ids),
        "unique_source_count": len(set(source_ids)),
        "complete": complete,
    }


async def _run(args: argparse.Namespace) -> int:
    requests = _requests(args.tickers, args.lookback_days)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("output directory must be absent or empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    settings = Settings.from_env()
    service = build_service(settings)
    responses = [await service.evaluate(request) for request in requests]
    dossier_files: dict[str, str] = {}
    for response in responses:
        name = f"dossier-{response.ticker}.json"
        _write_json(args.output_dir / name, response.model_dump(mode="json"))
        dossier_files[response.ticker] = name

    claim = _claim_id(responses)
    claim_pagination = None
    if claim:
        store = EvidenceStore(settings.evidence_store_path)
        try:
            claim_pagination = _paginate_claim(store, args.output_dir, *claim)
        finally:
            store.close()
    missing_or_rejected = _missing_or_rejected(responses)
    manifest = {
        "package_version": version("catalyst-edge-mcp"),
        "tickers": [response.ticker for response in responses],
        "one_call_per_ticker": True,
        "dossier_files": dossier_files,
        "review_ticker": claim[0] if claim else responses[0].ticker,
        "claim_pagination": claim_pagination,
        "missing_or_rejected_case": missing_or_rejected,
        "acceptance": {
            "five_schema_valid_calls": len(responses) == 5,
            "full_claim_pagination": bool(
                claim_pagination and claim_pagination["complete"]
            ),
            "missing_or_rejected_case": missing_or_rejected is not None,
        },
    }
    _write_json(args.output_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0 if all(manifest["acceptance"].values()) else 1


def main() -> None:
    try:
        raise SystemExit(asyncio.run(_run(_parser().parse_args())))
    except (OSError, ValidationError, ValueError) as exc:
        print(f"demo failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
