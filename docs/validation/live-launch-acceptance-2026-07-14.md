# Live launch acceptance — 2026-07-14

> **Current scope note — 2026-07-15:** This is dated evidence that the live
> semantic readiness gate worked for one evidence window. It is not a persistent
> build-health guarantee and does not complete the pending 20–30 real-case
> product evaluation. For the current owner-operated build, a later exit 1 can
> correctly mean that no qualifying fresh catalyst exists.

## Result

The evidence-semantic launch gate passed against live data on merged `main` at
commit `ed8a9cef29a777df8fdafa96d9135cac5a177575`.

The existing local `.env` was sourced without printing it. The following
secret-free command was then run sequentially for AAPL, NVDA, TSLA, BRK.B, and
RKLB:

```bash
uv run catalyst-edge-smoke <TICKER> --lookback-days 14
```

| Ticker | As of (UTC) | SEC provenance | Fresh directional family | Launch ready | Exit |
| --- | --- | --- | --- | --- | ---: |
| AAPL | 2026-07-14T21:30:32.772146+00:00 | false | false | false | 1 |
| NVDA | 2026-07-14T21:30:39.419005+00:00 | true | false | false | 1 |
| TSLA | 2026-07-14T21:30:45.907474+00:00 | true | false | false | 1 |
| BRK.B | 2026-07-14T21:30:52.400518+00:00 | false | false | false | 1 |
| RKLB | 2026-07-14T21:30:58.900263+00:00 | true | true | true | 0 |

RKLB supplied two fresh SEC evidence items and a qualifying directional direct
insider observation. Coverage remained partial, and the absent optional
families did not receive fabricated readiness credit. The other four tickers
correctly remained fail-closed.

## Operational state

- Configuration preflight passed with SEC, reviewed issuer feeds, GDELT, and
  Bluesky composed.
- FMP and Finnhub credentials were present but remained conditional and were
  not composed without explicit policy approval.
- Every GDELT request in this acceptance run timed out and degraded cleanly.
  This is a live-source reliability issue to monitor, not a reason to weaken
  the readiness gate.
- Bluesky remained in its required 14-day warm-up.
- Options flow still requires a licensed transaction-plus-quote provider;
  technicals still require an approved OHLC source; sentiment remains disabled.

## Local runtime handoff

Run the merged `main` commit above with the SEC identity and existing local
collector settings. Keep optional conditional providers disabled. Run the same
smoke command as a dated runtime check, while treating a later exit 1 as a valid
evidence-window outcome rather than a process failure. Preserve the current
typed degradation behavior.

This acceptance proves the required live provenance and directional-evidence
gate. It does not claim full five-family coverage, provider entitlement for
options/OHLC, or completion of the Bluesky collection window.

## Subsequent provider-readiness remediation

Later on 2026-07-14, repeated GDELT latency was removed from the MCP request
path in favor of an explicit cache-refresh command. Bluesky was changed to fetch
two complete historical seven-day windows directly; a live NVDA validation
returned neutral fresh attention with six baseline and 11 current exact-match
posts. The options/OHLC/sentiment entitlement blockers remain external and are
recorded in the Phase 5 audit.

## 2026-07-15 local recheck

- RKLB returned configuration-ready partial coverage with SEC provenance, but
  no qualifying fresh directional family in that later evidence window;
  `launch_ready=false` and exit 1 were therefore correct.
- MSFT returned no canonical evidence and `launch_ready=false`; it is not in the
  currently reviewed GDELT/Bluesky alias registries.
- The local GDELT cache had not refreshed since 2026-07-14T23:09:59Z, confirming
  that automatic local refresh/catch-up and explicit freshness health remain
  implementation work.

These results distinguish a valid quiet/no-event response from a collector or
coverage gap; `launch_ready=false` alone is not a build defect.

## 2026-07-15 event-synthesis verification

The event-specific synthesis slice was verified against live RKLB primary-source
records after the implementation change:

- Form 144 accession `0001958244-26-000433` produced a “Proposed insider sale
  notice” with explicit language that proposed intent does not establish a
  completed disposition, plus a Form 4 follow-up check.
- 8-K accession `0001753926-26-001085` classified Item 1.01 as a material
  definitive agreement, surfaced Items 7.01 and 9.01, explained the contract
  relevance, and directed the user to the exact accession and exhibits.

These dated runs validate synthesis semantics, not investment performance or the
still-pending 20–30 real-case product gate.
