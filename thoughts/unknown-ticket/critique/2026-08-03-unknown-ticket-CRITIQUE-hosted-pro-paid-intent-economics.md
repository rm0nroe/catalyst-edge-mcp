---
date: 2026-08-03
type: self-critique
target: /Users/ryanmonroe/Desktop/dev/catalyst-edge-mcp/thoughts/unknown-ticket/research/2026-08-03-RESEARCH-hosted-pro-architecture.md
target_type: research-follow-up
ticket: unknown-ticket
---

# Self-critique log: Hosted Pro paid-intent economics

**Target**: `thoughts/unknown-ticket/research/2026-08-03-RESEARCH-hosted-pro-architecture.md`

## Cycle 1 — 2026-08-03 16:00 EDT

**Found**: 1 blocker, 3 risks, 2 gaps

**Addressed**:

- **Cumulative gate cost:** each later gate now covers all prior irreversible spend; the
  rounded gates changed from 300/1,000/8,000 to 350/1,350/8,600.
- **Activation loss:** removed visitor-equivalent claims because the activation-link rate is
  unknown.
- **Conversion timing:** added a three-month lag and reduced the revenue horizon to 21 paid
  months while retaining 24 months of fixed cost.
- **Retention mismatch:** all survival inputs are now GRR sensitivities; B2B NRR is not used
  in the curve.
- **Variable cost:** labeled `$0.75` as an inference and added `$0–$5` sensitivity.
- **Wilson rule:** every count gate now also requires a one-sided 95% lower bound of at least
  3%; the initial 250-exposure precision example is explicit.

**Deferred**: none.

## Cycle 2 — 2026-08-03 16:08 EDT

**Found**: 0 blockers, 3 risks, 1 gap

**Addressed**:

- **Raw intent versus activation:** the 3% Wilson floor now applies only to the benchmarked
  raw verified-intent rate; activation yield is reported separately with no invented floor.
- **Conversion lag:** three months is labeled a midpoint, zero/three/six-month sensitivity
  is shown, and the investment gate uses the full six-month lag.
- **Safety margin:** the full-build gate now adds a 10% economic reserve and a one-sided 95%
  binomial conversion allowance, increasing the rounded gate to 11,100.
- **Intent aging:** staged counts expire after 180 days absent voluntary self-serve
  reconfirmation; early gates are explicitly capped value-of-information expenses rather
  than claims that their cohorts will pay.

**Deferred**: none.

## Cycle 3 — 2026-08-03 16:14 EDT

**Found**: 0 blockers, 0 risks, 1 gap

**Addressed**:

- **Value-of-information overclaim:** the first two thresholds are now explicitly heuristic
  risk-budget caps. Their spend-per-signal ratios are shown, but no claim is made that the
  future cohort economically covers them or that their information value has been estimated.

**Deferred**: none.
