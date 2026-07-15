# Catalyst Edge MCP — PRD-Complete Technical Design

**Revision:** Phases 0–6 implementation and product validation, 2026-07-13

## 1. Scope, outcome, and fixed decisions

This document is the implementation design for the complete `PRD.md`. The
deliverable is a standalone, read-only MCP server in this repository exposing
one tool, `catalyst_edge_score`. Completion means the tool can return a compact,
source-linked catalyst dossier backed by legally usable evidence, with explicit
missingness for unavailable families. A schema-valid no-data result is required
failure behavior, but is not sufficient for product acceptance. Product launch
requires SEC provenance and at least one fresh directional observation whose
semantics, not provider name, satisfy the readiness rule in §14.

The sibling `../analysis-api` repository is reference code only. Pure
normalization and scoring ideas may be adapted, but its Flask application,
MongoDB initialization, caches, AI helpers, and random-weight
`CCEModelManager` must never be imported by this package.

Fixed decisions:

- Python 3.10+, Pydantic v2, and official MCP Python SDK stable v1
  (`mcp>=1.27,<2`).
- FastMCP with verified local stdio and local streamable HTTP transports.
- Deterministic scoring only: `scoring_method=deterministic_v1` and
  `model_status=not_trained`.
- The production baseline is direct SEC data, reviewed issuer feeds, GDELT
  discovery metadata, Bluesky AppView, and reviewed Mastodon instances. Each
  non-SEC source remains constrained by the source-policy registry in §6.
- FMP, Finnhub, Reddit, Stocktwits, OCC, and any options vendor are conditional:
  credentials alone never prove commercial authorization. Their adapters may
  run in production only after an explicit policy decision records the needed
  permission or license.
- True `options_flow` requires a licensed transaction-plus-quote source.
  yfinance is development/private diagnostic data only and never supplies
  production evidence, canonical coverage, or launch-readiness credit.
- Five canonical families are always expected: `filings_news`,
  `insider_trading`, `options_flow`, `technical`, and `social`.
  `alternative` is optional.
- `technical` requires a user-supplied/licensed OHLC source or typed neutral
  missingness; this TDD does not claim a cleared zero-subscription OHLC source.
- MediaCrawler, ai-berkshire, trained/calibrated scoring, licensed options flow,
  and execution of the sibling Flask migration remain future/conditional items.

## 2. Package architecture and entrypoints

The implementation is split by responsibility rather than by provider runtime:

```text
catalyst_edge_mcp/
  models.py                 # public and internal Pydantic schemas
  source_policy.py          # reviewed rights, quality, rate, and host policy
  evidence_store.py         # SQLite/WAL observations and collector state
  validation.py             # secure input validation
  redaction.py              # recursive raw-payload protection
  adapters/
    base.py                 # adapter protocol and common client behavior
    sec.py                  # SEC filings, ownership XML, and Form 144
    issuer_feeds.py         # reviewed issuer RSS/Atom feeds
    gdelt.py                # serialized discovery metadata
    bluesky.py              # partial social-attention sample
    mastodon.py             # optional reviewed-instance attention
    authorized.py           # explicitly authorized vendor adapters
    options.py              # licensed flow or private diagnostic only
  scorer.py                 # scorer protocol and deterministic_v1
  summary.py                # mode-aware, template-based synthesis
  service.py                # orchestration and data-quality evaluation
  server.py                 # FastMCP registration and transports
  cli.py                    # direct local invocation and live smoke command
tests/
  fixtures/providers/       # sanitized provider responses
  fixtures/dossiers/        # deterministic scenario fixtures
  unit/
  contract/
  integration/
```

Installed commands:

- `catalyst-edge-mcp`: start stdio unless
  `CATALYST_EDGE_TRANSPORT=streamable-http` is set.
- `catalyst-edge-score TICKER`: invoke the same service and print JSON.
- `catalyst-edge-smoke TICKER`: opt-in live credential/provenance check; it
  prints provider status but never raw payloads or credentials.

`build_service(settings)` is the only production composition root. Tests inject
adapters, scorer, settings, clock, and HTTP transports without environment or
network access.

## 3. Public tool contract

FastMCP derives JSON Schema from the annotated function and returns structured
Pydantic output. The PRD inputs remain unchanged:

```json
{
  "ticker": "NVDA",
  "lookback_days": 14,
  "include_sources": true,
  "include_raw_signals": false,
  "risk_mode": "research"
}
```

Validation occurs before adapter construction or invocation:

- `ticker`: trim, uppercase, and require `^[A-Z][A-Z0-9.-]{0,11}$`; reject
  control characters, HTML, path separators, whitespace within the symbol,
  SQL comment forms (`--`, `/*...*/`), the tautology pattern `or 1=1`, and the
  case-insensitive substrings `script`, `exec`, `union`, `select`, `drop`,
  `delete`, `insert`, and `update`, matching the sibling secure validator.
