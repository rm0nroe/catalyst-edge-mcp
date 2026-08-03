# Catalyst Edge MCP - Handoff PRD

## Repository Context

This document lives in the implementation target directory:

```text
/Users/ryanmonroe/Desktop/dev/catalyst-edge-mcp
```

Build the MCP implementation in this directory. Treat `analysis-api` as a sibling reference/source repository:

```text
/Users/ryanmonroe/Desktop/dev/
  analysis-api/
  catalyst-edge-mcp/
```

The implementation should copy or adapt only the code patterns that are needed from `../analysis-api`. Do not turn this directory into a broad clone of `analysis-api`.

## Ticket Summary

Retrofit the existing CCE endpoint concept from sibling repo `../analysis-api` into a standalone MCP tool that produces a source-linked catalyst edge dossier for a ticker. The goal is not to expose the current Flask endpoint through MCP as-is. The goal is to reuse the existing CCE skeleton where useful, replace the untrusted scoring path, and return an evidence-first output that an agent can use for investment research, alert triage, or thesis review.

## Current Implementation Status — 2026-07-21

The free-source research and subsequent implementation established a sufficient
zero-subscription capability set for the current local-only product: direct SEC
filings and insider records plus reviewed issuer-feed, GDELT Web NGrams, and
forward-collected Bluesky partial-public-attention adapters. Local stdio/HTTP MCP transports, strict
contracts, provenance, typed missingness, the canonical event graph, and
deterministic scoring are implemented. The public self-serve configuration is
fail-closed: SEC is composed only when the user supplies a monitored identity,
while issuer feeds, GDELT, and Bluesky are disabled unless explicitly enabled.
Bluesky opt-in uses a local out-of-band collector; MCP requests never call AppView.

The zero-subscription implementation meets the current bounded local PRD
acceptance corpus as of 2026-07-16. Evidence-specific synthesis, the automatic
local GDELT refresh/freshness lifecycle, strict local registry configuration,
publisher-domain quality tiers, and a 25-case real SEC catalyst evaluation are
implemented. The real evaluation complements the 28 sanitized Phase 6 contract
fixtures and records primary-link, classification, freshness, distinct-event,
research-value, and dossier-direction results. Item 8.01 document enrichment is
a versioned allowlist of supported semantics, not general filing understanding.

GDELT entity-resolution registry v2 is also implemented. Reviewed per-alias context,
exclusion, validity, CIK, and provenance rules now produce a deterministic decision
before ingestion. Body-context matches must also align to a reviewed issuer alias or
non-single-letter ticker in the surfaced publisher title; tangential titles fail closed
as `title_not_aligned`. Accepted/rejected candidate metadata is retained in an
append-only, retry-idempotent audit table without publisher bodies or raw NGram text.
This improves discovery precision and creates a future replay input; it does not make
the operational event graph a point-in-time backtest dataset.

Grouped-source recovery and scoped disposition diagnostics are implemented. Each
grouped operational event has an immutable claim ID and exact supporting-source
count; the bounded `catalyst_edge_claim_sources` query recovers every source ID and
accession/record through cursor pages. Dossiers also expose the complete ordered
set of scoped `observed_none`, `source_unavailable`, `source_unsupported`,
`entity_rejected`, `discovery_only`, and `evaluated_not_material` records. These
diagnostics do not create a RESEARCH NOW/MONITOR/IGNORE product classification.

The distinct SEC-backed ETF/fund lane is implemented for SPY, QQQ, DIA, IWM,
XLE, XLK, GLD, and GDX. Five funds resolve official CIK plus series/class IDs
and parse N-CEN/NPORT filings into neutral, research-only evidence with as-filed
chronology. SPY and DIA resolve CIKs but have no official series/class mapping;
GLD is outside the N-CEN/NPORT investment-company lane. These return typed
unsupported reasons, and reviewed fund tickers never enter the corporate filing
or insider-transaction semantics.

The evaluation did not justify changing numeric scorer weights because it has no
forward-return labels. Preserving the deterministic, explicitly unbacktested
weights is the recorded tuning decision rather than implying unsupported outcome
calibration.

