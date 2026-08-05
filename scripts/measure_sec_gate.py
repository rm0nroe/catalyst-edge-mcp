#!/usr/bin/env python
"""Measure gate admission wait vs network I/O under production topology.

Answers the question the bug report gates all rate/deadline tuning on: when an
SEC adapter blows its 8s budget, is the time going to gate admission
(semaphore + rate spacing) or to actual upstream I/O?

Runs the real production composition root (`build_service`) over a ticker
sample at production concurrency against live SEC, then prints the split.

    uv run --extra dev python scripts/measure_sec_gate.py --tickers AAPL,MSFT,...

Gate rates are unchanged, so this stays within the same request envelope the
service already uses. It does not touch the cron, the workspace, or any state.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from catalyst_edge_mcp.adapters.base import gate_timings, reset_gate_timings
from catalyst_edge_mcp.models import ToolInput
from catalyst_edge_mcp.server import build_service
from catalyst_edge_mcp.settings import Settings

# Families served by the shared SEC gate; the ones the bug report is about.
SEC_FAMILIES = ("filings_news", "insider_trading")


async def evaluate_one(service, ticker: str, lookback_days: int, limiter: asyncio.Semaphore):
    async with limiter:
        started = time.monotonic()
        try:
            response = await service.evaluate(ToolInput(ticker=ticker, lookback_days=lookback_days))
        except Exception as exc:  # a failed ticker must not abort the measurement
            return {"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"}
        elapsed = time.monotonic() - started
        statuses = {
            fs.family: fs.status
            for fs in response.data_quality.family_statuses
            if fs.family in SEC_FAMILIES
        }
        return {
            "ticker": ticker,
            "elapsed_s": round(elapsed, 3),
            "statuses": {k: str(getattr(v, "value", v)) for k, v in statuses.items()},
        }


def format_gate_table(timings) -> str:
    header = (
        f"{'gate':<12} {'reqs':>5} {'never':>6} {'admit_tot':>10} {'body_tot':>9} "
        f"{'admit_avg':>10} {'body_avg':>9} {'admit_max':>10} {'admit%':>7}"
    )
    lines = [header, "-" * len(header)]
    for name in sorted(timings):
        t = timings[name]
        total = t.admission_wait_s + t.body_s
        share = (t.admission_wait_s / total * 100) if total > 0 else 0.0
        lines.append(
            f"{name:<12} {t.requests:>5} {t.never_admitted:>6} "
            f"{t.admission_wait_s:>10.2f} {t.body_s:>9.2f} "
            f"{t.admission_wait_s / t.requests:>10.3f} {t.body_s / t.requests:>9.3f} "
            f"{t.max_admission_wait_s:>10.3f} {share:>6.1f}%"
        )
    return "\n".join(lines)


async def main_async(args) -> int:
    settings = Settings.from_env()
    if not settings.sec_user_agent:
        print("CATALYST_EDGE_SEC_USER_AGENT is unset; SEC adapters would not be built.")
        return 2

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if args.tickers_file:
        tickers += [
            line.strip().upper()
            for line in Path(args.tickers_file).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    if not tickers:
        print("no tickers given")
        return 2

    service = build_service(settings)
    if args.adapter_timeout is not None:
        # Deliberate experiment knob for step 2; production default is 8.0.
        service.adapter_timeout_seconds = args.adapter_timeout

    print(
        f"tickers={len(tickers)} concurrency={args.concurrency} "
        f"adapter_timeout={service.adapter_timeout_seconds}s "
        f"lookback_days={args.lookback_days}"
    )

    reset_gate_timings()
    limiter = asyncio.Semaphore(args.concurrency)
    wall_started = time.monotonic()
    results = await asyncio.gather(
        *(evaluate_one(service, t, args.lookback_days, limiter) for t in tickers)
    )
    wall = time.monotonic() - wall_started
    timings = gate_timings()

    print(f"\nwall={wall:.1f}s\n")
    print(format_gate_table(timings))

    status_counts: dict[str, dict[str, int]] = {f: {} for f in SEC_FAMILIES}
    errors = 0
    for row in results:
        if "error" in row:
            errors += 1
            continue
        for family, status in row["statuses"].items():
            status_counts[family][status] = status_counts[family].get(status, 0) + 1
    print("\nfamily outcomes:")
    for family in SEC_FAMILIES:
        print(f"  {family}: {status_counts[family]}")
    if errors:
        print(f"  evaluation errors: {errors}")

    sec = timings.get("sec")
    if sec and sec.requests:
        total = sec.admission_wait_s + sec.body_s
        share = (sec.admission_wait_s / total * 100) if total else 0.0
        print(
            f"\nVERDICT: {share:.1f}% of shared-'sec'-gate time was admission wait; "
            f"{sec.never_admitted}/{sec.requests} requests died queueing; "
            f"worst single admission wait {sec.max_admission_wait_s:.2f}s "
            f"against a {service.adapter_timeout_seconds}s adapter budget."
        )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(
                {
                    "wall_s": wall,
                    "concurrency": args.concurrency,
                    "adapter_timeout_s": service.adapter_timeout_seconds,
                    "lookback_days": args.lookback_days,
                    "gates": {
                        name: {
                            "requests": t.requests,
                            "never_admitted": t.never_admitted,
                            "admission_wait_s": t.admission_wait_s,
                            "body_s": t.body_s,
                            "max_admission_wait_s": t.max_admission_wait_s,
                        }
                        for name, t in timings.items()
                    },
                    "results": results,
                },
                indent=2,
                sort_keys=True,
            )
        )
        print(f"\nwrote {args.json_out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", default="", help="comma-separated tickers")
    parser.add_argument("--tickers-file", help="file with one ticker per line")
    parser.add_argument("--concurrency", type=int, default=4, help="production default is 4")
    parser.add_argument("--lookback-days", type=int, default=14)
    parser.add_argument(
        "--adapter-timeout",
        type=float,
        default=None,
        help="override the adapter deadline (production default 8.0)",
    )
    parser.add_argument("--json-out", help="write the full measurement as JSON")
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
