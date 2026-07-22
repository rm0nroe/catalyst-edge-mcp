---
date: 2026-07-21
type: self-critique
target: /Users/ryanmonroe/Desktop/dev/catalyst-edge-mcp/docs/research/2026-07-21-catalyst-source-roadmap.md
target_type: research
ticket: unknown-ticket
---

# Self-critique log: Catalyst Edge source and backtest research

**Targets**: [coverage research](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-free-open-source-coverage-research.md), [backtest research](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-point-in-time-backtest-dataset-research.md), and [source roadmap](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-catalyst-source-roadmap.md)

## Cycle 1 — 2026-07-21

**Cross-stage checks**: repository source map and both research tracks reviewed

**Found**: 10 blockers/risks and 1 wording issue

**Addressed**:

- Split Databento Corporate Actions from the separately priced Security Master and removed the unsupported `$349/month` bundle conclusion.
- Reclassified Databento plus Tiingo as a conditional Stage A candidate and required CRSP or an equivalent terminal-outcome source for Stage B.
- Moved the corpus start to 2018-05-01 and separated future-conditioned terminal audit cases from the performance sample.
- Added `historically_available_at` and `reconstructed_at`, plus a contemporaneous-archive admissibility rule for historical issuer evidence.
- Replaced point-in-time sector/size assumptions with price/dollar-volume matching unless contemporaneous classifications are available.
- Required zero known critical timestamp, identity, and terminal-outcome errors.
- Made entity rules per-alias, harmonized the 98% precision/85% recall gate, and required at least 300 labeled candidates.
- Made rejection history append-only, replaced the bounded source appendix with immutable claim IDs plus pagination, and clarified downstream classification ownership.
- Added current GDELT Web NGrams provisional status and full AT Protocol verification requirements.
- Allowed the provider-neutral TDD to proceed in parallel while keeping vendor mappings, contact, purchase, and ingestion gated.

**Deferred**:

- Vendor-specific schema mappings and exact prices remain blocked on approved vendor contact, returned samples, and written rights.

## Readability pass — 2026-07-21

**Found**: 5 major and 5 minor findings

**Addressed**:

- Defined classification owner/policy version and froze class definitions and mappings for any downstream-class evaluation.
- Made reason codes scoped and multi-valued with deterministic display precedence.
- Required all candidate scorers to be frozen before one shared untouched-test unseal.
- Gated both the vendor questionnaire and sample request on owner approval.
- Defined split/dividend, sign, neutral, MFE/MAE, and scenario-cost label conventions.
- Aligned roadmap sequencing, clarified replay-availability assertions, disambiguated the ETF-lane implementation, and named the recommended primary predictive metric.

**Deferred**:

- A full glossary was not added because the expanded first-use descriptions and source links keep the decision sections actionable without materially lengthening the reports.