- `lookback_days`: integer, default 14, inclusive range 1–90.
- `include_sources`: boolean, default true.
- `include_raw_signals`: boolean, default false.
- `risk_mode`: `research`, `alert_triage`, or `thesis_review`.
- Unknown input fields are rejected.

The response preserves every PRD field: `ticker`, `as_of`, `lookback_days`,
`edge`, `summary`, `evidence`, `data_quality`, and `next_checks`. Existing
evidence extensions are formalized: `direction`, `source_quality`, and signed
`contribution`. `data_quality.family_statuses` exposes one status per canonical
family, including `available`, `status`, `reason`, `observed_at`, and
`coverage_ratio`. Evidence also gains an optional `change` object:

```json
{
  "description": "Mention volume increased 42% versus the prior 7-day window.",
  "current_value": 1840.0,
  "baseline_value": 1296.0,
  "delta": 544.0,
  "unit": "mentions",
  "comparison_window": "current 7 days vs prior 7 days"
}
```

`current_value`, `baseline_value`, and `delta` are nullable finite numbers.
`description` is required and bounded to 240 characters; `unit` to 40; and
`comparison_window` to 80. Event evidence uses a description with null numeric
fields. Metric evidence must include both current and baseline values or emit a
`baseline_unavailable` warning and leave `change` absent.

Unavailable options are represented explicitly and never as evidence:

```json
{
  "family": "options_flow",
  "available": false,
  "status": "licensed_feed_required",
  "reason": "licensed_transaction_feed_required",
  "observed_at": null,
  "coverage_ratio": 0.0
}
```

The same shape expresses `technical` missingness and incomplete social windows,
permission, rate-limit, or outage states. A status object is data quality, not
a bullish or bearish signal, and cannot enter the scoring evidence list.

## 4. Internal interfaces and canonical-family policy

```python
class CatalystSignalAdapter(Protocol):
    family: str
    provider: str
    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult: ...

class CatalystScorer(Protocol):
    method: str
    model_status: str
    def score(self, evidence, *, as_of, lookback_days, expected_families): ...
```

`AdapterResult` contains:

- `family`: normalized family name;
- `provider`: stable provider identifier;
- `evidence`: normalized evidence items;
- `warnings`: sanitized provider/family warnings;
- `status`: one typed status from `fresh`, `no_observations`, `stale`,
  `rate_limited`, `permission_required`, `licensed_feed_required`, `timeout`,
  `schema_error`, or `unavailable`;
- `policy_decision`: the policy registry decision used for this collection;
- `degraded`: whether a fallback or incomplete provider result was used;
- `collected_at`: UTC collection completion time.

Multiple adapters may contribute to one family. SEC filings and FMP news, for
example, produce separate `AdapterResult` values for `filings_news`; scoring
aggregates them under the single family budget.

Canonical expected families are a constant, not derived from registered
adapters:

```text
filings_news, insider_trading, options_flow, technical, social
```

An unconfigured, permission-blocked, license-blocked, failed, timed-out, empty,
or wholly stale canonical family is always included in `missing_families` and
has a typed `family_status`. Missingness contributes zero directional evidence.
Optional `alternative` evidence can increase confirmation but never determines
whether coverage is complete.

## 5. Evidence, provenance, and change normalization

Each `Evidence` contains:

- `family`, stable `signal`, and `direction` (`bullish`, `bearish`, `neutral`);
- `strength`, `confidence`, and `source_quality` in `[0, 1]`;
- UTC `timestamp` and optional `change`;
- zero or more provenance-complete `Source` records;
- optional bounded `notes` and opt-in `raw_signal`;
- scorer-populated signed `contribution` and derived `source_count`.

Each `Source` provenance envelope contains stable `source_id`, `source_tier`,
display `name`, original `url`, `canonical_url`, optional accession/record ID,
`published_at`, `observed_at`, `retrieved_at`, optional raw SHA-256, parser
version, policy decision, optional model/lexicon revision, and bounded
`related_sources`. Publisher or social bodies are not retained merely because
an endpoint is public. SEC evidence stores parsed facts, identifiers, hashes,
and links rather than indiscriminately redistributing full filing text.

Source URLs must be returned directly by the source or constructed from a
documented official URL scheme. Adapters must not invent article or filing
URLs. Duplicate evidence is removed using `(family, signal, timestamp,
canonical_source_url)` before scoring.

Provider source-quality constants are deterministic and documented rather than
inferred dynamically:

