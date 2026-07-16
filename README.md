# Catalyst Edge MCP

Catalyst Edge is a standalone, read-only MCP server that returns compact,
source-linked catalyst evidence dossiers for public-company tickers. It collects
independent evidence families concurrently and applies a documented deterministic
score. It does not import the sibling `analysis-api` application or its random-weight
model.

The public surface is one tool: `catalyst_edge_score`.

## Current status and completion boundary

As of 2026-07-15, the zero-subscription local runtime has the free dependencies
needed to deliver the revised product: direct SEC filings and insider records,
reviewed issuer feeds, GDELT Web NGrams discovery, and Bluesky partial attention.
The MCP transports, schemas, provenance, typed missingness, event graph, and
deterministic scorer are implemented and tested.

The first product-completion slice landed on 2026-07-15: evidence now carries
event type, materiality, novelty, correction lineage, source-record support, and
factual why-it-matters context. SEC 8-K item codes and insider transaction facts
drive event-specific headlines, invalidation criteria, and next checks. The slice
is covered by fixed real RKLB SEC metadata and was rechecked against live RKLB
Form 144 and 8-K records.

The automatic local GDELT lifecycle is now implemented: server startup schedules
a bounded catch-up when persisted state is due, periodic refresh remains outside
the MCP request path, shutdown cancels cleanly, and `catalyst-edge-health` reports
last-success age plus fresh, stale, failed, never-refreshed, or unregistered state.
Issuer feeds, discovery aliases, social aliases, and publisher-domain quality tiers
now load from one strictly validated local JSON registry. The packaged reviewed
defaults preserve the existing cohort; a custom path replaces that cohort rather
than silently merging unreviewed aliases.

The zero-subscription runtime meets its current local acceptance corpus as of
2026-07-16. A 25-case real SEC evaluation complements the 28 synthetic Phase 6
contract scenarios. It exposed and closed event-priority, merger-delisting, and
recorded Item 8.01 specificity defects; all recorded classification, provenance,
freshness, distinct-event, research-value, and dossier-direction checks pass.

Item 8.01 primary-document enrichment is intentionally bounded rather than a
general SEC semantic parser. The versioned `sec-primary-document-v1` rules cover
explicit completed debt offerings, entered or amended equity distribution
agreements, actual share-repurchase activity, and filed prospectus supplements.
They record the selected rule and version, reject proposed or negated near
matches, preserve amendment semantics, and leave multiple specific events
generic rather than choosing an arbitrary first match. Representative HTML,
table, and inline-XBRL fixtures exercise those boundaries. Unsupported wording
or filing structures remain `other_material_event` and require human review.

No numeric scorer change was justified because the real corpus contains no
forward-return labels. The scorer remains deterministic and explicitly
unbacktested. Paid options flow, licensed OHLC, sentiment, packaging, CI, hosted
deployment, consumer distribution, and broader SEC semantic extraction are
future capabilities, not blockers for the documented local acceptance boundary.

In older implementation notes and runtime messages, “production” means the
real non-fixture composition path used by the local MCP. It does not imply a
hosted service, third-party provider role, paid account, or consumer rollout.

## Install and verify

Python 3.10+ and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

All default tests are offline. Provider tests use sanitized fixtures and
`httpx.MockTransport`; live credentials are not required. Direct SEC event,
ownership, and Form 144 parsing plus issuer RSS/Atom collection and event-graph
behavior and GDELT Web NGrams discovery are implemented with fixed fixtures.
Official-host Bluesky partial-attention collection is also fixture-covered.
Phase 5 sentiment/options gates and 28 dated Phase 6 synthetic contract cases are also
executable offline.

The live Web NGrams replacement evidence is recorded in
[`docs/validation/gdelt-web-ngrams-live-2026-07-14.md`](docs/validation/gdelt-web-ngrams-live-2026-07-14.md).

## Source and provider configuration

