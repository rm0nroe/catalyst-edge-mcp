---
date: 2026-07-21
type: self-critique
target: /Users/ryanmonroe/Desktop/dev/catalyst-edge-mcp/TDD.md
target_type: design
ticket: unknown-ticket
---

# Self-critique log: Point-in-time replay and backtest addendum

**Target**: [TDD.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/TDD.md)

## Cycle 1 — 2026-07-21

**Cross-stage checks**: research ✓

**Found**: 4 blockers, 3 risks, 1 gap

**Addressed**:

- Validation carve-out: executed the provider-neutral cutoff and canonical-serialization contract against all 25 recorded official-SEC cases and added measured results to §17.9.
- Byte identity: defined canonical JSONL ordering, timestamps, decimal precision, rounding, missing values, adjustment precedence, and exact scenario-cost formulas in §17.4.
- Predictive claim: restored mandatory monotonicity, walk-forward stability, and concentration gates in §17.7.
- Stage dependencies: required entity-resolution/rejection auditing, scoped reasons, immutable source recovery, and approved data rights before Stage A in §17.7.
- Physical architecture: specified the replay module boundary, content-addressed objects, canonical JSONL, Parquet, DuckDB, SQLite catalog, adapter failure contract, and core cardinalities in §17.4.
- Corpus fidelity: restored universe, liquidity, control-exclusion, regime, Stage A composition, and terminal-audit requirements in §17.6.
- Multiple testing: restored attempted-variant logging, fold requirements, and secondary-search corrections in §17.6.
- Availability and entry semantics: defined allowed proof types, conflict/null behavior, conservative proof time, the 15-minute buffer, and exact session-open selection in §17.5.

**Deferred**:

- Empirical market-session, returns, adjustment, terminal-outcome, provider-correction, coverage, and rights validation remains blocked on approved provider samples and contracts; §17.9 names each boundary explicitly.

## Cycle 2 — 2026-07-21

**Cross-stage checks**: research ✓

**Found**: 2 blockers, 3 risks, 1 gap

**Addressed**:

- Reproducibility: added `scripts/validate_replay_contract.py`, its exact command, and a content-derived observation-ID algorithm; refreshed the measured canonical hash in §17.9.
- Stage separation: split Stage A market-component concerns from Stage B terminal-source semantics and pricing in §17.9.
- Immutable IDs: defined namespaced derivation and collision handling for observation, dataset, evaluation, and label IDs in §17.4.
- Event diversity: restored the upstream requirement of at least 20 distinct event types in Stage A.
- ETF prerequisite: required completion of the SEC-backed fund identity/evidence lane before any ETF enters Stage A.
- Coverage denominator: defined predeclared family-by-observation evaluability cells, treatment of `observed_none`, uncovered statuses, and the prohibition on narrowing claims after results.

**Deferred**:

- No new deferrals; the remaining empirical vendor-dependent checks retain the Cycle 1 boundary.

## Cycle 3 — 2026-07-21

**Cross-stage checks**: research ✓

**Found**: 2 blockers, 1 risk, 0 gaps

**Addressed**:

- Canonical byte surface: changed the validator from one JSON array to one canonical record per JSONL line.
- Eligibility validation: made the validator execute the documented `max(accepted_or_published_at, historically_available_at) <= evaluation_at` predicate against each normalized record immediately before and at acceptance.
- Correction identity: split stable `observation_key` from versioned `observation_id`, with provider version or payload/fact hash and explicit correction lineage.

**Deferred**:

- None. The hard-cap findings were applied directly; no further substance-critic cycle was run.
