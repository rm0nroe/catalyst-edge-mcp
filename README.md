# CATALYST/EDGE

<!-- mcp-name: io.github.rm0nroe/catalyst-edge-mcp -->

**Catalyst Edge Research** is source-linked market intelligence for AI agents. The
standalone, read-only MCP server returns compact,
source-linked catalyst evidence dossiers for public-company tickers. It collects
independent evidence families concurrently and applies a documented deterministic
score. It does not import the sibling `prior service` application or its random-weight
model.

The public surface has two read-only tools: `catalyst_edge_score` returns the
compact dossier, and `catalyst_edge_claim_sources` pages through every immutable
source record counted by a grouped claim.

## Audience and distribution status

Catalyst Edge is for analysts and builders. **Builders includes retail traders and
technically capable individual investors who assemble their own Claude, Codex, Cursor,
or other MCP research workflows.** It is not limited to institutional teams.

The product promise is bounded:

> Ask your AI research agent what changed for a ticker, why it matters, what contradicts
> it, and show every source and missing-data warning.

The scorer is deterministic and unbacktested. Catalyst Edge does not promise alpha,
investment performance, buy/sell signals, personalized advice, or execution.

Version 0.1.4 is the approved free Local Beta for GitHub, PyPI, Codex, the MCP
Registry, and Claude Desktop. The Claude Desktop `.mcpb` is distributed as a transparent
unsigned custom extension because file-level publisher verification is unavailable in the
released MCPB tooling. Review the source and checksum before installing it. This is separate
from any future Anthropic directory review. The current direction also includes
a `Hosted Pro — $29/month` paid-intent test. Research does not support building Hosted Pro
now: only recent activation-linked, verified, price-aware signups count toward staged 350
compatibility-spike, 1,350 scoped-review, and 11,100 safeguarded full-build reconsideration
gates. None grants automatic implementation, payment, or deployment authority.

## Current status and completion boundary

As of 2026-07-21, the zero-subscription local runtime has the free dependencies
needed to deliver the revised product: direct SEC filings and insider records plus
implemented GDELT Web NGrams discovery and opt-in issuer-feed and Bluesky capabilities.
The MCP transports, schemas, provenance, typed missingness, event graph, and
deterministic scorer are implemented and tested.

The first product-completion slice landed on 2026-07-15: evidence now carries
event type, materiality, novelty, correction lineage, source-record support, and
factual why-it-matters context. SEC 8-K item codes and insider transaction facts
drive event-specific headlines, invalidation criteria, and next checks. The slice
is covered by fixed real RKLB SEC metadata and was rechecked against live RKLB
Form 144 and 8-K records.

The default local GDELT lifecycle schedules a bounded catch-up when persisted state is
due, while periodic refresh remains outside
the MCP request path, shutdown cancels cleanly, and `catalyst-edge-health` reports
last-success age plus fresh, stale, failed, never-refreshed, or unregistered state.
Every dossier and paginated claim containing GDELT-derived data includes a machine-readable
`The GDELT Project` citation and official link even when detailed sources are suppressed.
Issuer feeds, discovery rules, social aliases, and publisher-domain quality tiers
now load from one strictly validated local JSON registry. Registry v2 applies
reviewed per-alias kind, match mode, required/negative context, validity interval,
canonical CIK, rule version, and review provenance before a GDELT candidate enters
the event graph. Custom registry v1 files remain compatible through deterministic
legacy-rule translation. The packaged reviewed defaults preserve the existing
cohort; a custom path replaces that cohort rather than silently merging unreviewed
aliases.

Grouped issuer-feed and GDELT evidence now carries an immutable `claim_id`, exact
`source_record_count`, and up to 20 `supporting_source_ids`. Call
`catalyst_edge_claim_sources` with the claim ID and its integer cursor to recover
every source ID, accession/record ID, canonical URL, timestamp, hash, parser, and
policy decision in pages of at most 20. `data_quality.reason_records` separately
retains ordered scoped reasons for unsupported or unavailable sources, no
observations, rejected entities, discovery-only evidence, and evaluated
non-material candidates. Display precedence does not discard coexisting reasons,
and truncation is explicit through `reason_record_count` and
`reason_records_truncated`. GDELT rejection disposition is source-scoped and
aggregate in the dossier; individual candidate decisions remain in the bounded
append-only entity audit.

The zero-subscription runtime meets its current local acceptance corpus as of
2026-07-16. A 25-case real SEC evaluation complements the 28 synthetic Phase 6
contract scenarios. It exposed and closed event-priority, merger-delisting, and
recorded Item 8.01 specificity defects; all recorded classification, provenance,
freshness, distinct-event, research-value, and dossier-direction checks pass.

