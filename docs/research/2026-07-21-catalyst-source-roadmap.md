# Catalyst Edge source roadmap

**Date:** 2026-07-21
**Inputs:** [free/open-source coverage research](./2026-07-21-free-open-source-coverage-research.md) and [point-in-time backtest dataset research](./2026-07-21-point-in-time-backtest-dataset-research.md)

## Decision

Catalyst Edge should improve current output quality before adding source volume, then build a provider-neutral replay architecture, and only then purchase/ingest a historical market-data stack.

The selected sequence is:

1. Harden GDELT entity resolution and retain rejected-match audit data; draft the provider-neutral point-in-time replay TDD in parallel.
2. Make grouped-source support and scoped coverage/disposition reasons complete.
3. Add a distinct SEC-backed ETF/fund evidence lane.
4. Prepare the Databento Corporate Actions, Databento Security Master, Tiingo, and terminal-outcome-source rights package; after owner approval to contact vendors, obtain written answers and coverage samples.
5. Run the 50–100-case Stage A timestamp/replay proof.
6. Proceed to 1,000+ observations only after Stage A and the licensed-source gates pass.

No options or retrospective social data is required for the first backtest.

## Source roles

| Lane | Selected role | Boundary |
| --- | --- | --- |
| SEC filings/ownership | Primary evidence and historical availability clock | Freeze accession payload/fact manifests; amendments remain separate versions |
| Issuer/sponsor official surfaces | Reviewed primary evidence | Host-specific rights and incomplete history; store metadata/facts/hashes, not blanket full text |
| GDELT | Discovery/corroboration metadata | Neutral until entity-resolved; never publisher truth or complete article history |
| SEC N-CEN/N-PORT and fund IDs | Fund identity, filings, lagged holdings context | Not real-time holdings and not corporate-insider semantics |
| AT Protocol | Prospective partial-attention corpus | Verify raw repository commits, DID identity, and message-chain continuity; record outages/deletes; no retrospective completeness claim |
| Databento Corporate Actions | Conditional Stage A lifecycle source from 2018-05-01 | Separate $299/month starting price; no presumed terminal-return field |
| Databento Security Master | Conditional Stage A point-in-time identity source | Separate quote/symbol-based price and rights confirmation required |
| Tiingo EOD | Conditional Stage A raw/adjusted daily labels | Published base price is not intended-use clearance; recycled-delist, retention, benchmark/report rights, and total price require an addendum |
| CRSP or equivalent | Required Stage B terminal-outcome/security source | Quote/license required; must cover inactive/delisted identity and terminal returns/final consideration; no assumed redistribution |
| Options | Typed unavailable | Add only with licensed transaction-plus-quote history and appropriate OPRA rights |

## Implementation roadmap

### PR 1 — entity-resolution v2 — implemented locally 2026-07-21

- Per-alias registry rules for alias kind, match mode, required/negative context, validity, canonical CIK, rule version, and review provenance.
- Deterministic GDELT accept/reject decision before event ingestion.
- Append-only rejected-match audit metadata.
- Fixed mutation/regression corpus with the observed TSLA false-positive classes,
  former-name validity, required brand context, retry idempotence, reject-only
  freshness, and rejection non-starvation.
- Implemented gate: all fixed entity-resolution and GDELT regression cases pass.
  The broader 98% precision/85% recall benchmark remains a Stage A corpus gate,
  because the current fixed cases are not large enough to support those estimates.

### PR 2 — provenance and reason completeness — implemented locally 2026-07-21

- Immutable claim IDs plus a paginated claim-source query keyed to every supporting accession/record; compact response pages remain bounded.
- Scoped reason records: `observed_none`, `source_unavailable`, `source_unsupported`, `entity_rejected`, `discovery_only`, `evaluated_not_material`; each includes scope type/ID and deterministic display precedence while retaining all coexisting reasons.
- Expose the ordered reason set through MCP diagnostics; keep RESEARCH NOW/MONITOR/IGNORE mapping in the consuming agent until a separate MCP classification contract is designed. Any backtest of those classes must freeze the consuming owner, policy version, class definitions, and exact mapping.
- Gate: every counted grouped record is recoverable and every degradation fixture maps to its exact expected ordered set of scoped reasons.

