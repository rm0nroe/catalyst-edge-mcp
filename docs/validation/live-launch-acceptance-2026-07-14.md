# Live launch acceptance — 2026-07-14

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

## Production deployment handoff

Deploy the merged `main` commit above with the SEC identity and existing
collector settings supplied through the deployment secret store. Keep
conditional providers disabled until their rights approval is recorded. After
deployment, run the same smoke command against RKLB as a runtime check, while
treating a later exit 1 as a valid evidence-window outcome rather than a process
failure. Monitor GDELT timeout rates and preserve the current typed degradation
behavior.

This acceptance proves the required live provenance and directional-evidence
gate. It does not claim full five-family coverage, provider entitlement for
options/OHLC, or completion of the Bluesky collection window.