The SEC-backed fund lane is implemented for SPY, QQQ, DIA, IWM, XLE, XLK, GLD,
and GDX. QQQ, IWM, XLE, XLK, and GDX resolve reviewed SEC registrant CIK plus
series/class IDs and produce neutral N-CEN/NPORT context with separate report,
period-end, filing, and acceptance chronology. SPY and DIA have official CIKs
but no SEC mutual-fund series/class mapping; GLD is outside the N-CEN/NPORT
investment-company lane. Those three cases return explicit `source_unsupported`
reasons instead of invented identifiers. Reviewed sponsor-primary URLs are
retained as metadata only, and every reviewed fund bypasses corporate filing
and insider semantics.

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
unbacktested. Paid options flow, licensed OHLC, sentiment, hosted deployment, and
broader SEC semantic extraction are future capabilities. Version 0.1.4 ships only the
local, self-serve surface.

In older implementation notes and runtime messages, “production” means the
real non-fixture composition path used by the local MCP. It does not imply a
hosted service, third-party provider role, paid account, or consumer rollout.

## Install

For Claude Desktop, download
[`catalyst-edge-mcp-0.1.4.mcpb`](https://github.com/rm0nroe/catalyst-edge-mcp/releases/download/v0.1.4/catalyst-edge-mcp-0.1.4.mcpb),
then choose **Settings → Extensions → Advanced settings → Install Extension…**. Enter a
monitored SEC identity in `Company email@example.com` form. Claude will show an unverified
custom-extension warning because the bundle is unsigned; review and accept it only if the
download and published SHA-256 match.

For Codex, Python 3.10+ and [uv](https://docs.astral.sh/uv/) are required. Register the
pinned PyPI package:

```bash
codex mcp add catalyst-edge \
  --env 'CATALYST_EDGE_SEC_USER_AGENT=YOUR_ORGANIZATION YOUR_EMAIL' \
  --env 'CATALYST_EDGE_EVIDENCE_STORE=/absolute/local/path/evidence.sqlite3' \
  -- uvx --from 'catalyst-edge-mcp==0.1.4' catalyst-edge-mcp
```

Open a fresh task and confirm discovery of exactly `catalyst_edge_score` and
`catalyst_edge_claim_sources`. The complete Codex, Claude Desktop, privacy, and rollback
procedure is in
[`docs/demo/customer-installation-runbook.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/demo/customer-installation-runbook.md).

## Privacy Policy

Read the [Catalyst Edge Privacy Policy](https://catalyst-edge-mcp.vercel.app/privacy.html).
Tool results and SQLite evidence stay on the user's machine. Ticker and issuer search terms
may be sent directly from that machine to the enabled public-source providers. The policy
describes public-source collection, local and site storage, third-party sharing, retention,
deletion, and contact information. The required SEC identity is sent only to `sec.gov` as
the monitored request `User-Agent`.

## Build and verify from source

Maintainers can verify the source checkout with the locked toolchain:

```bash
uv sync --frozen --extra dev
uv run --frozen pytest
uv run --frozen ruff check .
uv build --no-sources --out-dir dist
```

All default tests are offline. Provider tests use sanitized fixtures and
`httpx.MockTransport`; live credentials are not required. Direct SEC event,
ownership, Form 144, N-CEN, and NPORT parsing plus issuer RSS/Atom collection,
event-graph behavior, and GDELT Web NGrams discovery are implemented with fixed fixtures.
Official-host Bluesky partial-attention collection is also fixture-covered.
Phase 5 sentiment/options gates and 28 dated Phase 6 synthetic contract cases are also
executable offline.

Pull requests and release tags run the required Python 3.10/3.14 offline matrix,
stdio/loopback contract suite, clean build, and installed-artifact verifier in
`.github/workflows/validation.yml`. The workflow has read-only repository permissions
and contains no package publish, release creation, registry, credential, or artifact-upload step.

The same workflow validates the MCPB release candidate with pinned Node/npm and
`@anthropic-ai/mcpb` versions, a locked dependency integrity, zero known npm audit
findings, a fail-closed file inventory, and deterministic ZIP metadata. Maintainers can
run the identical packaging lane from a source checkout:

```bash
npm ci --ignore-scripts
npm audit --audit-level=low
npm run mcpb:validate
npm run mcpb:pack
uv run --frozen python scripts/verify_mcpb.py \
  --bundle dist/catalyst-edge-mcp-0.1.4.mcpb
```

This produces the unsigned custom-extension artifact distributed for Claude Desktop. It is
not a cryptographically verified publisher package.

The live Web NGrams replacement evidence is recorded in
[`docs/validation/gdelt-web-ngrams-live-2026-07-14.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/validation/gdelt-web-ngrams-live-2026-07-14.md).

## Source and provider configuration

| Evidence | Configuration | Behavior when absent |
| --- | --- | --- |
| Direct SEC filings/ownership | `CATALYST_EDGE_SEC_USER_AGENT="Company ops@example.com"` | Required local live-data baseline; missing identity blocks live collection |
| SEC fund identity/N-CEN/NPORT | Same SEC user agent; reviewed SPY/QQQ/DIA/IWM/XLE/XLK/GLD/GDX registry | Official series/class IDs yield neutral as-filed context; absent or inapplicable IDs return typed unsupported status; never uses corporate-insider semantics |
| Reviewed issuer RSS/Atom | Built-in reviewed AAPL/NVDA registry; explicit `CATALYST_EDGE_ISSUER_FEEDS=enabled` opt-in | Disabled by public default pending source-specific output-rights clearance; unregistered tickers make no feed request |
| GDELT Web NGrams discovery | Built-in reviewed AAPL/NVDA/TSLA/RKLB/BRK-A/BRK-B aliases; `CATALYST_EDGE_GDELT=disabled` opt-out | Enabled by public default with mandatory GDELT citation/linking; refresh is out of band and request-time reads are cache-only |
| Bluesky partial public attention | Reviewed exact aliases; explicit `CATALYST_EDGE_BLUESKY=enabled` opt-in | Disabled by public default; opt-in uses forward-only local collection, 14-day derived-cache retention, operator deletion, and neutral-only output |
| Mastodon attention | Reviewed-instance registry required | No instance is composed: measured representative coverage has not justified an allowlist |
| FMP and Finnhub | Key plus recorded policy approval | Keys alone do not establish commercial rights and are not composed by default |
| FlowAlgo/CheddarFlow/future OPRA vendor | Key plus recorded transaction-and-quote license | Otherwise `options_flow` is `licensed_feed_required` |
| User-supplied OHLC | Recorded provider/license approval | Otherwise `technical` is `licensed_feed_required` |
| Options selection | `CATALYST_EDGE_OPTIONS_PROVIDER=none\|auto\|flowalgo\|cheddarflow\|yfinance` | Defaults to `none`; yfinance is private diagnostic only and receives no scored evidence or coverage credit |
| Sentiment model | `CATALYST_EDGE_SENTIMENT_MODEL=disabled` | Must remain disabled: no audited candidate passes rights, Python, preprocessing, labeled-quality, rounding, and threshold gates |

Provider credentials are read only from this process environment. They are never
loaded from `../prior service`, logged, or returned in raw signals.

Copy the checked-in template, populate the SEC identity, then export it into the
current shell. The template enables attributed GDELT discovery and leaves issuer feeds
and Bluesky disabled:

```bash
cp .env.example .env
# Edit .env without committing it, then:
set -a
source .env
set +a
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
| `CATALYST_EDGE_ISSUER_FEEDS` | `disabled` | Explicit opt-in only after source-specific rights and output review |
| `CATALYST_EDGE_GDELT` | `enabled` | Attributed, neutral discovery metadata; set to `disabled` to opt out; request reads are cache-only and refresh is out of band |
| `CATALYST_EDGE_GDELT_REFRESH_SECONDS` | `300` | Period between bounded background attempts; 60–86,400 seconds |
| `CATALYST_EDGE_GDELT_LOOKBACK_DAYS` | `14` | Event-store reporting window used by each background refresh; 1–90 days |
| `CATALYST_EDGE_GDELT_MAX_AGE_SECONDS` | `900` | Last-success age after which request-time cache health becomes stale; must be at least the refresh interval |
| `CATALYST_EDGE_BLUESKY` | `disabled` | Explicit opt-in to ranked, incomplete partial public attention; no request-time network call |
| `CATALYST_EDGE_BLUESKY_REFRESH_SECONDS` | `21600` | Out-of-band completed-day refresh cadence; six hours by default |
| `CATALYST_EDGE_BLUESKY_MAX_AGE_SECONDS` | `43200` | Fail-closed maximum age since the last collector check |
| `CATALYST_EDGE_REGISTRY_PATH` | Packaged `reviewed_registries.json` | Optional local JSON replacing the complete reviewed issuer/feed/discovery/social/publisher registry; invalid or ambiguous entries fail startup |
| `CATALYST_EDGE_EVIDENCE_STORE` | `~/.local/state/catalyst-edge-mcp/evidence.sqlite3` | Local SQLite/WAL collector state, canonical event graph, immutable claim/source relations, and entity-decision audit |
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

GDELT uses reviewed company entity rules and the official downloadable Web NGrams feed at
`storage.googleapis.com/data.gdeltproject.org/gdeltv5/weblegacy/ngrams`. The legacy
DOC 2.0 endpoint now directs high-traffic callers to these files, so local MCP
requests remain cache-only while `catalyst-edge-refresh-gdelt` scans the newest
bounded minute index/TOC pairs out of band. Each pair is downloaded once and matched
against all requested issuers. A deterministic ruleset-versioned decision accepts or
rejects each valid TOC candidate before ingestion. Accepted body-context matches must
also name a reviewed issuer alias or non-single-letter ticker in the surfaced publisher
title; otherwise they are audited as `title_not_aligned`. The cache-read path applies
the same check so legacy tangential titles stop surfacing without deleting audit history.
Exact HTTPS host/path validation,
compressed and decompressed byte ceilings, a five-file run limit, a 200-candidate
per-issuer audit cap, and a separate 50-accepted-document ingestion cap bound the
work without allowing false positives to starve later valid matches. Only publisher
titles, timestamps, domains, hashes, HTTPS links, and derived entity-decision metadata
are retained; article bodies and ngram context are never stored. Accepted and rejected
decisions are appended idempotently to `entity_match_audit`; a ruleset or context
change creates a new audit record rather than overwriting history. HTTP, timeout,
malformed schema, and missing-file states remain typed and preserve cached evidence.
A reject-only refresh is a fresh successful collection with no observations, not a
provider failure. Discovery observations merge into the same 48-hour canonical graph
but remain below SEC and issuer-primary sources in global ranking. Previously cached
v1 observations are not destructively purged and age out under the configured lookback.

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
unauthenticated AppView hosts; no proxy, scraper, account, or credential path exists.
The six-hour out-of-band lifecycle queries one bounded first page for the previous
completed UTC day and never follows a cursor. Each daily bucket deduplicates AT URIs,
counts unique authors, and retains counts, pseudonymous SHA-256 identifiers, response
hash, coverage/outage state, and at most three representative links—not post bodies.
Buckets auto-prune to the 14 completed days needed for two equal seven-day windows;
`catalyst-edge-purge-bluesky-cache TICKER...` deletes the local buckets and collector
state on request. Missing days, reported hit overflow, upstream failures, stale state,
or disappeared URI hashes fail closed. Until 14 consecutive adequate forward buckets
exist, output explicitly reports `warm_up`. Even after warm-up, each seven-day window
must contain at least five posts from three unique authors. Search is ranked and
incomplete, so output is always labeled partial public attention, remains neutral, and
never claims sentiment or market-wide coverage. MCP requests read cache only.
Mastodon remains uncomposed because no
reviewed instance set was available to establish representative cross-instance
coverage; no instance is treated as a global index.

Phase 5 reviewed Finnhub sentiment, TextBlob, VADER, DistilBERT SST-2, and
ProsusAI FinBERT. None passes every rights, input-data, compatibility,
preprocessing, labeled-quality, rounding, and threshold gate, so no sentiment
adapter is composed. FlowAlgo and CheddarFlow also remain uncomposed: public
terms do not grant the required automated extraction, storage, redistribution,
and derived-output rights. The local composition root therefore never calls an
options provider before policy evaluation. See
[`docs/audits/phase5-capability-gates-2026-07-13.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/audits/phase5-capability-gates-2026-07-13.md).

Phase 6 validates 28 dated, sanitized synthetic product-contract cases covering strong and
weak bullish evidence, bearish material events, neutral issuer/discovery items,
insider clusters, Form 144 intent, missing/stale/provider failures, Bluesky
historical warm-up/outage/sample regressions, contradictions, rejected sentiment, and
unlicensed options/technical missingness. All 28 expected-versus-produced
assertions pass. A separate 25-case real SEC product evaluation now covers the
primary-source gate. See
[`docs/validation/phase6-historical-validation-2026-07-13.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/validation/phase6-historical-validation-2026-07-13.md).

The real-case evaluation, semantic corrections, offline suite, live target
cohort, fresh GDELT health, and final RKLB `launch_ready=true` smoke are recorded
in [`docs/validation/real-catalyst-evaluation-2026-07-15.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/validation/real-catalyst-evaluation-2026-07-15.md)
and [`docs/validation/local-product-completion-2026-07-15.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/validation/local-product-completion-2026-07-15.md).

The live evidence-semantic launch gate passed for RKLB on 2026-07-14 from
merged `main`; the other four acceptance tickers correctly remained
fail-closed. See
[`docs/validation/live-launch-acceptance-2026-07-14.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/validation/live-launch-acceptance-2026-07-14.md).

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
  "attributions": [],
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
  "attributions": [],
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

Full canonical no-data response example (with every evidence source absent or disabled):

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
  "attributions": [],
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

See [technical specification](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/technical specification) for exact formulas, provider contracts, compactness rules, and
the Flask migration design that intentionally remains outside this repository.
