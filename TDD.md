# Catalyst Edge MCP — Technical Design

**Revision:** Public self-serve source defaults aligned, 2026-08-02

## 1. Scope, outcome, and fixed decisions

This document is the implementation design for the current `PRD.md` local
acceptance boundary. The
deliverable is a standalone, read-only MCP server in this repository exposing
`catalyst_edge_score` plus the bounded supporting query
`catalyst_edge_claim_sources`. Completion means the score tool can return a compact,
source-linked catalyst dossier backed by usable free evidence, with explicit
missingness for unavailable families. A schema-valid no-data result is required
failure behavior, but is not sufficient for product acceptance. Local acceptance
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
- The zero-subscription capability set is direct SEC data, reviewed issuer feeds, GDELT
  discovery metadata, Bluesky AppView, and reviewed Mastodon instances. The public
  self-serve runtime composes SEC only when a monitored identity is supplied; issuer
  feeds, GDELT, and Bluesky default to disabled and require explicit opt-in after the
  applicable source/output review. Each non-SEC source remains constrained by the
  source-policy registry in §6.
- FMP, Finnhub, Reddit, Stocktwits, OCC, and any options vendor are conditional:
  credentials alone never prove commercial authorization. Their adapters may
  run only after an explicit policy decision records the needed
  permission or license.
- True `options_flow` requires a licensed transaction-plus-quote source.
  yfinance is development/private diagnostic data only and never supplies
  local product evidence, canonical coverage, or readiness credit.
- Five canonical families are always expected: `filings_news`,
  `insider_trading`, `options_flow`, `technical`, and `social`.
  `alternative` is optional.
- `technical` requires a user-supplied/licensed OHLC source or typed neutral
  missingness. Licensed OHLC is an optional future extension and is not a
  blocker for the current local product boundary.
- MediaCrawler, ai-berkshire, trained/calibrated scoring, licensed options flow,
  and execution of the sibling Flask migration remain future/conditional items.

## 2. Package architecture and entrypoints

The implementation is split by responsibility rather than by provider runtime:

```text
catalyst_edge_mcp/
  models.py                 # public and internal Pydantic schemas
  reason_records.py         # scoped reason IDs and display ordering
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

`build_service(settings)` is the only real, non-fixture composition root. Here,
“production” in older code comments means this runtime path; it does not imply a
hosted service, paid-provider requirement, or consumer deployment. Tests inject
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

The supporting `catalyst_edge_claim_sources` tool accepts `claim_id`, an integer
cursor defaulting to zero, and a limit from 1–20. It returns an exact total, a
bounded list of immutable source references, and a next cursor when another page
exists. Unknown or malformed claim IDs fail closed. The query reads local retained
metadata only; it performs no provider collection and does not affect scoring.

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

Every grouped operational event also receives an immutable `clm_<sha256>` claim ID.
Its evidence context reports the exact source-record count, up to 20 stable
`src_<sha256>` supporting IDs, and whether that compact list is truncated. The
claim-source query resolves those IDs to every counted source/accession. Relations
are append-only and retry-idempotent; existing event/source rows are deterministically
backfilled when the additive schema opens.

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
| Reviewed issuer RSS/Atom | `approved_per_registry` | Disabled by public default; only reviewed feeds/terms and bounded metadata/factual extraction after explicit opt-in |
| GDELT Web NGrams/TOC | `approved_discovery` | Disabled by public default until required GDELT citation/linking is implemented; discovery never outranks primary evidence |
| Bluesky AppView | `approved_partial_attention` | Disabled by public default; minimal post metadata/derived buckets only after output/privacy/retention review |
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
- GDELT: request-time evaluation is cache-only. The server lifespan coordinator and
  explicit recovery command download the newest bounded Web NGrams index/TOC pairs from the official
  `storage.googleapis.com/data.gdeltproject.org/gdeltv5/weblegacy/ngrams` path,
  matches all reviewed issuers in one pass, and stores publisher metadata/links
  rather than article bodies or ngram context. Registry-v2 rules resolve each valid
  TOC candidate before ingestion using reviewed alias kind, match mode, context,
  validity, CIK, and rule provenance. A candidate that passes body-context rules must
  also name a reviewed issuer alias or non-single-letter ticker in its surfaced title;
  `title_not_aligned` candidates remain audited but are not ingested. Cache reads apply
  the same alignment check to suppress legacy tangential events without deleting them.
  Exact host/path validation, byte ceilings, a
  five-file run limit, a 200-candidate audit cap, and a separate 50-accepted-document
  ingestion cap per issuer bound the collector.
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
automatic lifecycle and explicit recovery command have a 30-second per-file upstream
budget. Persisted last-check state prevents restart storms, while due or never-refreshed
state receives one bounded startup catch-up. Broad collection runs outside request
latency. There are no unbounded retries. `429`, permission,
license, schema, network, and timeout failures map to typed statuses and cached
partial results with freshness. Cancellation always propagates.

The evidence store uses SQLite/WAL tables for `source_observation`,
`canonical_event`, `event_source`, `insider_transaction`, `insider_cluster`,
`social_bucket`, `collector_state`, `source_policy`, `event_claim`, `claim_source`,
and `entity_match_audit`.
Entity decisions are append-only and retry-idempotent by audit fingerprint; a
ruleset or candidate-context change appends a distinct record. The table retains
TOC/context hashes and derived matched terms, never publisher bodies or raw NGram
text. Event deduplication
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
  -> calculate family/data-quality warnings and scoped reasons
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

`data_quality.reason_records` retains typed reasons at source, candidate, family,
or evaluation scope. The allowed codes are `observed_none`, `source_unavailable`,
`source_unsupported`, `entity_rejected`, `discovery_only`, and
`evaluated_not_material`. Records are deduplicated by deterministic reason ID and
displayed in that order by precedence groups: unavailable, unsupported, rejected,
none observed, discovery-only, then evaluated non-material. This display order
does not erase coexisting reasons or map them to RESEARCH NOW/MONITOR/IGNORE.
The production-safe output bound is 600 records; total count and truncation are
explicit if a nonstandard composition exceeds it. GDELT uses one source-scoped
aggregate `entity_rejected` disposition for the evaluation window; individual
candidate decisions remain recoverable from the append-only audit and are not
silently truncated into the dossier.

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

Implementation status on 2026-07-15: the contract and collector foundation in
Phases 0 through 5 is implemented and covered by offline contract/parser
fixtures. Phase 1 was live-validated against
representative SEC Forms 4/144 and 8-K archive metadata. Phase 2 was live-validated
against the reviewed Apple and NVIDIA issuer feeds, including conditional state.
Phase 3 has bounded success/empty/malformed/rate-limit/timeout/host/provenance
fixtures. Repeated live request-path timeouts moved DOC refreshes into an explicit
out-of-band command; MCP evaluation now reads the typed cache without response-body
retention.
Phase 4 now uses only the two documented Bluesky AppView hosts from an out-of-band
forward collector. Request-time evaluation is cache-only. The collector persists 14
completed daily buckets without post bodies, never follows search cursors, fails closed
on reported ranked-page overflow, gaps, stale/outage state, or disappeared URI hashes, and
keeps attention neutral. No Mastodon instance registry is composed because the
review found no approved instance set from which representative cross-instance
coverage could be established. The live Bluesky POC confirmed the current 403 on
the cached public search host and successful unauthenticated direct-AppView fallback.
Phase 5 records immutable fail-closed audits for five sentiment candidates and
four options candidates. No candidate passes every required gate, so sentiment
and options remain uncomposed; the local composition root makes no
rejected-provider request. Phase 6 executes 28 dated, sanitized synthetic
contract cases plus a separate 25-case real SEC catalyst evaluation. The real
corpus verifies primary links, classification, accepted-time freshness,
distinct-event behavior, research value, and final dossier direction.

Completed on 2026-07-15: the first event-intelligence slice adds a typed evidence
context for event type, label, novelty, materiality, correction lineage, source
record counts, source tiers, and factual why-it-matters text. SEC 8-K item
taxonomy and insider semantics now produce evidence-specific summaries,
invalidation criteria, and source-aware next checks. Fixed real RKLB accessions
and live local runs verify the 8-K and Form 144 paths.

Accepted for the bounded local corpus on 2026-07-16: the 25-case real evaluation
exposed lexical multi-item priority, merger-related delisting direction, and
recorded Item 8.01 specificity gaps. Explicit context priority,
change-of-control delisting semantics, and `sec-primary-document-v1` rules cover
completed debt offerings, entered or amended equity distribution agreements,
filed prospectus supplements, and actual repurchase activity. The rule identity
and version are recorded; proposed, negated, unsupported, and ambiguous cases
fail closed to the generic event. Representative HTML, table, inline-XBRL,
amendment, multi-event, and near-match fixtures enforce that boundary. No filing
body is retained. The recorded corpus provides no forward-return labels, so
preserving the deterministic unbacktested numeric weights is the evidence-based
tuning decision. Final target-cohort, fresh GDELT, and recent RKLB acceptance
passed.

Completed on 2026-07-21: the separate SEC fund lane adds strict reviewed CIK,
series/class, historical ticker/status, and sponsor-primary metadata for SPY,
QQQ, DIA, IWM, XLE, XLK, GLD, and GDX. QQQ, IWM, XLE, XLK, and GDX parse
N-CEN/NPORT XML with report, period-end, filing, acceptance, accession, hash,
and parser provenance into neutral research-only evidence. SPY and DIA fail
closed because the official mutual-fund ticker map supplies no series/class IDs;
GLD is typed outside this investment-company form lane. Fund tickers return
explicit unsupported reasons from corporate filing and insider collectors.

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
   integration. FastMCP lifespan now schedules due startup catch-up and periodic
   refresh, cancels cleanly, and exposes last-success age and explicit freshness
   states through `catalyst-edge-health` and request-time degradation warnings. The
   legacy DOC endpoint is no longer used by the refresh command.
   Issuer-feed, discovery, and social registries now compose from one strict local
   JSON file with packaged reviewed defaults. Duplicate ticker ownership, ambiguous
   aliases, unknown fields, malformed CIKs, and feed-host mismatches fail closed.
   Reviewed publisher-domain tiers deterministically set GDELT quality from 0.62 to
   0.70; unlisted domains receive 0.60 and never inherit through lookalike suffixes.
   Registry v2 now applies ruleset-versioned per-alias context, exclusion, validity,
   CIK, provenance, and surfaced-title alignment rules before ingestion. Every valid
   TOC candidate receives an
   append-only accepted/rejected audit record; reject-only runs remain fresh successful
   no-observation collections. Legacy registry v1 files remain load-compatible, and
   legacy cached observations age out normally rather than being destructively purged.
   Immutable claim/source relations now make every grouped count recoverable through
   a bounded MCP query, and scoped reason records retain unavailable, unsupported,
   no-observation, entity-rejected, discovery-only, and evaluated-non-material
   dispositions without changing scoring semantics.
4. Implemented: Bluesky exact-match partial public attention with cached-to-direct
   official AppView fallback, scheduled forward daily buckets, 14-day warm-up,
   cache-only MCP reads, minimum samples, deletion-aware failure states, and neutral
   semantics. Mastodon remains
   uncomposed after the measured allowlist decision found no reviewed instance
   set for representative coverage.
5. Implemented: audited Finnhub sentiment, TextBlob, VADER, DistilBERT SST-2,
   and ProsusAI FinBERT against rights, Python, preprocessing, labeled-quality,
   rounding, and threshold gates. Audited FlowAlgo, CheddarFlow, a future OPRA
   vendor, and yfinance against transaction-plus-quote and entitlement gates.
   None passes; all remain disabled and uncomposed.
6. Accepted for the current corpus: 28 dated sanitized synthetic cases cover
   directional strength, primary
   and discovery provenance, insider clusters, Form 144, missing/stale/provider
   failures, Bluesky historical warm-up/outage/sample regressions, contradictions, rejected
   sentiment, and options/technical entitlement boundaries. All assertions pass;
   the separate 25-case real SEC corpus and final live acceptance also pass. The
   no-change numeric scorer decision is documented from the corpus limitations.

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
  Web NGrams processing, exact official-host enforcement, publisher-body exclusion,
  startup/periodic lifecycle, restart throttling, clean shutdown, and freshness health;
- registry-v2 entity-rule validation, legacy-v1 translation, ruleset hashing,
  required/negative context and validity behavior, accept/reject audit idempotence,
  rejection non-starvation, and reject-only freshness semantics;
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
| TR19 Phase 6 synthetic contract validation | §13–§14 | `FX_PHASE6_HISTORICAL_PRODUCT_CASES` |
| TR20 real-case product validation | §13–§14 | `test_real_catalyst_evaluation.py`, 25 recorded official-SEC cases, completion report |
| TR21 local collection lifecycle | §6, §8, §14 | `test_collection_lifecycle.py`, cache-only GDELT adapter tests, server lifespan test |
| TR22 validated local registries and domain tiers | §6, §8, §14 | `test_registry_config.py`, GDELT publisher-quality tests, composition-root tests |
| TR23 deterministic entity decisions and rejection audit | §6, §8, §14, §17 | `test_entity_resolution.py`, `test_gdelt_web_ngrams.py`, `test_evidence_store.py` |
| TR24 grouped-source recovery and scoped reasons | §3, §5–§6, §8, §14, §17 | `test_evidence_store.py`, `test_service.py`, `CT_CLAIM_SOURCE_SCHEMA_AND_DIRECT_INVOCATION` |
| TR25 SEC fund identity and as-filed evidence | §5–§6, §8, §14, §17 | `test_sec_funds.py`, fixed SPY/QQQ/DIA/IWM/XLE/XLK/GLD/GDX registry assertions, composition-root tests |

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
- **Legally available sources:** SEC is the public baseline under fair-access and
  content-retention constraints. Issuer/Bluesky/Mastodon use the reviewed policies in
  §6 and remain disabled by public default. GDELT permits commercial use and
  redistribution but requires a GDELT citation/link; it remains disabled until that
  output contract is implemented. FMP, Finnhub, Reddit, Stocktwits, OCC, OHLC vendors,
  and options vendors require an explicit permission/license decision; credentials are
  insufficient.
- **Options:** the zero-subscription local runtime reports
  `licensed_feed_required`; yfinance is private diagnostic only.
- **Technical:** typed neutral missingness until a user-supplied/licensed OHLC
  source is approved; this optional extension does not block local completion.
- **Scorer:** deterministic v1 behind `CatalystScorer`; no trained scorer or
  performance claim in this implementation.

## 17. Point-in-time replay and backtest addendum

### 17.1 Status and decision boundary

This section defines a future, provider-neutral replay architecture. It does not
authorize a vendor purchase, paid-data ingestion, scorer calibration, or a
predictive claim. The current MCP remains `deterministic_v1`, `not_trained`, and
`unbacktested` until the Stage B acceptance contract below passes.

As of 2026-07-21, entity-resolution v2, append-only rejected-match auditing,
scoped reason semantics, immutable grouped-source recovery, and the SEC-backed
fund lane are implemented in the operational collector. The replay dataset and
every vendor-gated identity/price/terminal-outcome component remain future work.

The chosen design separates two systems:

1. The existing operational SQLite event graph continues to support bounded
   local collection and current dossier assembly.
2. A new immutable research dataset freezes historically admissible evidence,
   identity, configuration, scorer inputs, and outcome labels for replay.

The operational graph is not retroactively treated as a point-in-time ledger.
Mutable `collector_state` and `source_policy` rows remain operational state and
cannot establish what a historical evaluation knew.

#### Inputs and normative dependencies

| Input or dependency | Status for this addendum |
| --- | --- |
| [Free/open-source coverage research](docs/research/2026-07-21-free-open-source-coverage-research.md) | Normative source-quality and entity-resolution evidence |
| [Point-in-time dataset research](docs/research/2026-07-21-point-in-time-backtest-dataset-research.md) | Normative replay, label, sampling, and vendor-rights evidence |
| [Reconciled source roadmap](docs/research/2026-07-21-catalyst-source-roadmap.md) | Normative ordering and approval gates |
| Operational provenance, collection, missingness, and scoring (§§5–9) | Implemented current-system inputs |
| Entity-resolution v2, scoped reasons, immutable grouped-source recovery, and SEC-backed ETF/fund identity | Required before Stage A |
| Point-in-time identity/lifecycle/price rights and provider mappings | Vendor-gated before Stage A |
| Survivor-aware terminal-outcome rights and mapping | Vendor-gated before Stage B |

#### Domain terms

- **Provider-neutral:** the canonical contract is independent of any vendor's
  field names or delivery format.
- **Pre-registered:** frozen and hashed before forward returns are joined.
- **Source observation:** one immutable version of one source record, including
  provenance and an availability decision.
- **Evaluation case:** one security at one `evaluation_at`, with the complete
  eligible evidence packet and scorer snapshot. Stage A/B sample counts always
  count evaluation cases, not source observations.
- **Label:** one outcome for an evaluation case, horizon, and cost scenario.
- **Fact manifest:** a content-hashed record of extracted facts and provenance
  used when raw payload retention is not permitted.
- **Scoped reason record:** a typed missingness/disposition reason attached to a
  named source, candidate, family, or evaluation scope; multiple reasons may
  coexist.
- **Shared untouched test:** one holdout opened once for all scorer candidates
  frozen before that opening.
- **Signal bucket:** a score/rank interval whose boundaries are pre-registered.
- **Claimed family:** an evidence family whose coverage claim and expected-cell
  denominator are pre-registered before outcomes are joined.

### 17.2 Desired end state

Given an `evaluation_at` timestamp, dataset version, and scorer version, the
research system reconstructs the exact admissible evidence packet, security
identity, market session, score, and forward labels without consulting current
registry state or later corrections. A rerun from retained licensed inputs
produces byte-identical normalized observations and labels.

Stage A proves replay correctness on 50–100 manually audited evaluation cases.
Stage B creates at least 1,000 valid evaluation cases, including at least 250 in
one shared untouched test, from a survivor-aware active/inactive universe beginning
no earlier than 2018-05-01.

### 17.3 Chosen approach: immutable manifests plus licensed label components

Catalyst Edge owns and freezes the evidence transformation layer:

- SEC accession-level filings and ownership facts;
- historically admissible issuer-primary metadata;
- GDELT metadata as discovery-only evidence;
- entity, deduplication, parser, registry, policy, and scorer decisions; and
- content hashes or fact manifests when raw retention is not permitted.

Identity, lifecycle, price, adjustment, and terminal-outcome components are
adapter contracts backed by an approved source. The conditional Stage A
candidate is Databento Corporate Actions, the separately licensed Databento
Security Master, and Tiingo end-of-day prices. This is not a Stage B selection.
Stage B requires CRSP or a contractually equivalent source that supplies
survivor-aware identity and complete terminal outcomes or delisting returns.

Vendor-specific field mappings remain unset until approved sample schemas and
written retention/derived-use rights are received. Adapters must map into this
canonical contract rather than leaking provider field names into replay logic.

### 17.4 Canonical immutable contract

#### Relationship map and version lifecycle

```text
build_specification ──> build_attempt ──success──> build_run
       │                                         │
       └─────────────────────────────────────────> dataset_version
                                                    │
                                                    ├─> evaluation_case
                                                    │      ├─> source_observation(s)
                                                    │      └─> scorer_snapshot
                                                    └─> label(s by horizon/scenario)