| Evidence | Configuration | Behavior when absent |
| --- | --- | --- |
| Direct SEC filings/ownership | `CATALYST_EDGE_SEC_USER_AGENT="Company ops@example.com"` | Required local live-data baseline; missing identity blocks live collection |
| Reviewed issuer RSS/Atom | Built-in reviewed AAPL/NVDA registry; `CATALYST_EDGE_ISSUER_FEEDS=enabled` | Enabled by default; unregistered tickers make no feed request and return typed no-observation status |
| GDELT Web NGrams discovery | Built-in reviewed AAPL/NVDA/TSLA/RKLB/BRK-A/BRK-B aliases; `CATALYST_EDGE_GDELT=enabled` | Server lifespan runs bounded startup/periodic refresh out of band; request-time reads remain cache-only; metadata/links remain neutral and never receive launch-readiness credit |
| Bluesky partial attention | Reviewed exact aliases; `CATALYST_EDGE_BLUESKY=enabled` | Two complete historical seven-day windows are fetched from official AppView hosts; attention remains neutral |
| Mastodon attention | Reviewed-instance registry required | No instance is composed: measured representative coverage has not justified an allowlist |
| FMP and Finnhub | Key plus recorded policy approval | Keys alone do not establish commercial rights and are not composed by default |
| FlowAlgo/CheddarFlow/future OPRA vendor | Key plus recorded transaction-and-quote license | Otherwise `options_flow` is `licensed_feed_required` |
| User-supplied OHLC | Recorded provider/license approval | Otherwise `technical` is `licensed_feed_required` |
| Options selection | `CATALYST_EDGE_OPTIONS_PROVIDER=none\|auto\|flowalgo\|cheddarflow\|yfinance` | Defaults to `none`; yfinance is private diagnostic only and receives no scored evidence or coverage credit |
| Sentiment model | `CATALYST_EDGE_SENTIMENT_MODEL=disabled` | Must remain disabled: no audited candidate passes rights, Python, preprocessing, labeled-quality, rounding, and threshold gates |

Provider credentials are read only from this process environment. They are never
loaded from `../analysis-api`, logged, or returned in raw signals.

Copy the checked-in template, populate the SEC identity, then export it into the
current shell. Conditional provider keys are useful only after policy approval:

```bash
cp .env.example .env
# Edit .env without committing it, then:
set -a
source .env
set +a
uv run catalyst-edge-refresh-gdelt AAPL NVDA TSLA BRK.B RKLB --lookback-days 14
uv run catalyst-edge-health AAPL NVDA TSLA BRK.B RKLB
uv run catalyst-edge-smoke NVDA --lookback-days 14
```

The smoke command performs a secret-free configuration preflight before making any
provider request. Exit status `2` means configuration is missing or invalid; exit
status `1` means providers ran but live evidence did not satisfy readiness; exit
status `0` means the live provenance gate passed.

Runtime settings:

| Setting | Default | Notes |
| --- | --- | --- |
| `CATALYST_EDGE_TRANSPORT` | `stdio` | Also accepts `streamable-http` |
| `CATALYST_EDGE_HOST` | `127.0.0.1` | Loopback addresses only |
| `CATALYST_EDGE_PORT` | `8000` | Streamable HTTP port |
| `CATALYST_EDGE_ISSUER_FEEDS` | `enabled` | Set `disabled` to suppress issuer-feed requests |
| `CATALYST_EDGE_GDELT` | `enabled` | Enables cache-only request reads and automatic out-of-band startup/periodic refresh; set `disabled` for a fully disabled GDELT path |
| `CATALYST_EDGE_GDELT_REFRESH_SECONDS` | `300` | Period between bounded background attempts; 60–86,400 seconds |
| `CATALYST_EDGE_GDELT_LOOKBACK_DAYS` | `14` | Event-store reporting window used by each background refresh; 1–90 days |
| `CATALYST_EDGE_GDELT_MAX_AGE_SECONDS` | `900` | Last-success age after which request-time cache health becomes stale; must be at least the refresh interval |
| `CATALYST_EDGE_BLUESKY` | `enabled` | Set `disabled` to suppress AppView requests; disable all three public collectors for a fully offline runtime |
| `CATALYST_EDGE_REGISTRY_PATH` | Packaged `reviewed_registries.json` | Optional local JSON replacing the complete reviewed issuer/feed/discovery/social/publisher registry; invalid or ambiguous entries fail startup |
| `CATALYST_EDGE_EVIDENCE_STORE` | `~/.local/state/catalyst-edge-mcp/evidence.sqlite3` | Local SQLite/WAL collector state and canonical event graph |
| `CATALYST_EDGE_SENTIMENT_MODEL` | `disabled` | Any other value fails configuration until a reviewed candidate passes every gate |