| Source | Quality | Reason |
| --- | ---: | --- |
| SEC filing/ownership record | 1.00 | Primary regulator record |
| Reviewed issuer IR release | 0.95 | Issuer primary disclosure |
| Explicitly authorized licensed provider | policy-specific, max 0.90 | Written rights and field semantics required |
| GDELT-discovered publisher metadata | 0.60–0.70 | Discovery only; domain tier constrains quality |
| Bluesky attention | 0.50–0.60 | Ranked, incomplete public attention sample |
| Reviewed Mastodon attention | 0.40–0.50 | Instance-scoped partial sample |
| Options without licensed trades plus quotes | none | No production proxy quality constant |
| yfinance chain snapshot | none | Development/private diagnostic; no production credit |

Change rules are family-specific:

- Events/filings: describe the newly observed form, item, or company event.
  Direction remains neutral unless an allowlisted event mapping supports it
  (for example bankruptcy, delisting, or restatement is bearish). No headline
  keyword model may invent direction.
- Insider: parse direct SEC Forms 3/4/5 transaction codes, holdings, ownership
  form, footnotes, and 10b5-1 context. Open-market purchase code `P` may be
  bullish with disclosed price/value. Sale code `S` uses lower confidence.
  Grants, exercises, gifts, tax withholding, conversions, and derivative moves
  are not discretionary open-market trades. Two distinct same-direction
  insiders form `cluster`; three or more form `strong_cluster`. Form 144 is
  proposed intent, never completed execution.
- True options flow: only a commercially authorized transaction-plus-quote
  source can set `options_flow.available=true`. Directional premium and
  sweep/block/aggressor labels must remain derived and auditable. Chain
  snapshots and OCC aggregates cannot create `options_flow` evidence.
- Technical: compare the latest and prior daily values for RSI-14, SMA-20,
  EMA-12, and EMA-26. Only crossovers or threshold transitions create evidence;
  static levels do not.
- Social attention: exact cashtag/reviewed-alias matches, unique authors,
  deduplicated posts, and two non-overlapping historical seven-day windows. It is
  always source-scoped and never called market-wide sentiment. No trend is
  emitted unless both cursor-bounded windows complete and meet the minimum sample
  threshold. Upstream failure or pagination truncation cannot look bearish.
- Social sentiment: separate optional evidence, disabled by default. It may
  influence scoring only after fixed preprocessing, labeled accuracy and
  compatibility gates, explicit model/lexicon rights, rounded outputs, and
  fixed thresholds. Attention alone remains neutral.
- Alternative lobbying: compare filing/activity counts with the preceding
  equal window and remain neutral unless the source explicitly supplies a
  supported direction. It is never a canonical-family substitute.

## 6. Provider implementation and configuration

All credentials live in this repository's process environment. They are never
read from, copied from, or logged out of `../analysis-api/.env*`.

The source-policy registry is fail-closed and reviewed in code. Every entry
records `source_id`, allowed families, tier, policy decision, commercial-use
note, content-retention rule, quality range, rate/concurrency limit, official
hosts, and review date. A key or reachable endpoint cannot override policy.

| Source | Policy decision | Production behavior |
| --- | --- | --- |
| SEC submissions/archive, Forms 3/4/5/144, 8-K/6-K | `approved` | Required baseline; identifying user agent; parsed facts/hashes/links |
| Reviewed issuer RSS/Atom | `approved_per_registry` | Only reviewed feeds/terms; metadata and factual extraction by default |
| GDELT Web NGrams/TOC | `approved_discovery` | Official downloadable index plus article metadata/links only; discovery never outranks primary evidence |
| Bluesky AppView | `approved_partial_attention` | Minimal post metadata/derived buckets; deletion/takedown honored |
| Reviewed Mastodon instance | `approved_per_registry` | Instance-scoped partial attention only |
| FMP/Finnhub/Reddit/Stocktwits/OCC | `permission_required` | Disabled until written rights are recorded |
| OPRA-derived options vendor | `licensed_feed_required` | Enabled only after non-display/storage/output rights and fields are approved |
| User-supplied OHLC provider | `licensed_feed_required` | Enables `technical` only after recorded rights |
| yfinance | `development_private_only` | Explicit private diagnostic mode; never production evidence/coverage |

Baseline contracts:

- SEC: resolve ticker to CIK, use real-time submissions metadata, then fetch
  ownership/Form 144/8-K/6-K archive documents by accession. Production uses
  existing async `httpx`; `lxml` performs namespace-safe local parsing.
  EdgarTools is optional offline fixture/backfill validation, not request-path
  transport. Requests run at two starts/second and concurrency two, below the
  SEC ceiling. Form 144 remains proposed intent.