Implementation note: the compact evidence context exposes at most 20 supporting
source IDs and an explicit truncation flag; `catalyst_edge_claim_sources` recovers
the complete relation in pages of at most 20. Reason records retain all six codes,
stable IDs, explicit scopes, precedence, total count, and truncation state without
changing scorer or downstream classification semantics.

### PR 3 — ETF/fund lane

- CIK + SEC series/class identity with historical ticker/status versions.
- N-CEN and N-PORT as-filed parsing with report/end/filing timestamps.
- Reviewed sponsor-primary notices for SPY, QQQ, DIA, IWM, XLE, XLK, GLD, and GDX.
- Gate: every named fund resolves official IDs or an explicit unsupported reason; no corporate-insider inference.

### TDD addendum — point-in-time replay

Define before implementation:

- Content-addressed raw/fact manifests and append-only dataset versions.
- Bitemporal evidence, identity, correction, policy, registry, and scorer/config records.
- Market-session cutoff and conservative next-open entry convention.
- Raw/adjusted price, corporate action, delisting/terminal, 1/5/20-day, SPY/sector-relative, MFE/MAE, and cost labels.
- Train/validation/untouched-test split and one-time test opening; freeze `deterministic_v1` and every candidate scorer before the shared unseal, and require a new future holdout for later models.
- Exact underlying/signal-signed return, split/dividend, neutral-signal, MFE/MAE path, rounding, and scenario cost formulas sufficient for byte-identical labels.
- Clean-room reproducibility and license-aware fixture strategy.

### Stage A — 50–100 cases

Draft the provider-neutral TDD now, but do not implement Stage A until the identity, lifecycle, price, retention, and derived-use rights are confirmed. Keep deliberately selected inactive/delisted/ticker-recycled cases in a separate terminal audit set rather than the performance sample. Every timestamp, identity interval, replayed dossier, session mapping, and label is manually audited.

### Stage B — 1,000+ cases

Target 2018-05-01–2025 with event observations plus matched controls selected from a point-in-time active/inactive universe. Stage B requires CRSP or a verified equivalent terminal-outcome source. Freeze unchanged `deterministic_v1`; any tuning is a separately versioned scorer. Publish negative results and uncertainty.

## Approval and procurement gate

Before any purchase, obtain written answers for Databento Corporate Actions, the separate Databento Security Master, Tiingo, and a Stage B terminal-outcome source led by CRSP on:

- Separate product pricing, point-in-time identifiers, corrections, inactive/delisted coverage, ticker recycling, and final consideration/delisting returns.
- Raw and normalized retention after subscription termination.
- Internal team/process access.
- Use for backtesting, calibration, and model training.
- Publication of aggregate benchmark results.
- Hosted derived outputs, citations, and redistribution fees.

After the owner approves vendor contact, request a 25-symbol sample spanning active, renamed, merged, acquired, bankrupt, delisted, ticker-recycled, ETF, ADR, split, and special-distribution cases. The owner separately approves one rights/price package before purchase.

## Product claims gate

- Until Stage B: `deterministic_v1`, `not_trained`, `unbacktested`.
- After a compliant Stage B with negative predictive results: `backtested; no demonstrated predictive edge`.
- The controlling primary claim metric is pre-registered in the TDD before labels are joined; the recommended default is the 20-session net SPY-relative return difference between the highest pre-registered signal bucket and matched controls. Its ticker-clustered/date-block-bootstrap 95% confidence interval must be above zero on the one-time untouched test. Directional improvement, rank correlation, concentration, and walk-forward stability remain required supporting diagnostics, but do not replace the primary gate.

## Current recommendation

**PR 1, PR 2, and the provider-neutral replay TDD are now complete locally. Implement
PR 3 next.** Prepare—but do not send or purchase without owner approval—the four-part
rights questionnaire and sample request. Vendor-specific mappings wait for returned
rights/coverage answers; Stage A implementation waits for the approved source contract.