The packaged registry currently contains Apple Newsroom and NVIDIA press-release
feeds on issuer-controlled hosts, plus the existing reviewed discovery/social cohort.
Tesla and Rocket Lab remain unregistered for issuer feeds because no official
RSS/Atom endpoint was confirmed. Copy
`catalyst_edge_mcp/data/reviewed_registries.json`, edit the copy, and set
`CATALYST_EDGE_REGISTRY_PATH` to use a local cohort. The loader rejects unknown
fields, duplicate ticker ownership, case-insensitive cross-issuer alias collisions,
noncanonical tickers, malformed CIKs, non-HTTPS feed URLs, and feed hosts absent
from the exact official-host allowlist. The adapter retains titles,
timestamps, identifiers, hashes, and links—not publisher bodies. Conditional ETag
and Last-Modified state is refreshed at ten-minute intervals. Exact fingerprints
run before same-issuer, 48-hour RapidFuzz matching at a token-set score of 92;
corrections and materially changed numbers become linked event versions. The local
store also snapshots the reviewed source-policy decisions used by collectors.

GDELT uses reviewed company aliases and the official downloadable Web NGrams feed at
`storage.googleapis.com/data.gdeltproject.org/gdeltv5/weblegacy/ngrams`. The legacy
DOC 2.0 endpoint now directs high-traffic callers to these files, so local MCP
requests remain cache-only while `catalyst-edge-refresh-gdelt` scans the newest
bounded minute index/TOC pairs out of band. Each pair is downloaded once and matched
against all requested issuers. Exact HTTPS host/path validation, compressed and
decompressed byte ceilings, a five-file run limit, and a 50-document per-issuer cap
bound the work. Only publisher titles, timestamps, domains, hashes, and HTTPS links
are retained; article bodies and ngram context are never stored. HTTP, timeout,
malformed schema, and missing-file states remain typed and preserve cached evidence.
Discovery observations merge into the same 48-hour canonical graph but remain below
SEC and issuer-primary sources in global ranking.

GDELT source quality is also registry-driven. Reviewed wire-service domains receive
`0.70`, reviewed financial-press domains `0.68`, reviewed release-distribution
domains `0.62`, and every unlisted domain the conservative `0.60` fallback. Matching
uses an exact hostname or dot-delimited subdomain boundary, so lookalike suffixes do
not inherit a tier. These remain discovery-quality heuristics to be checked during
the real-case evaluation; none changes GDELT's neutral direction or readiness credit.

When the MCP server starts, its lifespan coordinator reads persisted collector state.
Never-refreshed or due issuers receive one immediate bounded catch-up; a recent prior
attempt delays until the configured interval, preventing restart storms. Refreshes
then run serially at the configured cadence. The coordinator never runs inside
`catalyst_edge_score`, and shutdown cancels its task before closing the SQLite handle.
`catalyst-edge-health` is read-only and exits nonzero unless every requested reviewed
ticker is fresh.

Bluesky searches reviewed exact cashtags and company aliases through
`public.api.bsky.app`, falling back only to `api.bsky.app`. Both are documented,
unauthenticated AppView hosts; no proxy or scraper path exists. The collector
queries non-overlapping historical seven-day windows using documented `since`,
`until`, and cursor parameters. It fetches at most three 100-post pages per window,
deduplicates post URIs, counts unique authors, and persists derived window metrics
plus at most three representative links—not post bodies. Both windows must paginate
completely and contain at least five exact-match posts; otherwise no trend is emitted.
Attention direction always remains neutral. Mastodon remains uncomposed because no
reviewed instance set was available to establish representative cross-instance
coverage; no instance is treated as a global index.

Phase 5 reviewed Finnhub sentiment, TextBlob, VADER, DistilBERT SST-2, and
ProsusAI FinBERT. None passes every rights, input-data, compatibility,
preprocessing, labeled-quality, rounding, and threshold gate, so no sentiment
adapter is composed. FlowAlgo and CheddarFlow also remain uncomposed: public
terms do not grant the required automated extraction, storage, redistribution,
and derived-output rights. The local composition root therefore never calls an
options provider before policy evaluation. See
[`docs/audits/phase5-capability-gates-2026-07-13.md`](docs/audits/phase5-capability-gates-2026-07-13.md).