```

- A `build_specification` is the canonical, pre-registered set of provider
  manifests, queries, policies, configurations, and code/environment hashes.
- A `build_attempt` is one execution with a catalog-only UUID.
- A successful attempt creates a `build_run` with output and audit hashes.
- A `dataset_version` is the content-addressed normalized output. Deterministic
  reruns of the same specification share the dataset version and create separate
  build runs; changed bytes create a new version. No prior version is overwritten.

One dataset version may have many build runs and evaluation cases. One security
has many non-overlapping identity intervals and lifecycle records. One evaluation
case references every eligible source observation in its evidence packet and
exactly one scorer snapshot. It has one label per horizon and cost scenario.

#### Logical records

Security identity and lifecycle records contain:

- `security_id`, `security_id_type`, issuer CIK, share class, and security type;
- ticker, name, exchange, and optional classification validity intervals;
- listing/IPO, halt/suspension, symbol/name change, merger, acquisition,
  bankruptcy, delisting, and terminal-outcome records; and
- announcement, record, effective, source-observation, retrieval, version, and
  hash metadata.

Point-in-time sector or size classifications may be used only when their source
and interval were valid at `evaluation_at`; otherwise matching uses prior price,
dollar volume, volatility, and momentum.

Each source observation contains:

- source ID/tier, accession or record ID, canonical URL, and permitted raw-object
  or fact-manifest reference;
- event occurrence and authoritative acceptance/publication times;
- `historically_available_at`, proof type/reference, and `reconstructed_at`;
- correction, amendment, or deletion lineage;
- parser, entity-ruleset, deduplication, registry, and source-policy versions; and
- normalized evidence, supporting source IDs, family status, warnings, and the
  complete ordered set of scoped reason records.

A 2026 backfill is never represented as collector-observed in 2018. Historical
issuer content is admissible only with a contemporaneous archive or identical
immutable SEC filing/exhibit; otherwise it remains discovery-only.

Each evaluation case contains `evaluation_at`, eligibility cutoff, frozen market
calendar, session relationship, scorer/code/environment hashes, score,
direction, confidence, and contribution breakdown. A downstream three-class
evaluation additionally freezes its owner, policy version, class definitions,
and exact score/reason mapping; those classes are not MCP-owned fields.

Each label contains entry convention and prices; 1/5/20-session raw-price,
total, SPY-relative, and conditionally sector-relative returns; path excursion;
halt/missing/merger/delisting/terminal status; and a versioned cost scenario.

#### Immutable IDs

`observation_key` is `cek_` plus SHA-256 of source ID, canonical issuer/security
ID, and stable source record ID joined by the unit separator. `observation_id`
is `ceo_` plus the hash of that key and the provider version ID or retained
payload/fact-manifest hash. Same-record corrections create new observations
linked through `correction_of_observation_id`.

`dataset_version` is `ced_` plus the build-specification hash. `evaluation_id`
is `cee_` plus the hash of dataset version, security ID, evaluation timestamp,
and scorer version. `label_id` adds horizon and cost-scenario version. Existing
IDs must have identical canonical bytes; a same-version collision with different
bytes fails the build.

#### Provider protocol and failure policy

Each provider adapter yields provider-neutral identity, lifecycle, price,
action, or terminal records plus source record/version IDs, publication/record/
observation timestamps, retrieval manifest, and payload hash. A required
component that is incomplete, rights-blocked, or cannot map losslessly fails the
build. Optional evidence families emit typed missingness and never silently
reduce the eligible universe.

#### Physical storage and modules

```text
catalyst_edge_mcp/replay/
  contracts.py       # immutable records and typed failures
  manifests.py       # canonical manifests, hashes, and build lineage
  adapters/          # licensed provider mappings
  eligibility.py     # availability proofs and replay cutoffs
  sessions.py        # exchange calendar and entry-session mapping
  labels.py          # adjustments, returns, paths, and costs
  sampling.py        # pre-registered universe/event/control selection
  audit.py           # Stage A/Stage B invariants and exclusions