- Issuer feeds: a reviewed registry defines canonical feeds and aliases.
  Collect with conditional `ETag`/`Last-Modified` requests every 5–15 minutes;
  broken feeds become `stale`, not “no news.”
- GDELT: request-time evaluation is cache-only. The explicit background refresh
  command downloads the newest bounded Web NGrams index/TOC pairs from the official
  `storage.googleapis.com/data.gdeltproject.org/gdeltv5/weblegacy/ngrams` path,
  matches all reviewed issuers in one pass, and stores publisher metadata/links
  rather than article bodies or ngram context. Exact host/path validation, byte
  ceilings, a five-file run limit, and per-issuer document caps bound the collector.
- Bluesky: search exact cashtags/reviewed aliases through the documented
  `public.api.bsky.app` AppView host, then the documented `api.bsky.app`
  fallback. Reads are unauthenticated. Never use proxies or scraping to bypass
  reachability. Returned headers control backoff.
- Mastodon: only reviewed instances are queried; returned limits and instance
  policy control behavior. No instance is treated as a global index.

Conditional provider adapters must carry an `approved` policy decision bound to
the deployed account/plan. FMP/Finnhub credentials without that decision return
`permission_required`. Options providers without recorded transaction-plus-
quote entitlements return `licensed_feed_required`. OCC or chain data may later
use a distinct `options_eod_activity` diagnostic family but never
`options_flow`. `CATALYST_EDGE_OPTIONS_PROVIDER` defaults to `none`; selecting
`yfinance` is valid only in explicit private diagnostic mode.

Request-time provider clients use a six-second request timeout and the service
applies an eight-second outer timeout. GDELT is never refreshed on that path; its
explicit background command has a 30-second per-file upstream budget. Broad collection
runs outside request latency. There are no unbounded retries. `429`, permission,
license, schema, network, and timeout failures map to typed statuses and cached
partial results with freshness. Cancellation always propagates.

The evidence store uses SQLite/WAL tables for `source_observation`,
`canonical_event`, `event_source`, `insider_transaction`, `insider_cluster`,
`social_bucket`, `collector_state`, and `source_policy`. Event deduplication
normalizes issuer/CIK and canonical URLs, uses exact fingerprints first, then a
48-hour same-issuer RapidFuzz token-set threshold of `>=92`. Corrections and
materially changed numbers are linked versions, not discarded duplicates.

No browser crawler, residential proxy, CAPTCHA solver, cookie farm, credential
rotation, or undocumented endpoint is part of this product. Schema drift fails
closed; adapters never guess replacement fields or paths during a tool call.

## 7. Recursive raw-signal protection

Raw data is excluded unless `include_raw_signals=true`. Before any raw value is
stored in evidence, logged, truncated, or returned, a shared redactor walks it
recursively and removes dictionary fields whose normalized names contain:

```text
secret, token, api_key, apikey, authorization, cookie, password,
email, user_id, userid, account_id, accountid
```

The redactor allows at most five nesting levels, 50 dictionary keys per object,
50 list items, and 1,000 characters per string. After redaction, serialized
JSON is capped at 8 KiB per evidence item; overflow becomes a bounded preview
plus `truncated=true`. Logs may contain only ticker, family, provider, status,
duration, evidence count, and sanitized error class—never raw response bodies,
request headers, query-string credentials, or redacted previews.

## 8. Orchestration, freshness, and data quality

The fixed request pipeline is:

```text
validate input
  -> construct canonical adapters from settings
  -> collect providers concurrently
  -> redact and normalize
  -> deduplicate
  -> enforce freshness and baseline rules
  -> calculate family/data-quality warnings
  -> score deterministic evidence
  -> generate mode-aware summary
  -> apply compactness/source/raw options
  -> validate final response schema
```

Evidence older than `as_of - lookback_days` is excluded and its family is added
to `stale_families`. A family with some fresh and some stale evidence is not
missing, but receives a stale warning. A canonical family with no fresh
evidence is both stale (when applicable) and missing.

Warnings are required for:

- every absent canonical family and affected provider;
- every `permission_required` or `licensed_feed_required` policy block;
- incomplete social windows, sample insufficiency, and collector coverage gaps;
- stale evidence;
- each provider failure or timeout;
- degraded provider use;
- missing comparison baseline;
- each evidence item with confidence `<0.50` (one bounded family warning);
- overall confidence `<0.50`;
- deterministic scoring not being backtested;
- no investment recommendation being provided.

Coverage is:

- `none`: no fresh evidence from any canonical family;
- `partial`: at least one but fewer than all five canonical families has fresh
  evidence;
- `complete`: all five canonical families have fresh evidence, regardless of
  optional alternative-data availability.

