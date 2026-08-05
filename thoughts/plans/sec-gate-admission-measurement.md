# sec-gate-admission — measure gate admission wait vs network I/O

**Ticket:** `thoughts/catalyst-scan-discovery-timeout-20260804/BUG_REPORT.md` (zenith), §7A step 1 / §8.1
**Branch:** `measure/sec-gate-admission` (worktree `~/Desktop/dev/catalyst-edge-mcp-gate-measure`, based on `3f34420` = deployed SHA on axe mini)
**Classification:** chore (instrumentation) | backend | small | clear
**Specialists engaged:** none — single-file timing change plus a harness script

## Why this exists

The bug report's remediation A says to retune the shared SEC rate, coordinator
concurrency, and adapter deadline. §8.1 makes instrumentation a hard gate on
that: *"If gate admission is not consuming most of the timed-out adapter
budget, the contention diagnosis is incomplete."* The candidate values
(2→8 rps, 8→15 s) are explicitly **not validated**. This ticket produces the
measurement that either justifies or refutes them. It changes no operating
value.

## Acceptance criteria

- For any gated request, admission wait (semaphore + rate spacing) and body
  time (network I/O + parse) are recorded as separate numbers.
- A request cancelled by the service's 8 s `asyncio.wait_for` still records its
  admission wait. This is the whole point — the timed-out requests are the
  population under study, and they are exactly the ones that get cancelled.
- Per-gate aggregates, so `sec` (shared by filings + ownership) is
  distinguishable from `sec_funds`.
- A harness reproduces production topology (concurrency=4, real adapters, real
  SEC) and reports the admission/body split, staying under SEC's 10 rps
  aggregate fair-access guideline.

## Findings that shape the design

- `SEC_GATE` (`sec_filings.py:76`, concurrency=2, rps=2) is shared across
  4 call sites in `sec_filings.py` and 2 in `sec_ownership.py:568,577`.
- **`SEC_FUND_GATE` (`sec_funds.py:35`) is a second, independent gate that also
  targets SEC** (2 more call sites). The two gates do not coordinate, so this
  process alone can offer ~4 rps at SEC. Any aggregate-rps decision in step 2
  must count both. The bug report does not mention this gate.
- `service.py:393` wraps the **entire** `adapter.collect()` in one 8 s
  `asyncio.wait_for`, so admission waits from every gated request inside one
  adapter accumulate against a single budget.

## Skills in play / explicitly skipped

- `superpowers:test-driven-development` — USED. Timing logic with a
  cancellation path; red test first.
- `superpowers:systematic-debugging` — SKIPPED. Root cause is already
  diagnosed and independently validated; this is measurement, not diagnosis.
- `superpowers:brainstorming` — SKIPPED. Not a feature; the report specifies
  the required output precisely.

## Phase 1 — instrument `ProviderGate`

**Files:** `catalyst_edge_mcp/adapters/base.py`
**Change:** record admission wait and body duration per gate as O(1) running
aggregates. Record in a `finally` so cancelled bodies still report admission
wait. Add an optional `name` to `ProviderGate`; name the existing gates.
**Tests:** `tests/test_provider_gate_timing.py`
**Verification:** `uv run pytest tests/test_provider_gate_timing.py`

Instrumenting inside `ProviderGate` means zero changes to `sec_filings.py`,
`sec_ownership.py`, or any adapter — every gate is covered for free.

## Phase 2 — measurement harness

**Files:** `scripts/measure_sec_gate.py`
**Change:** drive the real SEC adapters at production concurrency over a
ticker sample against live SEC, then print the per-gate admission/body split
and the share of adapter budget spent waiting for admission.
**Verification:** run locally, then on axe mini against real SEC.

## Phase 3 — collect on mini

Deploy the branch to a scratch checkout on mini (NOT over the live service
tree), run the harness, record numbers back into the bug report as the §7A
input.

## Test cases

| TC | Description | Status |
|---|---|---|
| TC1 | Admission wait accumulates under rate limiting; body time stays separate | ✅ `pytest tests/test_provider_gate_timing.py` |
| TC2 | Body time recorded for slow bodies with no contention | ✅ same run |
| TC3 | Cancelled (timed-out) request still records admission wait | ✅ same run — caught a real defect in the first implementation |
| TC4 | Harness reports split against real SEC at concurrency=4 | ✅ on axe mini, production `.env`, 12 real watchlist tickers |
| TC5 | Full suite shows no regression from the gate change | ✅ 447 passed, exit 0 |

## Result

Admission wait is **91.9%** of shared-gate time under production settings
(mean 2.45 s admission vs 0.217 s body). Dropping concurrency 4→1, changing
nothing else, took `filings_news` from 3 timeouts to 0 and never-admitted from
7/50 to 0/59. §8.1 is answered in the affirmative; the contention diagnosis
holds.

Full write-up, including two findings absent from the bug report
(`SEC_FUND_GATE` as a second SEC gate; `no_observations` being independent of
contention): zenith `thoughts/catalyst-scan-discovery-timeout-20260804/MEASUREMENT.md`.