For the current owner-operated local build, paid options flow, licensed OHLC,
sentiment, hosted deployment, packaging, CI, consumer distribution, broader SEC
semantic extraction, and the sibling Flask migration are optional future
extensions rather than blockers for this acceptance boundary. Their absence
must remain explicit typed missingness and must never be fabricated as evidence.

## Problem

The sibling `../analysis-api` repo already has a CCE route that collects ticker signals, extracts features, combines them, predicts an edge score, stores the result, and returns catalyst details. The route shape is useful, but the current model is not product-grade: the CCE model manager initializes random weights and the score is therefore not commercially or analytically trustworthy.

At the same time, generic finance APIs, OpenBB-style data layers, SEC MCP servers, Quiver, Unusual Whales, Form4API, OpenInsider, and other products already cover raw market data, filings, insider activity, options flow, and generic sentiment. A valuable MCP tool must therefore be an evidence synthesis and confidence tool, not another wrapper around commodity data.

## Existing Code Starting Points

- Route skeleton: `../analysis-api/trading/api/cce_routes.py`
  - `GET /api/cce/<ticker>` starts at `get_edge_score`.
  - Existing flow: collect signals, process features, combine features, predict edge score, store raw signals, return score plus catalysts.
- CCE feature code: `../analysis-api/trading/cce/feature_engineering.py`
  - Existing feature families include options flow, insider trading, social sentiment, technical indicators, filings, and alternative data.
- Current scoring caveat: `../analysis-api/trading/cce/gat_model.py`
  - `CCEModelManager._initialize_model()` currently initializes random weights and explicitly notes that production should load pre-trained weights.
- Related data integrations:
  - Insider trading analyzer: `../analysis-api/trading/features/insider_trading/analyzer.py`
  - Social sentiment analyzer: `../analysis-api/trading/features/social_sentiment/analyzer.py`
  - Events analyzer: `../analysis-api/trading/features/events/analyzer.py`
  - Options flow analyzer: `../analysis-api/trading/features/options_flow/analyzer.py`
  - Market/trending aggregators where useful: `../analysis-api/trading/features/trending_aggregator.py`

## Product Goal

Create an MCP tool named `catalyst_edge_score` that answers:

> "For this ticker, what recent catalyst evidence exists, how strong is it, what changed, what sources support it, what confidence should an agent assign, and what should be checked next?"

The first implementation should be useful even before a trained model exists by using deterministic, documented scoring rules and explicit confidence limitations. A later implementation can replace the deterministic scorer with a calibrated model after backtesting.

## Non-Goals

- Do not port all of `analysis-api` into MCP.
- Do not expose commodity endpoints like quote, chart, financial ratios, basic technicals, or generic news summary.
- Do not present the current random-weight CCE model as valid.
- Do not generate buy/sell recommendations.
- Do not claim alpha, performance, or investment advice.
- Do not depend on MediaCrawler or ai-berkshire for the first TDD unless the implementation plan explicitly adds optional adapters.
- Do not build a UI.

## Target Users

- Agentic investment research workflows that need a compact, source-linked catalyst summary.
- Analysts or builders who already have raw data but need a reproducible evidence packet.
- Internal tools that need "why is this ticker moving or worth reviewing?" rather than a full equity research report.

## MCP Tool Contract

### Primary Tool Name

`catalyst_edge_score`

### Supporting provenance query

`catalyst_edge_claim_sources` accepts an immutable `claim_id`, nonnegative cursor,
and page limit from 1–20. It returns every source ID, accession/record ID, canonical
URL, publication/observation/retrieval time, hash, parser version, and policy
decision counted by that grouped claim. It does not recollect providers or alter
scoring.

### Input

```json
{
  "ticker": "NVDA",
  "lookback_days": 14,
  "include_sources": true,
  "include_raw_signals": false,
  "risk_mode": "research"
}
```

### Input Rules