`family_statuses` always contains all five canonical families. Fresh evidence
sets `available=true` and `status=fresh`. Otherwise the highest-information
status wins in this order: `permission_required`, `licensed_feed_required`,
`rate_limited`, `timeout`, `schema_error`, `stale`, `no_observations`, then
`unavailable`. Social coverage ratios include collector downtime. No typed
missingness object is converted into evidence.

## 9. Deterministic scoring

Family point budgets remain:

| Family | Maximum absolute points |
| --- | ---: |
| `filings_news` | 16 |
| `insider_trading` | 12 |
| `options_flow` | 10 |
| `technical` | 6 |
| `social` | 4 |
| `alternative` | 4 |
| unknown | 3 |

For item `i`:

```text
polarity_i = +1 bullish, -1 bearish, 0 neutral
age_days_i = max(0, (as_of - timestamp_i) / 86400 seconds)
recency_i = max(0, 1 - age_days_i / lookback_days)
raw_i = polarity_i * strength_i * confidence_i * source_quality_i * recency_i
raw_family = sum(raw_i for items in family)
bounded_family = clamp(raw_family, -1, 1)
family_points = family_weight * bounded_family
```

Mixed-direction item attribution must preserve opposing evidence and sum
exactly to the bounded family result:

```text
if raw_family == 0:
    attribution_scale = family_weight
else:
    attribution_scale = family_points / raw_family
item_contribution_i = raw_i * attribution_scale
sum(item_contribution_i) == family_points
```

Missingness never becomes bearish evidence. It pulls directional conviction
toward neutral:

```text
missing_high_value = missing among {filings_news, insider_trading}
missing_other = missing among {options_flow, technical, social}
coverage_factor = max(0.60,
  1 - 0.15 * missing_high_value - 0.05 * missing_other)
score = round(clamp(50 + sum(family_points) * coverage_factor, 0, 100))
```

Direction is bullish at `score >= 55`, bearish at `score <= 45`, and neutral
otherwise. Horizon is five days.

Confidence is independent of direction:

```text
evidence_quality = strength-weighted mean(confidence * source_quality)
coverage = observed canonical families / 5
confirmation = min(1, observed non-neutral families / 3)
confidence = min(0.95,
  evidence_quality * (0.55 + 0.25 * coverage + 0.20 * confirmation))
```

`permission_required`, `licensed_feed_required`, private yfinance diagnostics,
social warm-up/outage, and technical missingness contribute exactly zero raw
and family points. Private diagnostic observations are excluded before scoring,
not merely down-weighted.

No evidence returns score 50, neutral direction, and confidence 0. A future
calibrated scorer must implement `CatalystScorer` and use a different method and
model status; it cannot silently replace `deterministic_v1`.

## 10. Summary, invalidation, compactness, and language

Summaries are deterministic templates using `Evidence.change.description`,
ranked contribution, source independence, missing families, and warnings. They
must not derive prose by merely replacing underscores in signal identifiers.

- `research`: balance supporting and contradicting evidence, provenance, and
  confidence limitations.
- `alert_triage`: lead with the newest material change, its timestamp, why it
  may warrant review, and the fastest primary-source check.
- `thesis_review`: identify evidence capable of changing a prior thesis,
  contradictory evidence, and explicit invalidation checks.

Invalidation checks are family-aware: primary filing contradiction, insider
cluster reversal, options normalization, technical crossover reversal, social
attention/sentiment normalization, and sector-wide explanation. They may only
reference families present in the response or explicitly identify a missing
confirmation check.

Compactness limits are three evidence items per family, 15 total evidence
items, three sources per evidence item, five `what_changed` entries, five
invalidation checks, 20 warnings, and five next checks. Evidence is selected by
absolute contribution, then recency; at least one contradictory item is kept
when available. `include_sources=false` empties source arrays and recomputes
`source_count=0`. Raw data remains absent unless explicitly requested.

Generated summary and next-check text must not contain transaction
instructions, “buy,” “sell,” “guaranteed,” “alpha,” expected-return claims, or
personalized investment advice. Every response states that scoring is
unbacktested and no investment recommendation is provided.

## 11. Flask route migration design (execution outside this repository)

The PRD explicitly keeps migration of
`../analysis-api/trading/api/cce_routes.py` outside this standalone
implementation. The migration is nevertheless decision-complete:

1. Publish this package as a pinned internal dependency; do not make the Flask
   process call MCP over a loopback network.
2. Add a compatibility mapper from `CatalystEdgeResponse` to the existing
   camelCase route fields while also returning the new evidence dossier.
3. Replace `DataIngestionOrchestrator`, `FeatureEngineering`, and
   `CCEModelManager.predict_edge_score` calls with `CatalystService.evaluate`.