```

Permitted raw objects are content-addressed by SHA-256. Canonical records use
JSON Lines for byte identity and Parquet partitioned by dataset/source/date for
analysis. DuckDB runs frozen queries over Parquet. A small SQLite catalog stores
immutable specification, run, version, and audit manifests—not mutable source
truth.

#### Canonical serialization

Canonical output is UTF-8 JSON Lines: keys sorted lexicographically, Unicode
preserved, no insignificant whitespace, one record per line, one trailing
newline, and records sorted by immutable primary key. Timestamps are UTC RFC
3339 with six fractional digits and `Z`. Missing values are JSON `null`; NaN and
infinity are forbidden. Prices/cash are decimal strings quantized to 8 places;
returns/rates use 10 places; both use round-half-even. Integers and booleans are
native. Unordered source/reason sets are sorted by stable ID; paths remain
session ordered. Canonical JSONL hashes—not Parquet bytes—are the byte-identity
surface.

#### Label mathematics

Freeze `signal_sign` as `+1`, `0`, or `-1`. Underlying return is
`exit_price / entry_price - 1`; signed gross return is
`signal_sign * underlying_total_return`. Neutral cases retain underlying labels
but have zero hypothetical P&L. Maximum favorable/adverse excursion is the
maximum/minimum signed excursion from entry across split-adjusted daily high/low
values through the horizon.

Explicit corporate-action factors are authoritative for the auditable raw path.
Vendor total-return labels must reconcile to those actions within a pre-registered
tolerance or fail. End-of-day data does not observe spread, slippage, or borrow.
Round-trip non-borrow scenario cost is
`2 * (half_spread_bps + slippage_bps + fee_bps) / 10000`. Negative-signal cases
also subtract `annual_borrow_rate * calendar_days_held / 365`; neutral and
positive cases incur no borrow. Net labels use the same decimal/rounding contract.

### 17.5 Eligibility, sessions, and corrections

A fact is eligible only when:

```text
max(accepted_or_published_at, historically_available_at) <= evaluation_at
```

The corresponding availability proof must be retained. Allowed proof types are:

- `sec_acceptance`, using the authoritative EDGAR acceptance timestamp;
- `prospective_collector_receipt`, using the append-only collector receipt for
  data gathered while the system was operating;
- `contemporaneous_archive_capture`, using the archive capture time as the
  conservative availability boundary; and
- `provider_point_in_time_record`, only when the contracted field semantics
  establish the provider record timestamp as historical availability.

For non-SEC proofs, `historically_available_at` is the later of the claimed
publication time and proof time. If multiple valid proofs exist, use the earliest
resulting proven boundary and retain all proof references. Conflicting issuer,
record, or timestamp identity makes the observation ineligible pending manual
resolution. A missing or unapproved proof type is ineligible, never imputed.
`reconstructed_at` never substitutes for proof. Amendments and corrections
create new versions; a later version cannot change an earlier replay.

With daily bars, compute `tradable_at = eligibility_time + 15 minutes` and choose
the first regular-session open whose timestamp is greater than or equal to
`tradable_at`. This permits the same day's open for sufficiently early premarket
evidence and otherwise selects the next session open. Horizons count sessions
under a frozen exchange calendar, including holidays and half-days. Missing
terminal consideration is a data failure and cannot be silently excluded.

### 17.6 Dataset construction and test discipline

The Stage B period is 2018-05-01 through 2025-12-31 unless an earlier verified
lifecycle source is selected. The default split is train 2018-05-01–2021,
validation 2022–2023, and untouched test 2024–2025, with annual walk-forward
diagnostics.

The sampling query is frozen before joining forward returns:

- U.S. common equities from the licensed point-in-time active/inactive security
  master, subject to pre-registered minimum prior price and dollar-volume rules at
  `evaluation_at`;
- approximately 700 eligible SEC/issuer catalyst evaluation cases sampled under a
  pre-registered probability rule, with event-family/year population weights;
- approximately 300 control evaluation cases from the same historical universe,
  matched on date, prior price/dollar volume, and prior 20-session
  volatility/momentum, with no eligible catalyst in the pre-registered lookback;
- population weights for any event-family/year stratification; no direction
  quotas; and
- a separate deliberately selected terminal audit set containing inactive,
  acquired, bankrupt, delisted, and ticker-recycled cases. It is never pooled
  into performance estimates.

The corpus must cover the 2018 volatility/tightening period, the 2020
shock/recovery, 2021 risk-on conditions, the 2022 inflation/rate selloff,
2023–2024 megacap/AI concentration, and the 2025 rate/post-election period.
Regime labels are descriptive diagnostics frozen without reference to each
evaluation case's subsequent return.

Stage A contains evaluation cases spanning at least 20 distinct event types and
at least 10 controls, multiple
after-hours cases, and correction/amendment cases. Its separate terminal audit
set contains ticker changes, an acquisition, a bankruptcy/delisting, at least
five inactive securities, a ticker-recycling case, splits/dividends, an ETF,
and an ADR. Every timestamp, identity interval, dossier, entry session, and
label is manually checked.

The unchanged deterministic scorer and every candidate calibrated scorer are
frozen before one shared untouched-test unseal. A candidate proposed after that
unseal requires a new future holdout and cannot reuse 2024–2025 as untouched
evidence.

The pre-registered primary predictive metric defaults to the 20-session net
SPY-relative return difference between the highest pre-registered signal bucket
and matched controls. Its ticker-clustered/date-block-bootstrap 95% confidence
interval must exceed zero for a predictive claim. Directional accuracy, rank
correlation, concentration, calibration, costs, and walk-forward stability are
required supporting diagnostics.

Calibration is eligible for the shared untouched test only when it improves the
pre-registered validation objective over unchanged `deterministic_v1` across at
least two walk-forward folds. Every attempted model, weight, threshold, horizon,
and subgroup analysis is logged. Secondary searches use a pre-registered
false-discovery or family-wise correction and are reported whether favorable or
unfavorable.

### 17.7 Stage gates

#### Stage A entry criteria

- Entity-resolution v2, append-only rejected-match auditing, and scoped reason
  semantics are complete.
- Every grouped source count used by replay resolves through an immutable
  claim/source relation.
- The SEC-backed ETF/fund identity and evidence lane is complete because the
  mandatory Stage A audit set includes an ETF; fund cases never reuse corporate
  issuer or insider semantics.
- The selected identity, lifecycle, and price components pass written rights and
  the 25-symbol sample checks.
- The provider-neutral contract validator in §17.9 passes.

#### Stage A exit criteria

- Replay visibility changes exactly at each proven historical-availability
  boundary.
- Every sampled identity interval and entry session matches source records.
- Every correction/amendment replays the older version before the change.
- Every terminal audit case is represented without silent row removal.
- Frozen manifests reproduce byte-identical canonical observations and labels.

#### Stage B entry criteria

- Stage A passes with all exclusions and manual-audit results retained.
- CRSP or a contractually equivalent terminal-outcome source passes rights,
  field-semantics, coverage, and sample checks.
- The Stage B universe, sampling query, claimed families, primary metric,
  scorer candidates, cost scenarios, and multiple-testing policy are
  pre-registered before forward returns are joined.

#### Stage B exit criteria

- At least 1,000 valid evaluation cases and 250 shared-untouched-test cases exist.
- There are zero known critical timestamp, identity, terminal-outcome,
  look-ahead, or survivor-selection errors. A sub-1% allowance applies only to
  pre-registered noncritical metadata.
- Claimed-family evaluability is at least 95%:
  `covered expected cells / all expected family-by-evaluation-case cells`.
  A covered cell resolves to evidence or proven `observed_none`; unavailable,
  unsupported, stale, failed, and unproven-empty cells are uncovered.
- The claimed-family set and denominator are frozen before returns are joined and
  cannot be narrowed afterward. Evidence-presence, missingness, and exclusions
  are reported separately by family and fold.
- Baselines, costs, clustered uncertainty, and every primary metric are reported
  whether favorable or unfavorable.
- Signed dataset/scorer/config/code hashes reproduce through the required
  interface `uv run python -m catalyst_edge_mcp.replay.build --dataset-version
  <ced_id> --replay`. That interface is required before Stage B, not implemented
  by this addendum.

Passing Stage B does not itself prove predictive value. A predictive claim also
requires monotonic score-band behavior on the untouched test, stability across
the pre-registered walk-forward diagnostics, and no material sector or megacap
concentration explanation for the primary result. If any predictive gate fails,
the permitted statement is `backtested; no demonstrated predictive edge`.

### 17.8 Alternatives considered

**Operational SQLite as the replay database.** Rejected because mutable
collector/policy state and incomplete raw/config history cannot reconstruct an
arbitrary historical dossier. Retrofitting bitemporal research semantics into
the live graph would also couple current request latency to research storage.

**Zero-cost price APIs plus current ticker mappings.** Rejected for Stage B
because the reviewed candidates do not establish survivor-aware inactive/delisted
coverage, frozen revisions, terminal outcomes, or the required retained research
rights. Such a source may support an owner-only engineering prototype, not a
backtested product claim.

**Single enterprise market-data vendor.** Viable if one executed agreement
covers identity, lifecycle, prices, terminal outcomes, retention, model use, and
derived reports. It trades higher cost for fewer joins. The canonical adapter
contract deliberately permits this option if it beats the conditional Stage A
components on coverage and rights.

**CRSP for every stage.** Technically strongest among reviewed research sources,
but quote/access constraints may make it slower or more expensive for the first
50–100-case engineering proof. It remains the preferred Stage B source.

### 17.9 Solution validation and open concerns

#### Validated now

The provider-neutral cutoff and serialization contract was exercised with
`uv run python scripts/validate_replay_contract.py` against
the 25 recorded official-SEC cases in
`tests/fixtures/validation/real_catalyst_cases.json`. A read-only executable
normalized each accession into the contract, checked visibility one microsecond
before and exactly at acceptance, reversed input order, and compared the
canonical bytes.

| Dimension | Expected | Measured | Status |
| --- | ---: | ---: | --- |
| Recorded official-SEC cases normalized | 25 | 25 | Pass |
| Unique immutable observation IDs | 25 | 25 | Pass |
| Visibility-boundary assertions | 50 | 50 passed | Pass |
| Order-independent canonical bytes | identical | identical | Pass |
| Canonical JSONL hash | stable | `7a6d8a26673100014173f1d7a240600c7fb219da14580a9d211f66e2b7c6a3e9` | Pass |

This validates deterministic identity, SEC availability cutoffs, ordering, and
canonical serialization for the real recorded target cases. It does not validate
market-session mapping, returns, adjustments, terminal outcomes, provider
corrections, coverage, or rights.

#### Not yet validated

Full end-to-end validation is not yet possible because no approved licensed
source, sample schema, or terminal-outcome feed is available in the workspace,
and contacting or purchasing from vendors requires owner approval. Mocked
provider mappings would not validate point-in-time coverage, terminal outcomes,
retained-data rights, or vendor rebuild behavior.

#### Open Stage A decisions

- approved provider field mappings and correction semantics;
- exact retention, post-termination, team, model-calibration, benchmark-report,
  and hosted-derived-output rights;
- empirical market-session, adjustment, and cost-label validation;
- total price for the separately licensed Stage A Corporate Actions, Security
  Master, and EOD components; and
- a 25-symbol sample spanning active, renamed, merged, acquired, bankrupt,
  delisted, recycled-ticker, ETF, ADR, split, and special-distribution cases.

#### Open Stage B decisions

- complete terminal consideration or delisting-return field semantics and
  empirical terminal-label validation; and
- rights and total price for CRSP or another approved terminal-outcome source.

#### Authorization boundary

Preparing the questionnaire and sample list is authorized documentation work.
Sending either, approving a quote, purchasing data, or implementing a
vendor-specific adapter requires a separate owner decision.
