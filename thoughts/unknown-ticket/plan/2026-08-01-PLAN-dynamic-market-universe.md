# Dynamic Market-Aware Universe: Implementation Plan

**Date**: 2026-08-01
**Ticket**: None
**Implementation repository**: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist`
**Implementation branch**: `codex/dynamic-market-universe-shadow`
**Status**: Authoritative implementation scope; shadow-only and committed locally
**Reconciled**: 2026-08-03 against the local documents, live Axe workspace, and commit `5c4c1e8`

## Overview

Implement the approved daily 900-name universe as a watchlist-owned, fixture-driven shadow pipeline. Deterministic code validates audited category inputs, selects exactly 900 unique ticker/CIK pairs, allocates three immutable 300-name cohorts, publishes content-addressed artifacts with first-writer semantics, and later exposes those cohorts to the existing coordinator only through an explicit delivery-disabled shadow mode.

## Document Authority and Terminology

- This plan defines implementation scope. The companion technical design defines architecture and invariants. Saved checkpoints record historical execution state; they do not add scope unless this plan or an explicit approved addendum incorporates it.
- GTM and monetization documents describe customer delivery and commercial sequencing. Their references to Claude or Codex mean MCP client hosts, not upstream universe-research runtimes.
- **Evidence-source adapter** means a Catalyst Edge or security-data collector. **Runtime adapter** means the upstream research or independent-audit execution surface. **MCP client** means the user-facing host that invokes Catalyst Edge.
- Provider and model names remain configuration inputs until an approved runtime record names them. The formal design does not select Codex, Claude, Sol, Terra, or Luna for the dynamic-universe pipeline.
- Checkpoint-only instructions to run provider-specific live research or audit do not override the live-retrieval exclusion below. They remain suspended unless separately approved and incorporated here.

## Validated State — 2026-08-03

- The remote implementation branch starts from `0ca48d5439af176f264dc678ef8cbe757782d008`; the Phase 0–2 shadow implementation, standalone runtime-adapter proof module, static-path integration test, and discovery-resume fix are committed locally as `5c4c1e8`. The repository has no Git remote, so that commit is not pushed or merged elsewhere.
- The enabled scheduled path remains the no-argument static 300-name scan. `scripts/run_scan.sh` does not pass dynamic or runtime-adapter arguments; `--dynamic-shadow` remains explicit, fixture-backed, dry-run, delivery-disabled, and isolated beneath `data/runs/`.
- Static membership, schedule, and delivery configuration are unchanged. A complete default `async_main` integration test now executes 300 fixed dossiers through live-state persistence with providers mocked. The 2026-08-03 11:30 ET scheduled run also exercised the modified default path and failed closed because IBOC's discovered SEC source timed out; an exact-run resume discarded and rescored the unreconciled discovery dossier, then failed closed again when SEC collection remained unavailable. No false success or delivery occurred, but a successful post-edit scheduled run is still absent.
- No accepted production universe, active dynamic pointer, `data/dynamic_state.json`, or dynamic scan schedule exists.
- `config/source-policy.json` records approved uses for bounded iShares holdings, the static market calendar, and SEC identity. `research_citations` and `audit_reopening` remain blocked.
- `config/runtime-adapters.json` keeps both production runtime roles blocked. `scripts/runtime_adapters.py` is a committed standalone proof CLI, imported only by its tests and unreachable from the scheduled scan path.
- The standalone proof shells out to Codex CLI for research and Claude Code CLI for audit; it does not call an Anthropic SDK or direct Claude API. Claude is restricted to `WebSearch` and `WebFetch` with session persistence disabled.
- The proof artifact schemas are not the compiler's `ResearchProposal` and `AcceptedAudit` schemas, and no converter or orchestrator connects them. Even a successful provider proof cannot currently feed `compile_universe`.
- Codex JSONL exposes token counts but the parser records no dollar cost. The adapter skips the dollar-ceiling comparison when provider cost is absent, so the required Codex cost ceiling is not currently verifiable.
- Persisted adapter attempts are ignored diagnostics, not accepted artifacts: generic `gpt-5.6` was rejected by Codex and `gpt-5.6-terra` reached execution but exceeded its configured token ceiling. Fresh bounded capability probes separately proved Codex Sol search/schema output and Claude Code WebSearch/WebFetch structured output, but they did not produce a complete `ResearchRuntimeArtifact`, `AuditRuntimeArtifact`, accepted compiler input, or production approval.
- Live OpenClaw inventory currently reports `openai/gpt-5.6-sol`, `openai/gpt-5.6-terra`, and `openai/gpt-5.6-luna` as configured and available; all three returned `OK` through the agent route without fallback. The static Watchlist cron currently uses Luna. Direct inference requires a different API-key transport and failed without that profile, so callability is surface-specific. These OpenClaw route IDs do not select a dynamic runtime.
- Claude Code `2.1.220` and Codex CLI `0.145.0` are installed on Axe. Claude is authenticated through `claude.ai` Max rather than an Anthropic API integration. Their capability probes do not satisfy the blocked provenance, independence, source-policy, end-to-end schema, or acceptance contracts.
- `data/calendars/us-equities.json` records an `exchange_calendars` 4.13.2 XNYS build. That package is available only through an on-demand `uv --with` environment; it is not declared or importable in the Catalyst service environment, and no calendar generation/refresh command is present in the watchlist workspace. The coordinator's dynamic-shadow path does not enable production-calendar loading; only tests call the loader with `allow_production=True`. Operational wiring and reproducible regeneration remain unimplemented.
- The production calendar JSON also omits the design-required retrieval time, update owner, and review cadence, plus the session dates and session open/close values named in its source-policy record. The loader instead derives eligibility as weekday-minus-retained-holidays. The current 4.13.2 XNYS calendar reports coverage through 2027-08-02 while the artifact claims generation through 2027-08-31, so its final coverage month is not reproducible from the declared dependency state.
- The isolated remote suite passes 64/64 and Ruff passes, including a 300-name default `async_main` integration test and the unreconciled-discovery resume regression.
- Implementation edits, tests, and the local shadow commit were approved and completed. Push and merge remain unavailable because the watchlist repository has no Git remote. Deployment, cron changes, dynamic scheduling, activation, and external delivery remain separately gated and unperformed.

## Desired End State

- Strict version-1 contracts reject unknown fields, malformed/stale provenance, unauthorized source uses, invalid identities, non-finite numbers, unordered collections, and incomplete recovery state.
- Fixture inputs deterministically produce exactly 900 unique core tickers/CIKs, 100–500 mapped reserves, three disjoint ordered 300-name cohorts, and stable content identity.
- Publication writes attempt diagnostics separately from canonical payload bytes, reuses only byte-identical payloads, and creates one accepted pointer without overwrite.
- Dynamic coordinator work is opt-in, shadow-only, delivery-disabled, and isolated from all live ledgers/state until activation is separately authorized.
- The static watchlist, no-argument scan path, cron, scoring/classification code, Catalyst Edge repository, and live state remain unchanged.

## What We're NOT Doing

- Approving any provider terms, inventing source authorization, selecting production research/audit adapters, or performing live retrieval.
- Enabling dynamic consumption, external delivery, or a pre-market job.
- Editing the live cron, static watchlist, provenance, legacy state, Catalyst Edge scoring, classification thresholds, or paper-only language.
- Claiming theme quality, alpha, profitability, backtest validity, or exact-once external delivery.
- Pushing, merging, deploying, scheduling, or activating without separate authorization and a configured target.

## Phase 0: Record the Blocked Operating Contracts

### Overview

Create machine-readable source-policy and runtime-adapter registries that state the current production blockers truthfully. Their blocked records must fail activation; fixture-only shadow tests inject separately approved fixture records and never convert those into production approval.

### Changes Required

#### 1. Source policy registry

**File**: `config/source-policy.json`

**New shape**:

```json
{
  "schema_version": 1,
  "revision": "source-policy-v1-blocked-2026-08-01",
  "uses": [
    {
      "approval_id": "broad-market-holdings-production",
      "use_case": "broad_market_holdings",
      "status": "blocked",
      "blocked_reasons": ["Automation, retention, hash, and derived-output rights are not approved."]
    },
    {"approval_id": "research-citations-production", "use_case": "research_citations", "status": "blocked", "blocked_reasons": ["Automated retrieval policy is not approved."]},
    {"approval_id": "audit-reopening-production", "use_case": "audit_reopening", "status": "blocked", "blocked_reasons": ["Independent reopening policy is not approved."]},
    {"approval_id": "sec-identity-production", "use_case": "sec_identity", "status": "blocked", "blocked_reasons": ["Automation and retention approval is not recorded."]},
    {"approval_id": "market-calendar-production", "use_case": "market_calendar", "status": "blocked", "blocked_reasons": ["Calendar source and refresh policy are not approved."]}
  ]
}
```

**Why**: Makes the activation denial explicit and machine-verifiable without fabricating provider approval.

#### 2. Runtime adapter registry

**File**: `config/runtime-adapters.json`

**New shape**:

```json
{
  "schema_version": 1,
  "revision": "runtime-adapters-v1-blocked-2026-08-01",
  "adapters": [
    {
      "adapter_id": "research-production",
      "role": "research",
      "status": "blocked",
      "blocked_reasons": ["Callable structured-output runtime is not selected."]
    },
    {
      "adapter_id": "audit-production",
      "role": "audit",
      "status": "blocked",
      "blocked_reasons": ["Independent audit runtime is not selected."]
    }
  ]
}
```

**Why**: Prevents shadow mechanics from being mistaken for a production research/audit integration.

### Verification

#### Automated

- [x] Strict registries parse: `PYTHONPATH=/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts /opt/homebrew/bin/uv run --directory /Users/axe/services/catalyst-edge-mcp --frozen python -m unittest test_dynamic_universe.PhaseZeroContractTests -v`
- [x] Blocked production configuration fails activation: `PYTHONPATH=/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts /opt/homebrew/bin/uv run --directory /Users/axe/services/catalyst-edge-mcp --frozen python -m unittest test_dynamic_universe.PhaseZeroContractTests.test_production_activation_fails_closed -v`

#### Manual

- [x] Confirm every production use/adapter remains `blocked` and contains no invented endpoint, terms revision, credential reference, owner approval, or expiry.

Post-Phase 2 source-policy records dated 2026-08-01 approve the bounded BlackRock/iShares holdings use, the generated calendar use, and SEC identity use. This is policy metadata, not proof that `exchange_calendars` is installed or that a refresh path exists. Research-citation and audit-reopening source uses plus both runtime adapters remain blocked until the complete callable-surface and approval contracts pass.

## Phase 1: Compiler and Immutable Artifact Contracts

### Overview

Add strict Pydantic v2 contracts, deterministic selection/allocation, canonical hashing, and crash-safe first-writer publication. All tests use generated or checked-in fixtures under temporary workspaces; no production network, state, or delivery path is reachable.

### Changes Required

#### 1. Strict contract models

**File**: `scripts/universe_contracts.py`

**New code pattern**:

```python
class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, allow_inf_nan=False
    )