4. Preserve `require_tier`, tier rate limits, secure ticker validation, cache
   TTL, HTTP status/error mapping, and database writes needed by existing
   consumers. Never persist raw provider payloads unless redacted.
5. Add contract tests comparing cached and uncached legacy response keys,
   authentication failures, rate limits, partial provider failure, and the new
   deterministic method/model fields.
6. Roll out behind `CCE_USE_CATALYST_EDGE`; shadow-compare responses without
   exposing the random score, then enable the new path. Rollback is disabling
   the flag; the old model must not be re-presented as trusted.

## 12. Runtime delivery and hosted-service boundary

Stdio and local streamable HTTP are required and contract-tested. Streamable
HTTP uses stateless mode and JSON responses. Default bind is loopback only;
host and port are explicit configuration. The package does not include a cloud
deployment.

Before any future non-loopback or hosted deployment, the host must add OAuth
2.1 or equivalent service authentication, per-principal rate limits, request
size limits, TLS, structured secret-free logs, `/health/live` and
`/health/ready` checks, provider circuit-breaker metrics, and an allowlist for
origins/network exposure. These controls are deployment prerequisites, not
silent defaults in the local server.

## 13. Implementation sequence

Implementation status on 2026-07-13: Phases 0 through 6 are implemented and
covered by offline contract/parser fixtures. Phase 1 was live-validated against
representative SEC Forms 4/144 and 8-K archive metadata. Phase 2 was live-validated
against the reviewed Apple and NVIDIA issuer feeds, including conditional state.
Phase 3 has bounded success/empty/malformed/rate-limit/timeout/host/provenance
fixtures. Repeated live request-path timeouts moved DOC refreshes into an explicit
out-of-band command; MCP evaluation now reads the typed cache without response-body
retention.
Phase 4 uses only the two documented Bluesky AppView hosts, persists derived
attention windows without post bodies, enforces complete pagination and sample gates,
and keeps attention neutral. No Mastodon instance registry is composed because the
review found no approved instance set from which representative cross-instance
coverage could be established. The live Bluesky POC confirmed the current 403 on
the cached public search host and successful unauthenticated direct-AppView fallback.
Phase 5 records immutable fail-closed audits for five sentiment candidates and
four options candidates. No candidate passes every required gate, so sentiment
and options remain uncomposed; production makes no rejected-provider request.
Phase 6 executes 28 dated, sanitized product cases. All expected-versus-produced
direction, provenance, missingness, staleness, and readiness assertions pass.

0. Revise this design and contracts: source policy, provenance, typed statuses,
   quality constants, evidence-semantic readiness, neutral missingness, and
   red tests/fixtures. Do not claim collector implementation from this phase.
1. Implement direct SEC insiders and events using async `httpx` plus `lxml`;
   use EdgarTools only for offline cross-checks. Preserve two-insider clusters,
   distinguish three-plus strong clusters, and keep Form 144 as proposed intent.
2. Implemented: reviewed issuer RSS/Atom feeds, conditional retrieval, canonical
   event graph, exact/fuzzy dedupe, correction versioning, and primary-source ranking.
3. Implemented: request-time GDELT cache reads plus batch out-of-band discovery from
   official Web NGrams index/TOC files, reviewed issuer aliases, metadata-only
   retention, bounded file processing, cached typed degradation, and canonical-event
   integration. The legacy DOC endpoint is no longer used by the refresh command.
4. Implemented: Bluesky exact-match partial attention with cached-to-direct official
   AppView fallback, two bounded historical windows, complete pagination, minimum
   samples, failure-aware coverage, and neutral semantics. Mastodon remains
   uncomposed after the measured allowlist decision found no reviewed instance
   set for representative coverage.
5. Implemented: audited Finnhub sentiment, TextBlob, VADER, DistilBERT SST-2,
   and ProsusAI FinBERT against rights, Python, preprocessing, labeled-quality,
   rounding, and threshold gates. Audited FlowAlgo, CheddarFlow, a future OPRA
   vendor, and yfinance against transaction-plus-quote and entitlement gates.
   None passes; all remain disabled and uncomposed.
6. Implemented: 28 dated sanitized cases cover directional strength, primary
   and discovery provenance, insider clusters, Form 144, missing/stale/provider
   failures, Bluesky historical warm-up/outage/sample regressions, contradictions, rejected
   sentiment, and options/technical entitlement boundaries. All assertions pass;
   package/runtime verification outcomes are recorded in the Phase 6 report.

No phase is called complete while its mapped PRD tests in the traceability
matrix fail or are absent.

## 14. Test, documentation, and launch acceptance

All default tests run without network access or live keys using sanitized JSON
fixtures or `httpx.MockTransport`. Provider normalization tests cover success,
empty data, malformed schema, authentication failure, rate limit, timeout, and
provenance. Secrets and real response cassettes are never committed.