Phase 6 validates 28 dated, sanitized synthetic product-contract cases covering strong and
weak bullish evidence, bearish material events, neutral issuer/discovery items,
insider clusters, Form 144 intent, missing/stale/provider failures, Bluesky
historical warm-up/outage/sample regressions, contradictions, rejected sentiment, and
unlicensed options/technical missingness. All 28 expected-versus-produced
assertions pass. A separate 25-case real SEC product evaluation now covers the
primary-source gate. See
[`docs/validation/phase6-historical-validation-2026-07-13.md`](docs/validation/phase6-historical-validation-2026-07-13.md).

The real-case evaluation, semantic corrections, 370-test suite, live target
cohort, fresh GDELT health, and final RKLB `launch_ready=true` smoke are recorded
in [`docs/validation/real-catalyst-evaluation-2026-07-15.md`](docs/validation/real-catalyst-evaluation-2026-07-15.md)
and [`docs/validation/local-product-completion-2026-07-15.md`](docs/validation/local-product-completion-2026-07-15.md).

The live evidence-semantic launch gate passed for RKLB on 2026-07-14 from
merged `main`; the other four acceptance tickers correctly remained
fail-closed. See
[`docs/validation/live-launch-acceptance-2026-07-14.md`](docs/validation/live-launch-acceptance-2026-07-14.md).

## Run

Stdio:

```bash
uv run catalyst-edge-mcp
```

Local stateless streamable HTTP:

```bash
CATALYST_EDGE_TRANSPORT=streamable-http \
CATALYST_EDGE_PORT=8000 \
uv run catalyst-edge-mcp
```

Direct invocation uses the same real, non-fixture composition root:

```bash
uv run catalyst-edge-score NVDA --lookback-days 14 --risk-mode research
```

The opt-in live readiness check prints provider names, coverage, provenance status,
and sanitized warnings—never response payloads or credentials:

```bash
uv run catalyst-edge-smoke NVDA --lookback-days 14
```

Readiness requires SEC provenance plus a fresh directional direct-insider
observation, allowlisted material event, or explicitly authorized provider
observation. Provider names and keys alone do not qualify. yfinance, GDELT
discovery, attention-only social data, and missing/stale data receive no readiness
credit. A schema-valid no-data response demonstrates graceful failure only.

## Tool input

```json
{
  "ticker": "NVDA",
  "lookback_days": 14,
  "include_sources": true,
  "include_raw_signals": false,
  "risk_mode": "research"
}
```

Ticker validation runs before service composition. Unknown fields, unsafe strings,
non-boolean flags, and lookbacks outside 1–90 are rejected. `risk_mode` accepts
`research`, `alert_triage`, and `thesis_review`.

## Response example

The following shortened multi-provider example includes conditional vendor items
that assume explicit deployed policy approval. Production responses can contain up
to three items per family and 15 total.