- `ticker`: required, validated using the existing secure ticker validation.
- `lookback_days`: optional, default 14, max 90.
- `include_sources`: optional, default true.
- `include_raw_signals`: optional, default false. Raw payloads should be bounded and redacted for size.
- `risk_mode`: optional enum.
  - `research`: neutral language, evidence and caveats.
  - `alert_triage`: emphasize what changed and why it may matter.
  - `thesis_review`: emphasize whether the evidence could change a prior thesis.

### Output

```json
{
  "ticker": "NVDA",
  "as_of": "2026-07-12T16:00:00Z",
  "lookback_days": 14,
  "edge": {
    "score": 67,
    "direction": "bullish",
    "confidence": 0.62,
    "horizon_days": 5,
    "scoring_method": "deterministic_v1",
    "model_status": "not_trained"
  },
  "summary": {
    "headline": "Options and news momentum strengthened, but insider evidence is weak.",
    "what_changed": [
      "Options volume rose versus recent baseline.",
      "Recent filing/news catalyst appears relevant.",
      "No confirming insider cluster found."
    ],
    "why_it_matters": "Multiple independent evidence families point to increased catalyst attention, but the signal lacks insider or high-quality filing confirmation.",
    "what_would_invalidate": [
      "Options flow normalizes within 1-2 sessions.",
      "Primary source filing does not support the market narrative.",
      "Price move is fully explained by broad sector beta."
    ]
  },
  "evidence": [
    {
      "family": "options_flow",
      "signal": "unusual_call_activity",
      "strength": 0.74,
      "confidence": 0.58,
      "timestamp": "2026-07-12T15:45:00Z",
      "source_count": 1,
      "sources": [
        {
          "name": "options_flow_analyzer",
          "url": null,
          "observed_at": "2026-07-12T15:45:00Z"
        }
      ],
      "notes": "Source quality depends on the configured options provider."
    }
  ],
  "data_quality": {
    "coverage": "partial",
    "missing_families": ["insider_trading"],
    "stale_families": [],
    "warnings": [
      "Current deterministic score is not backtested.",
      "No investment recommendation is provided."
    ]
  },
  "next_checks": [
    "Verify primary filing or company announcement.",
    "Check whether move is sector-wide.",
    "Review liquidity and options data source quality."
  ]
}
```

## Required Behavior

1. Validate ticker and input parameters before invoking data collectors.
2. Collect available signal families with bounded timeouts and graceful partial failure.
3. Normalize each signal family into a common evidence schema.
4. Compute a deterministic v1 score only from available evidence.
5. Return explicit data-quality warnings when evidence is missing, stale, low confidence, or unbacktested.
6. Include source/provenance fields wherever the underlying integration can provide them.
7. Avoid investment-advice wording. Use "evidence suggests", "may warrant review", and "confidence" language.
8. Make model status visible. Until a trained model exists, return `model_status: "not_trained"`.
9. Keep output compact enough for agent context, with optional raw signal inclusion.
10. Be testable without live external APIs by injecting or stubbing collectors.

## Suggested Architecture

### New MCP Layer

Add a small standalone MCP server in this `catalyst-edge-mcp` directory rather than modifying the existing Flask route first. The implementation agent should inspect the new repo's dependency and packaging setup before finalizing the exact layout, but a likely shape is:

```text
catalyst_edge_mcp/
  __init__.py
  server.py
  tools/
    catalyst_edge_score.py
  schemas/
    catalyst_edge.py
tests/
  ...
pyproject.toml
README.md
```

### Internal Service Layer

Create a service that can be used by both MCP and the existing Flask route later:

```text
catalyst_edge_mcp/cce/
  catalyst_service.py
  evidence_schema.py
  deterministic_scorer.py
  provenance.py
```

The MCP tool should call the service. The Flask route in `../analysis-api` can be migrated later to call this service or share a packaged library, but that migration is a follow-up unless explicitly added to scope.

### Collector Adapter Interface

Define a thin interface for signal adapters:

```python
class CatalystSignalAdapter(Protocol):
    family: str
    def collect(self, ticker: str, lookback_days: int) -> EvidenceFamilyResult:
        ...
```

