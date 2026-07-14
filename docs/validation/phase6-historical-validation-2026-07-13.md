# Phase 6 historical product validation — 2026-07-13

## Result

All 28 dated cases matched their expected provenance, aggregate direction,
missingness, staleness, SEC-provenance flag, and launch-readiness result.

The cases are sanitized product-contract scenarios with synthetic tickers. They
do not assert that an event occurred for a real issuer and do not use later price
performance or hindsight labels. Each case supplies only evidence available at
its `as_of` timestamp. The executable source is
`tests/fixtures/validation/phase6_historical_cases.json`; verification is
`FX_PHASE6_HISTORICAL_PRODUCT_CASES`.

Summary: 28/28 passed; six bullish, three bearish, and 19 neutral aggregate
directions; 14 cases retained SEC provenance; 11 passed the evidence-semantic
launch-readiness gate. Readiness can pass when the aggregate score remains
neutral if a fresh qualifying directional observation exists, as designed in
the weak-observation and contradiction cases.

In the table, `E→P` means expected to produced; identical sets are shown once.

| Case | Score | Direction E→P | Missing families E=P | Stale E=P | Source IDs E=P | SEC E→P | Ready E→P |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| 01 strong bullish multi-source | 68 | bullish→bullish | options, social, technical | none | SEC | true→true | true→true |
| 02 weak bullish observation | 53 | neutral→neutral | filings, options, social, technical | none | SEC | true→true | true→true |
| 03 bearish material filing | 40 | bearish→bearish | insider, options, social, technical | none | SEC | true→true | true→true |
| 04 neutral issuer release | 50 | neutral→neutral | insider, options, social, technical | none | issuer feed | false→false | false→false |
| 05 neutral discovery metadata | 50 | neutral→neutral | insider, options, social, technical | none | GDELT | false→false | false→false |
| 06 two-insider cluster | 55 | bullish→bullish | filings, options, social, technical | none | SEC | true→true | true→true |
| 07 three-insider strong cluster | 57 | bullish→bullish | filings, options, social, technical | none | SEC | true→true | true→true |
| 08 reported insider sale | 44 | bearish→bearish | filings, options, social, technical | none | SEC | true→true | true→true |
| 09 Form 144 proposed intent | 50 | neutral→neutral | filings, options, social, technical | none | SEC | true→true | false→false |
| 10 material event, insider missing | 58 | bullish→bullish | insider, options, social, technical | none | SEC | true→true | true→true |
| 11 stale options observation | 50 | neutral→neutral | all five | options | none | false→false | false→false |
| 12 technical provider timeout | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 13 primary provider schema error | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 14 social rate limited | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 15 Bluesky warm-up | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 16 Bluesky collector outage | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 17 Bluesky sample insufficient | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 18 equal primary contradiction | 50 | neutral→neutral | insider, options, social, technical | none | SEC | true→true | true→true |
| 19 unlicensed options rejected | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 20 yfinance diagnostic rejected | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 21 technical license missing | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 22 attention only with SEC provenance | 50 | neutral→neutral | insider, options, technical | none | Bluesky, SEC | true→true | false→false |
| 23 sentiment candidate disabled | 50 | neutral→neutral | insider, options, social, technical | none | SEC | true→true | false→false |
| 24 no data | 50 | neutral→neutral | all five | none | none | false→false | false→false |
| 25 strong bearish multi-family | 30 | bearish→bearish | options, social, technical | none | SEC | true→true | true→true |
| 26 issuer material event plus SEC baseline | 58 | bullish→bullish | insider, options, social, technical | none | issuer feed, SEC | true→true | true→true |
| 27 stale primary event | 50 | neutral→neutral | all five | filings | none | false→false | false→false |
| 28 hypothetical authorized options contract | 56 | bullish→bullish | insider, social, technical | none | authorized fixture, SEC | true→true | true→true |

Case 28 verifies the contract boundary only: a hypothetical provider passes when
an `approved` entitlement is explicitly present. It does not claim any current
options provider has that approval; Phase 5 records that none does.

## Package and runtime verification

Executed from the untracked `implement/scorer-complete` worktree on
2026-07-13 America/New_York:

- `uv sync --extra dev` completed from the locked dependency graph. yfinance and
  its transitive packages are absent unless `--extra diagnostic` is requested.
- `uv run pytest -q`: 259 passed, including the nine stdio/streamable-HTTP MCP
  contract tests and all 28 Phase 6 cases.
- `uv run ruff check .`: passed.
- `uv build`: source distribution and wheel built successfully. Inspection
  confirmed the Phase 3–5 adapters, registries, capability gates, and audit
  reports are packaged.
- Disabled-collector stdio startup with immediate EOF exited cleanly.
- Sanitized live `catalyst-edge-smoke NVDA --lookback-days 14`: configuration
  ready, partial coverage, SEC provenance present, no qualifying directional
  family, and `launch_ready=false` with exit 1. GDELT returned no publisher
  links, Bluesky remained in its 14-day warm-up, options stayed
  `licensed_feed_required`, sentiment stayed disabled, and no readiness was
  fabricated.

The live outcome proves safe runtime behavior but is not a launch-readiness
pass. A future live run still needs SEC provenance plus a qualifying fresh
directional observation.