```json
{
  "ticker": "NVDA",
  "as_of": "2026-07-12T16:00:00Z",
  "lookback_days": 14,
  "edge": {
    "score": 62,
    "direction": "bullish",
    "confidence": 0.69,
    "horizon_days": 5,
    "scoring_method": "deterministic_v1",
    "model_status": "not_trained"
  },
  "summary": {
    "headline": "Insider activity has the largest recent bullish contribution.",
    "what_changed": [
      "Net reported open-market insider value was 1500000 across 3 distinct insiders versus 100000.",
      "A new SEC 8-K was observed with item codes 2.02,9.01.",
      "Social mentions changed from 920 to 1410; sentiment changed by +0.180."
    ],
    "why_it_matters": "Source independence and agreement can strengthen confidence; missing families and lower-quality observations constrain it.",
    "what_would_invalidate": [
      "A primary filing or company record contradicts the normalized event.",
      "The reported insider cluster reverses in a subsequent equal window.",
      "Options activity normalizes during the requested horizon.",
      "A sector-wide event fully explains the ticker-specific observations."
    ]
  },
  "evidence": [
    {
      "family": "filings_news",
      "signal": "sec_form_8_k",
      "direction": "neutral",
      "strength": 0.8,
      "confidence": 0.98,
      "timestamp": "2026-07-11T00:00:00Z",
      "source_quality": 1.0,
      "change": {
        "description": "A new SEC 8-K was observed with item codes 2.02,9.01.",
        "current_value": null,
        "baseline_value": null,
        "delta": null,
        "unit": null,
        "comparison_window": null
      },
      "sources": [
        {
          "name": "SEC EDGAR",
          "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/nvda-8k.htm",
          "observed_at": "2026-07-11T00:00:00Z"
        }
      ],
      "notes": "SEC 8-K filing reports item codes 2.02,9.01.",
      "contribution": 0.0,
      "raw_signal": null,
      "source_count": 1
    },
    {
      "family": "insider_trading",
      "signal": "insider_purchase_strong_cluster",
      "direction": "bullish",
      "strength": 0.9,
      "confidence": 0.82,
      "timestamp": "2026-07-10T00:00:00Z",
      "source_quality": 1.0,
      "change": {
        "description": "Net reported open-market insider value was 1500000 across 3 distinct insiders versus 100000.",
        "current_value": 1500000.0,
        "baseline_value": 100000.0,
        "delta": 1400000.0,
        "unit": "USD reported value",
        "comparison_window": "current half vs preceding equal window"
      },
      "sources": [{"name": "SEC EDGAR", "source_id": "sec", "source_tier": "primary_regulator", "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/form4.xml", "canonical_url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/form4.xml", "accession_or_record_id": "0001045810-26-000101", "published_at": "2026-07-10T00:00:00Z", "observed_at": "2026-07-10T00:00:00Z", "retrieved_at": "2026-07-12T16:00:00Z", "raw_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "parser_version": "sec-ownership-v1", "policy_decision": "approved", "model_or_lexicon_revision": null, "related_sources": []}],
      "notes": "Only non-derivative open-market P/S transactions with disclosed shares and price are directional.",
      "contribution": 7.21,
      "raw_signal": null,
      "source_count": 1
    },
    {
      "family": "options_flow",
      "signal": "call_flow_increase",
      "direction": "bullish",
      "strength": 0.7,
      "confidence": 0.78,
      "timestamp": "2026-07-12T14:00:00Z",
      "source_quality": 0.85,
      "change": {
        "description": "Directional options premium changed from 400000 to 1250000; 6 sweep/block events were observed.",
        "current_value": 1250000.0,
        "baseline_value": 400000.0,
        "delta": 850000.0,
        "unit": "USD directional premium",
        "comparison_window": "current half vs preceding equal window"
      },
      "sources": [{"name": "flowalgo", "url": null, "observed_at": "2026-07-12T14:00:00Z"}],
      "notes": null,
      "contribution": 4.55,
      "raw_signal": null,
      "source_count": 1
    },
    {
      "family": "technical",
      "signal": "ema_12_crossed_above_26",
      "direction": "bullish",
      "strength": 0.65,
      "confidence": 0.75,
      "timestamp": "2026-07-12T00:00:00Z",
      "source_quality": 0.85,
      "change": {
        "description": "EMA spread transitioned from -0.20 to 0.35.",
        "current_value": 0.35,
        "baseline_value": -0.20,
        "delta": 0.55,
        "unit": "EMA spread",
        "comparison_window": "latest daily value vs prior daily value"
      },
      "sources": [{"name": "FMP technical indicator", "url": null, "observed_at": "2026-07-12T00:00:00Z"}],
      "notes": null,
      "contribution": 2.38,
      "raw_signal": null,
      "source_count": 1
    },
    {
      "family": "social",
      "signal": "social_sentiment_increase",
      "direction": "bullish",
      "strength": 0.55,
      "confidence": 0.72,
      "timestamp": "2026-07-12T12:00:00Z",
      "source_quality": 0.80,
      "change": {
        "description": "Social mentions changed from 920 to 1410; sentiment changed by +0.180.",
        "current_value": 1410.0,
        "baseline_value": 920.0,
        "delta": 490.0,
        "unit": "mentions",
        "comparison_window": "current half vs preceding equal window"
      },
      "sources": [{"name": "Finnhub social sentiment", "url": null, "observed_at": "2026-07-12T12:00:00Z"}],
      "notes": null,
      "contribution": 1.27,
      "raw_signal": null,
      "source_count": 1
    }
  ],
  "data_quality": {
    "coverage": "complete",
    "missing_families": [],
    "stale_families": [],
    "warnings": [
      "Deterministic v1 scoring is not backtested.",
      "This dossier does not provide an investment recommendation."
    ]
  },
  "next_checks": [
    "Verify the closest primary filing or company announcement.",
    "Check whether a sector-wide event explains the observation.",
    "Review timestamps, source independence, and comparison baselines."
  ]
}
```

