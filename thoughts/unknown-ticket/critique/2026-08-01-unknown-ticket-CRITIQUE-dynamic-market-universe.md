# Dynamic Market-Aware Universe Design Critique

**Target**: `thoughts/unknown-ticket/design/2026-08-01-CATALYST-WATCHLIST-TDD-dynamic-market-universe.md`
**Status**: Historical design review. Later status reconciliation does not change the provider-neutral architecture or its activation gates.

## Iteration 1

The substantive review found six contract blockers and related operational gaps.

| Finding | Resolution |
| --- | --- |
| Self-referential and timestamp-dependent universe hash | Split the immutable logical payload from its publication envelope; hash only canonical payload bytes and derive IDs afterward. |
| A second builder could replace an already accepted universe | Added temporary-directory promotion, directory `fsync`, non-overwriting rename, per-session lock, first-writer compare-and-swap, typed conflict, and explicit supersession constraints. |
| Fallback and multi-category ownership were nondeterministic | Removed unmatched broad-market fallback; added audited adjacency, deterministic primary-category assignment, mapped reserves, and golden allocation fixtures. |
| Retry could mix service revisions and evidence epochs | Added a persisted scan-contract hash, fixed start time, runtime/input revisions, resume TTL, and failure after expiry. |
| Completed-scan and delivery semantics conflicted | Separated commit, report readiness, delivery receipt, and byte-identical delivery retry with stable IDs. |
| Global discovery watermark breaks out-of-order recovery | Replaced it with immutable per-slot windows and durable same-day ticker/CIK exclusion. |

The revision also made source approval and automated research/audit runtime machine-verifiable Phase 0 blockers; defined application-level integrity boundaries; added untrusted-network/parser controls; normalized provider semantics; versioned strict schemas; made migration accept the current version-2 state and older unversioned legacy state without rewriting either; and added calendar, lock, freshness, stage-deadline, migration, and rollback contracts.

The final tightening defined audit independence as a different provider/model family or deterministic source verifier and removed share-class exceptions from v1, preserving exactly 900 unique CIKs.

No production source adapter or research runtime is represented as approved by this design. Implementation remains shadow-only until both Phase 0 records validate.

## Iteration 2

The second review found three remaining contradictions: content-addressed payload reuse was mixed with attempt-specific envelope bytes, the 500-record reserve cap was worded against the whole accepted set, and stable scan identity still inherited a wall-clock start time. The revision separated payload/attempt/acceptance storage, defined exact core/reserve/total bounds, and bound each cohort to a schedule-derived scan ID before scoring.

It also made external delivery explicitly at-least-once without provider idempotency, expanded the scan-contract hash to all behavior-changing inputs, assigned per-use source approvals to the watchlist repository, specified authorized pre-scan pointer supersession, named `dynamic_state.json` schema version 1, added a pre-commit `scoring` state, required calendar provenance/coverage, and added fault-injection contract tests for each corrected boundary.

## Iteration 3

The final substance pass found one out-of-order recovery race in supplemental discovery. The revision added an atomic session-wide ticker/CIK reservation ledger before every supplemental dossier call, claim reuse during recovery, release only when no dossier was persisted, and a failure-injection test spanning a partial earlier scan, later slot, and earlier-slot recovery.

## Readability Pass

The editorial pass added a six-step overview, a terminology table, stable invariant IDs, grouped contract tests, schedule/freshness tables, and explicit live-only evidence labeling. It moved implementation phases after validation and acceptance, clarified the `open` slot label, reconciled the 2,586 metadata count with 2,591 raw parsed rows, normalized `payload_sha256`, and split rollback procedure from guarantees.