Required deterministic dossier scenarios:

- strong multi-source bullish catalyst;
- weak single-source social-only catalyst;
- bearish filing/news catalyst;
- missing insider data;
- stale options data;
- collector timeout and provider exception;
- invalid ticker and parameter bounds;
- mixed bullish/bearish family attribution;
- evidence and overall low-confidence warnings;
- canonical but unconfigured families;
- yfinance private diagnostic receives no production evidence/coverage credit;
- `permission_required` and `licensed_feed_required` typed missingness;
- options without a licensed transaction-plus-quote feed stay unavailable;
- technical without licensed OHLC stays neutrally missing;
- incomplete social windows, sample insufficiency, and collector outage stay neutral;
- GDELT request-path cache isolation, one-download-per-file batch matching, bounded
  Web NGrams processing, exact official-host enforcement, and publisher-body exclusion;
- Bluesky documented official-host fallback without proxying;
- sentiment/model-disabled behavior;
- missing baseline and valid current-vs-prior change calculations;
- recursive redaction and the 8 KiB raw limit;
- source inclusion/suppression and raw opt-in;
- all risk modes and prohibited-language checks.

Contract tests cover FastMCP discovery, input JSON Schema, structured output,
complete PRD response shape, stdio invocation, and local streamable HTTP
invocation. The HTTP test starts on an ephemeral loopback port.

`catalyst-edge-smoke` is opt-in and uses current configuration. Launch readiness
requires a real response containing SEC provenance plus at least one fresh
directional observation that is either direct SEC insider activity, an
allowlisted material event backed by SEC/issuer-primary provenance, or evidence
from an explicitly authorized provider. Provider names and credentials alone
never qualify. The report must show correct typed status for every canonical
family. yfinance, GDELT discovery, attention-only social data, stale data, and
neutral observations cannot satisfy the directional gate. A no-data response
proves graceful failure only and cannot satisfy launch readiness.

Documentation acceptance requires:

- complete environment/provider configuration matrix;
- full realistic source-linked response;
- permission/license-required, private-diagnostic, and no-data examples;
- source-policy and retention documentation;
- stdio, HTTP, test, and live-smoke commands;
- scoring/data-quality limitations without classifying unfinished PRD work as
  deferred scope.

## 15. PRD-to-TDD traceability

Test identifiers below are mandatory names or markers in the test suite.

### Required behavior and TDD requirements

| PRD item | Design coverage | Required verification |
| --- | --- | --- |
| RB1 validate before collection | §3, §8 | `UT_INPUT_*`, adapter-not-called assertion |
| RB2 bounded collection and partial failure | §6, §8 | `UT_TIMEOUT`, `UT_PARTIAL_FAILURE` |
| RB3 common evidence normalization | §4–§6 | `PT_*_NORMALIZATION` for every provider |
| RB4 deterministic available-evidence score | §9 | `UT_SCORE_*` |
| RB5 missing/stale/low-confidence/unbacktested warnings | §8 | `UT_QUALITY_*` |
| RB6 source/provenance | §5–§6 | `UT_PROVENANCE`, provider fixture tests |
| RB7 advice-language guardrails | §10 | `UT_LANGUAGE_ALL_MODES` |
| RB8 visible model status | §9 | `CT_RESPONSE_SCHEMA` |
| RB9 compact output and optional raw data | §7, §10 | `UT_COMPACTNESS`, `UT_RAW_*` |
| RB10 testable without live APIs | §2, §14 | default offline suite |
| TR1 framework and entrypoint | §1–§2, §12 | `CT_DISCOVERY`, `CT_STDIO`, `CT_HTTP` |
| TR2 file/module layout | §2 | package import/build test |
| TR3 tool and JSON schemas | §3 | `CT_INPUT_SCHEMA`, `CT_RESPONSE_SCHEMA` |
| TR4 service interfaces and DI | §4 | injected adapter/scorer/clock tests |
| TR5 evidence schema | §5 | schema and serialization tests |
| TR6 exact scoring formula | §9 | exact-math and attribution tests |
| TR7 timeout/partial failure | §6, §8 | timeout/cancellation/failure tests |
| TR8 provenance handling | §5–§6 | provider URL and suppression tests |
| TR9 data-quality warnings | §8 | warning threshold/missing/stale tests |
| TR10 fixture/mock plan | §14 | complete offline suite |
| TR11 Flask migration path | §11 | design review; later route contract suite |
| TR12 security/compliance guardrails | §3, §7, §10, §12 | redaction/language/exposure tests |
| TR13 source-policy enforcement | §5–§6 | `UT_SOURCE_POLICY`, `PT_PERMISSION_REQUIRED` |
| TR14 typed canonical status | §3–§4, §8 | `CT_FAMILY_STATUS`, `FX_LICENSED_FEED_REQUIRED` |
| TR15 evidence-semantic readiness | §14 | `UT_SMOKE_*` direct-insider/event/authorized cases |
| TR16 options integrity | §5–§6, §9 | `FX_OPTIONS_UNLICENSED_NEUTRAL`, `UT_OPTIONS_ENTITLEMENTS_*` |
| TR17 attention/sentiment separation | §5, §8–§9 | `FX_SOCIAL_ATTENTION_NEUTRAL`, `FX_SENTIMENT_MODEL_DISABLED` |
| TR18 free-source rate/host policy | §6 | `PT_GDELT_WEB_NGRAMS`, `PT_BLUESKY_HOST_FALLBACK` |
| TR19 Phase 6 product validation | §13–§14 | `FX_PHASE6_HISTORICAL_PRODUCT_CASES` |