## Private diagnostic and no-data behavior

yfinance may be selected explicitly for development/private diagnostics, but its
upstream data rights are not commercially cleared by the library. The default local
composition root does not call it. Isolated diagnostic code and fixtures grant no
evidence, canonical coverage, or readiness credit. It is never described as
smart-money or trade flow. Install diagnostic dependencies explicitly with
`uv sync --extra diagnostic`.

Private-yfinance diagnostic response example:

```json
{
  "ticker": "NVDA",
  "as_of": "2026-07-12T16:00:00Z",
  "lookback_days": 14,
  "edge": {
    "score": 50,
    "direction": "neutral",
    "confidence": 0.0,
    "horizon_days": 5,
    "scoring_method": "deterministic_v1",
    "model_status": "not_trained"
  },
  "summary": {
    "headline": "No fresh canonical catalyst evidence was available.",
    "what_changed": [],
    "why_it_matters": "Private diagnostic observations are excluded from production scoring.",
    "what_would_invalidate": [
      "A transaction-level options source contradicts the snapshot activity."
    ]
  },
  "evidence": [],
  "data_quality": {
    "coverage": "none",
    "missing_families": [
      "filings_news",
      "insider_trading",
      "options_flow",
      "social",
      "technical"
    ],
    "stale_families": [],
    "family_statuses": [
      {
        "family": "options_flow",
        "available": false,
        "status": "licensed_feed_required",
        "reason": "licensed_transaction_feed_required",
        "observed_at": null,
        "coverage_ratio": 0.0
      }
    ],
    "warnings": [
      "options_flow provider yfinance is private diagnostic only; no production evidence or coverage credit was granted.",
      "Overall confidence is below 0.50.",
      "Deterministic v1 scoring is not backtested.",
      "This dossier does not provide an investment recommendation."
    ]
  },
  "next_checks": [
    "Verify the closest primary filing or company announcement.",
    "Check whether a sector-wide event explains the observation.",
    "Review timestamps, source independence, and comparison baselines."
  ]
}
```

If every canonical family is absent, the response remains schema-valid with score
`50`, neutral direction, confidence `0`, `coverage="none"`, and all five canonical
families in `missing_families`. Provider failures, timeouts, stale evidence, missing
baselines, and low confidence are warnings; missingness never becomes bearish
evidence.

Full canonical no-data response example (including issuer feeds, GDELT, and Bluesky disabled):

```json
{
  "ticker": "NVDA",
  "as_of": "2026-07-12T16:00:00Z",
  "lookback_days": 14,
  "edge": {
    "score": 50,
    "direction": "neutral",
    "confidence": 0.0,
    "horizon_days": 5,
    "scoring_method": "deterministic_v1",
    "model_status": "not_trained"
  },
  "summary": {
    "headline": "No fresh canonical catalyst evidence was available.",
    "what_changed": [],
    "why_it_matters": "Missing evidence is uncertainty, not bearish evidence.",
    "what_would_invalidate": [
      "Fresh source-linked evidence from a canonical family becomes available."
    ]
  },
  "evidence": [],
  "data_quality": {
    "coverage": "none",
    "missing_families": [
      "filings_news",
      "insider_trading",
      "options_flow",
      "social",
      "technical"
    ],
    "stale_families": [],
    "warnings": [
      "No live evidence adapters are configured.",
      "Overall confidence is below 0.50.",
      "Deterministic v1 scoring is not backtested.",
      "This dossier does not provide an investment recommendation."
    ]
  },
  "next_checks": [
    "Verify the closest primary filing or company announcement.",
    "Check whether a sector-wide event explains the observation.",
    "Review timestamps, source independence, and comparison baselines."
  ]
}
```

## Scoring and data limitations

`deterministic_v1` weights normalized direction, strength, confidence, documented
source quality, and recency within fixed family budgets. Missing coverage reduces
directional conviction toward neutral. The score is not trained, calibrated, or
backtested and makes no expected-return claim. Every response exposes
`model_status="not_trained"`, states the backtesting limitation, and states that no
investment recommendation is provided.

Raw signals are excluded by default. When explicitly requested, a recursive redactor
removes credential and identity-like fields, bounds containers and strings, and caps
each serialized raw item at 8 KiB.

See [TDD.md](TDD.md) for exact formulas, provider contracts, compactness rules, and
the Flask migration design that intentionally remains outside this repository.