class UniversePayload(ContractModel):
    schema_version: Literal[1]
    session_date: date
    valid_from: AwareDatetime
    expires_at: AwareDatetime
    research: ResearchIdentity
    audit: AuditIdentity
    source_policy_revision: BoundedText
    source_snapshots: tuple[SourceSnapshot, ...]
    source_health: tuple[SourceHealth, ...]
    focus_categories: tuple[AcceptedCategory, ...]
    candidates: Annotated[tuple[UniverseCandidate, ...], Len(1000, 1400)]
    reserves: Annotated[tuple[str, ...], Len(100, 500)]
    cohorts: Cohorts
```

Define strict versioned models for research proposal, accepted audit, source policy/manifest, security snapshot, SEC identity, universe candidate/payload/envelope/pointer, dynamic state, commit state, scan contract, and discovery identity. Enforce the deployed downstream ticker ceiling, ten-digit CIKs, UTC-aware cutoffs, SHA-256 fields, bounded strings/collections, referential integrity, declared array ordering, and non-finite-number rejection.

**Why**: Implements `DU_INPUT_RESEARCH_SCHEMA`, `DU_AUDIT_PROVENANCE`, `DU_SECURITY_SNAPSHOT_SCHEMA`, and the future integration contracts without weakening Catalyst Edge.

#### 2. Deterministic compiler

**File**: `scripts/universe_compiler.py`

**New public functions**:

```python
def require_phase0_approved(policies, runtimes, required_uses, at): ...
def assign_category_owners(audit, candidates): ...
def allocate_quotas(categories, total=900): ...
def select_core_and_reserves(audit, candidates): ...
def allocate_cohorts(core): ...
def compile_universe(research, audit, sources, securities, sec_identities): ...
def canonical_json_bytes(payload): ...
def payload_identity(payload): ...
def publish_universe(root, payload, attempt, fault=None): ...
def supersede_universe(root, replacement, authorization, state): ...
```

Implementation order:

1. Validate every referenced fixture source approval and research/audit runtime contract.
2. Join provider-neutral security rows to authoritative SEC identity; reject unsupported exchange/type/location, malformed symbols, duplicate ticker, and duplicate CIK.
3. Assign one primary category by `(direct nomination, focus before honorable mention, category rank, category_id)`.
4. Allocate focus quotas by largest remainder with declared minimum/maximum bounds.
5. Fill shortages through audited adjacency then ordered honorable mentions; never use unmatched broad-market fallback.
6. Select exactly 900 core and the declared 100–500 mapped reserves.
7. Allocate ordered core records across `open`, `midday`, and `afternoon` by per-category rotation, asserting 300/300/300 and zero overlap.
8. Canonicalize logical payload bytes with sorted object keys, declared array order, compact UTF-8 JSON, and one trailing newline; derive `cu_<sha256>`.
9. Under a per-session `fcntl.flock`, write attempt diagnostics and payload through temporary siblings, `fsync` files/directories, reuse only identical payload bytes, and create `accepted-universe.json` with a non-overwriting hard-link CAS.

Expose a fixture-only CLI (`build --workspace ... --input ... --shadow`) that refuses non-shadow operation. It exists for subprocess interruption/recovery tests and writes only beneath the supplied workspace.

**Why**: Implements the deterministic and immutable boundaries behind `INV-CORE`, `INV-COHORT`, `INV-PROVENANCE`, `INV-IMMUTABLE`, and `INV-NO-FALLBACK`.

#### 3. Golden fixture

**File**: `data/fixtures/dynamic-universe-v1.json`

Store the fixture provenance/revisions and the complete ordered expected result: universe hash, 300 `open`, 300 `midday`, 300 `afternoon`, 100+ reserves, and the forced honorable-mention shortage records. Input records may be generated deterministically in the test helper, but expected ordered output is static.

**Why**: Array order participates in identity; a full golden result makes the allocation prose executable.

#### 4. Contract, compiler, publication, and fault tests

**File**: `scripts/test_dynamic_universe.py`

Add tests named for the stable IDs:

```python
class DynamicUniverseContractTests(unittest.TestCase):
    def test_DU_INPUT_RESEARCH_SCHEMA(self): ...
    def test_DU_SOURCE_POLICY_APPROVAL(self): ...
    def test_DU_SOURCE_HEALTH_ISOLATION(self): ...
    def test_DU_AUDIT_PROVENANCE(self): ...
    def test_DU_SECURITY_SNAPSHOT_SCHEMA(self): ...
    def test_DU_SEC_IDENTITY_GATE(self): ...
    def test_DU_UNIQUE_TICKER_AND_CIK(self): ...
    def test_DU_EXACT_CORE_900(self): ...
    def test_DU_RESERVE_BOUNDS(self): ...
    def test_DU_EXACT_COHORT_300(self): ...
    def test_DU_ZERO_COHORT_OVERLAP(self): ...
    def test_DU_HONORABLE_BACKFILL(self): ...
    def test_DU_DETERMINISTIC_ALLOCATION(self): ...
    def test_DU_ATOMIC_PUBLICATION(self): ...
    def test_DU_IDENTICAL_PAYLOAD_REUSE(self): ...
    def test_DU_SUPERSESSION_RACE(self): ...
    def test_DU_STALE_FALLBACK_FORBIDDEN(self): ...
    def test_DU_COHORT_SCAN_BINDING_contract(self): ...
    def test_DU_RESUME_TTL_contract(self): ...
    def test_DU_SCAN_CONTRACT_MISMATCH_contract(self): ...
    def test_DU_DISCOVERY_ATOMIC_CLAIM_contract(self): ...