Initial adapters can wrap, copy, or reimplement the relevant logic from `../analysis-api` CCE orchestrator/analyzers, but they must normalize outputs into the common evidence schema. Prefer clean, testable adapters over importing large Flask/runtime dependencies from `analysis-api`.

## Deterministic Scoring v1

Use an intentionally simple scoring model for the first MCP version:

- Start from neutral score 50.
- Add/subtract bounded contributions from each evidence family.
- Weight by evidence strength, confidence, recency, and source quality.
- Apply penalties for missing high-value confirming families.
- Cap output to 0-100.
- Return contribution breakdown in the evidence objects.

The TDD should define the exact formula. Keep it explainable and stable. This is a bridge until a trained and backtested model exists.

## Optional Future Adapters

These are not part of the first implementation unless explicitly added to scope:

- MediaCrawler adapter for public Chinese/social-platform evidence.
  - Useful for China consumer, policy, platform, supply-chain, and crowd-pressure catalysts.
  - Must resolve licensing/commercial-use constraints before any paid deployment.
- ai-berkshire judgment adapter.
  - Useful for output rubrics: moat impact, management impact, thesis-change severity, inversion risks, data confidence.
  - Treat as decision framework/corpus, not market data.

## TDD Requirements For Next Agent

The implementation agent should write a detailed TDD before coding. The TDD should cover:

1. Exact MCP server framework and package entrypoint.
2. File/module layout.
3. Tool schema and JSON schema validation.
4. Service interfaces and dependency injection design.
5. Evidence normalization schema.
6. Deterministic scoring formula.
7. Timeout and partial-failure behavior.
8. Source/provenance handling.
9. Data-quality warnings.
10. Test plan with fixtures and mocks.
11. Migration path for the existing Flask `/api/cce/<ticker>` route in `../analysis-api`.
12. Security/compliance language guardrails.

## Acceptance Criteria

- MCP tool `catalyst_edge_score` can be called locally with a ticker and returns the contracted output shape.
- Tests pass without live API keys.
- Unit tests cover:
  - ticker validation
  - parameter defaults and bounds
  - all-success evidence collection
  - partial collector failure
  - no-data response
  - deterministic scoring contribution math
  - source/provenance formatting
  - `include_raw_signals` false by default
  - no buy/sell recommendation language in generated summary
- Existing CCE Flask route in `../analysis-api` is not modified or broken unless route migration is explicitly included.
- Current random-weight model is not used for production MCP scoring.
- Output includes `scoring_method` and `model_status`.
- Documentation includes a local run example and a sample MCP response.

## Suggested Test Fixtures

Create small deterministic fixtures for:

- Strong multi-source bullish catalyst.
- Weak single-source social-only catalyst.
- Bearish filing/news catalyst.
- Missing insider data.
- Stale options data.
- Collector timeout.
- Invalid ticker.

## Open Questions

- Which MCP Python SDK/version should this repository standardize on?
- Should the first tool be read-only local-only, or exposed through a hosted service wrapper?
- Which existing collectors are reliable enough to wrap in v1?
- Should the existing `/api/cce/<ticker>` route be migrated in the same PR or kept separate?
- What data vendors are legally available in the deployment environment?
- Should the scorer be purely deterministic v1, or should it support a pluggable trained model interface immediately?

## Recommended First Implementation Slice

1. Add schemas and deterministic scorer with full unit tests.
2. Add fake adapters/fixtures and service orchestration tests.
3. Add MCP tool wrapper around the service.
4. Wire one or two existing real adapters only after the service is tested.
5. Add docs and local run instructions.
6. Leave Flask route migration for a follow-up PR unless the TDD proves it is low risk.

## Definition Of Done

The PR meets this local acceptance boundary when another agent can call the MCP
tool locally, receive a compact source-linked catalyst dossier, and inspect
tests proving that the score is deterministic, caveated, and not using the
current random-weight CCE model. Collector and semantic coverage must remain
explicitly bounded: unsupported or ambiguous primary-document wording stays
generic and does not receive a guessed event classification.