### Acceptance criteria, fixtures, and Definition of Done

| PRD item | Design coverage | Required verification |
| --- | --- | --- |
| AC local tool returns contract | §3, §12, §14 | `CT_STDIO`, `CT_RESPONSE_SCHEMA` |
| AC tests pass without keys | §14 | default CI clears provider env vars |
| AC ticker/default/bounds tests | §3, §14 | `UT_INPUT_*` |
| AC all-success collection | §8, §14 | `FX_STRONG_BULLISH` |
| AC partial failure | §8, §14 | `UT_PARTIAL_FAILURE` |
| AC no-data response | §8–§10 | `FX_NO_DATA` |
| AC scoring contribution math | §9 | `UT_SCORE_ATTRIBUTION` |
| AC provenance formatting | §5 | `UT_PROVENANCE` |
| AC raw false by default | §3, §7 | `UT_RAW_DEFAULT` |
| AC no recommendation language | §10 | `UT_LANGUAGE_ALL_MODES` |
| AC sibling route unchanged | §11 | git scope check |
| AC random-weight model unused | §1, §11 | import/dependency scan |
| AC scoring/model fields | §3, §9 | `CT_RESPONSE_SCHEMA` |
| AC run docs and sample response | §14 | documentation acceptance check |
| FX strong multi-source bullish | §14 | `FX_STRONG_BULLISH` |
| FX weak social-only | §14 | `FX_WEAK_SOCIAL` |
| FX bearish filing/news | §5, §14 | `FX_BEARISH_FILING_NEWS` |
| FX missing insider | §8, §14 | `FX_MISSING_INSIDER` |
| FX stale options | §8, §14 | `FX_STALE_OPTIONS` |
| FX permission required | §6, §8, §14 | `PT_PERMISSION_REQUIRED` |
| FX licensed flow required | §3, §6, §14 | `FX_LICENSED_FEED_REQUIRED` |
| FX options unavailable is neutral | §5, §9, §14 | `FX_OPTIONS_UNLICENSED_NEUTRAL` |
| FX attention-only social is neutral | §5, §9, §14 | `FX_SOCIAL_ATTENTION_NEUTRAL` |
| FX collector timeout | §6, §14 | `UT_TIMEOUT` |
| FX invalid ticker | §3, §14 | `UT_INPUT_INVALID_TICKER` |
| DoD callable compact source-linked dossier | §10, §12, §14 | stdio/HTTP contracts plus live smoke |
| DoD deterministic and caveated | §8–§10 | score, warning, and language suites |
| DoD excludes random model | §1, §11 | import/dependency scan |

## 16. Resolved PRD open questions

- **SDK/version:** official MCP Python SDK stable v1, constrained below v2.
- **Runtime:** read-only local stdio and local streamable HTTP; no cloud
  deployment in this repository.
- **Reliable collectors:** direct SEC is the required primary baseline; reviewed
  issuer feeds, GDELT discovery, and partial public attention extend it under
  §6 policy. No sibling runtime imports.
- **Flask migration:** decision-complete design only; execution remains the
  PRD-stated follow-up.
- **Legally available sources:** SEC is approved under fair-access and content-
  retention constraints. Issuer/GDELT/Bluesky/Mastodon use the reviewed policies
  in §6. FMP, Finnhub, Reddit, Stocktwits, OCC, OHLC vendors, and options vendors
  require an explicit permission/license decision; credentials are insufficient.
- **Options:** zero-subscription production reports
  `licensed_feed_required`; yfinance is private diagnostic only.
- **Technical:** typed neutral missingness until a user-supplied/licensed OHLC
  source is approved.
- **Scorer:** deterministic v1 behind `CatalystScorer`; no trained scorer or
  performance claim in this implementation.