```

Use `TemporaryDirectory` for every publication test. Inject typed failures before payload promotion and pointer acceptance. For process-kill coverage, start one child against a verified temporary workspace, wait for a durable phase marker, `SIGKILL` only the captured PID, and `wait` it; never use `pkill` or name matching.

**Why**: Verifies the accepted invariants under malformed inputs, retries, conflicts, concurrency, and interrupted writes.

#### 5. Runtime artifact ignores

**File**: `.gitignore`

**Add**:

```gitignore
data/dynamic_state.json
data/universes/
data/dynamic-locks/
```

**Why**: Keeps accepted/shadow runtime state out of version control while retaining explicit fixtures and configuration.

### Verification

#### Automated

- [x] Dynamic contract/compiler suite: `PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/uv run --directory /Users/axe/services/catalyst-edge-mcp --frozen python -m unittest discover -s /Users/axe/.openclaw/workspace-catalyst-watchlist/scripts -p 'test_*.py' -v`
- [x] Watchlist lint: `/opt/homebrew/bin/uv run --directory /Users/axe/services/catalyst-edge-mcp --frozen ruff check /Users/axe/.openclaw/workspace-catalyst-watchlist/scripts`
- [x] Catalyst regression: `cd /Users/axe/services/catalyst-edge-mcp && PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/uv run --frozen pytest -p no:cacheprovider`
- [x] Catalyst lint: `cd /Users/axe/services/catalyst-edge-mcp && /opt/homebrew/bin/uv run --frozen ruff check catalyst_edge_mcp tests`
- [x] Whitespace: `git diff --check`

#### Manual

- [x] Inspect the golden artifact and a stratified sample of direct, classification-only, honorable-mention, reserve, and rejected records.
- [x] Confirm no test or helper imports Catalyst Edge, reads production `.env`, performs network access, or writes outside a temporary workspace.

## Phase 2: Coordinator Integration Behind Shadow Mode

### Overview

Integrate accepted cohort consumption, stable scan contracts, migration, discovery claims, and commit recovery without changing the default scheduled path. Dynamic mode must require explicit arguments and force dry-run/external-delivery denial.

### Changes Required

#### 1. Dynamic scan state machine

**File**: `scripts/dynamic_scan.py`

**New public functions**:

```python
def resolve_slot(calendar, session_date, slot): ...
def load_accepted_cohort(workspace, session_date, slot): ...
def build_scan_contract(...): ...
def bind_or_resume_scan(...): ...
def load_or_migrate_dynamic_state(...): ...
def claim_discovery_identities(...): ...
def transition_commit(...): ...
def reconcile_commit(...): ...
```

Use first-writer cohort binding, complete behavior-versioned scan-contract hashing, resume TTL, immutable discovery windows, ticker+CIK claims, stable commit IDs, and version-1 `dynamic_state.json`. Legacy version-2 and unversioned state stay byte-identical read-only inputs; historical version-1 input gets an explicit read-only compatibility test rather than silent rejection.

The hashed scan contract freezes the universe/cohort IDs and checksum, scheduled cutoff and discovery window, first-attempt time, coordinator and Catalyst service commits, dependency-lock hash, registry/classification/lookback revisions, source-policy/calendar/dynamic-state revisions, and secret-free provider/config fingerprints. Commit transitions reconcile only isolated shadow copies of ledgers, indexes, queues, and state, terminate at `report_ready`, never invoke current `persist_live()`, and never write a delivery receipt.

#### 2. Opt-in coordinator seam

**File**: `scripts/scan_coordinator.py`

Add `--dynamic-shadow`, `--session-date`, and `--slot`. `--dynamic-shadow` must imply `--dry-run`; validate the pointer, payload, cohort, schedule, binding, scan contract, and TTL before discovery, Catalyst import, or provider calls. Dynamic runs use `data/runs/<scan_id>/`, immutable slot discovery windows, and isolated dynamic state projections. The no-argument path must remain byte-for-byte behaviorally equivalent.

Update `_sec_ticker_by_cik`, `_parse_sec_current_feed`, `_discover_issuer_events`, `_bounded_discovery`, and `_validate_discovery_dossier` so every supplemental candidate, dossier reconciliation, decision, exclusion, and claim carries canonical CIK plus SEC snapshot identity. Ticker-only discovery identity is invalid in dynamic mode.

#### 3. Stable dynamic record identity

**File**: `scripts/record_decision.py`

Add an optional `scan_id` input. When present, derive `record_id` from `scan_id|ticker`; when absent, preserve the legacy `run_at|ticker` identity exactly.

#### 4. Calendar fixture

**File**: `data/fixtures/calendars/us-equities-v1.json`

Add a checked-in, explicitly non-production calendar fixture with revision, checksum, generated-through date, holidays, early closes, and at least 12 future months of synthetic test coverage. This was the Phase 2 boundary. A later approved-use record and generated production JSON now exist, but no package declaration or reproducible refresh path was added; the production artifact therefore remains an externally generated static input rather than a maintained dependency workflow.

#### 5. Lifecycle and recovery tests

**File**: `scripts/test_dynamic_scan.py`

Cover `DU_COHORT_SCAN_BINDING`, `DU_RESUME_TTL`, `DU_SCAN_CONTRACT_MISMATCH`, `DU_STALE_FALLBACK_FORBIDDEN`, `DU_SUPERSESSION_RACE`, `DU_DISCOVERY_DAILY_EXCLUSION`, `DU_DISCOVERY_ATOMIC_CLAIM`, and `DU_SELECTION_CLASSIFICATION_SEPARATION`, plus explicit `DU_SLOT_RESOLUTION`, `DU_LEGACY_STATE_MIGRATION`, and `DU_COMMIT_RECOVERY` cases. Test out-of-order recovery, persisted-claim retention, old-run rejection, every commit interruption, completed retry with zero appends, byte-identical report recovery, and forced `delivery_allowed=false`.

### Verification

#### Automated

- [x] Run all Phase 1 verification commands.
- [x] Compare pre/post SHA-256 for `scripts/run_scan.sh`, `data/watchlist.json`, `data/watchlist-provenance.md`, and `data/state.json`; every hash must be unchanged.
- [x] Read cron `b371d3d3-f194-4ccf-9464-b20034b48fe0`; schedule, payload, timeout, enabled state, and delivery must be unchanged.
- [x] Run an isolated explicit dynamic-shadow fixture scan and verify `delivery_allowed=false`, stable `scan_id`, exact 300 cohort decisions, no writes to live ledgers/state, and retry of only missing dossiers.

#### Manual

- [x] Review all source-family degradation, category mapping, selected/rejected sample, state transition, and recovery evidence from the isolated fixture run.
- [x] Confirm dynamic activation, pre-market scheduling, external delivery, push, merge, and deployment remain disabled/unperformed; the authorized shadow implementation is preserved in local commit `5c4c1e8`.

## Testing Strategy

### New Tests

- `scripts/test_dynamic_universe.py`: Phase 0 registries, strict contracts, compilation/allocation, canonical identity, atomic publication, conflicts, and fault recovery.
- `scripts/test_dynamic_scan.py`: slot/scan identity, migration, discovery claims, commit recovery, resume TTL, and shadow-only integration.

### Existing Tests

- Preserve `scripts/test_scan_coordinator.py` as the classification/discovery regression suite; add only separation assertions needed to prove universe metadata cannot change classification.
- Preserve the full Catalyst Edge offline suite as the downstream scorer regression gate.

## References

- Design: [thoughts/unknown-ticket/design/2026-08-01-CATALYST-WATCHLIST-TDD-dynamic-market-universe.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/thoughts/unknown-ticket/design/2026-08-01-CATALYST-WATCHLIST-TDD-dynamic-market-universe.md)
- Design critique: [thoughts/unknown-ticket/critique/2026-08-01-unknown-ticket-CRITIQUE-dynamic-market-universe.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/thoughts/unknown-ticket/critique/2026-08-01-unknown-ticket-CRITIQUE-dynamic-market-universe.md)
- Live coordinator: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts/scan_coordinator.py`
- Live decision writer: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts/record_decision.py`
