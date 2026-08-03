# Catalyst Watchlist Dynamic Market-Aware Universe: Technical Design

**Date**: 2026-08-01
**Authors**: Ryan Monroe, Codex
**Ticket**: None
**Status**: Authoritative architecture; provider-neutral, shadow-only, and committed locally
**Reconciled**: 2026-08-03 against the implementation plan, live Axe workspace, and commit `5c4c1e8`

## TL;DR

The watchlist currently scans the same 300 companies three times per weekday, so it performs 900 evaluations but covers only 300 unique symbols. We will add a separate pre-market research and universe-compilation pipeline that identifies the day's most important market themes, expands those themes into a validated pool of U.S. equities, and freezes three non-overlapping 300-symbol cohorts. The existing Catalyst Edge service remains the downstream per-ticker evidence engine; universe priority never changes its scoring or `RESEARCH NOW` gates.

## Problem Statement

The live Catalyst Watchlist has a deterministic, resumable, fail-closed scanner, but its universe is static. `data/watchlist.json` is a committed 300-symbol cohort built from the original 30 names plus SPY holdings by descending weight. Every scheduled run reloads that same file, so the 8:30, 11:30, and 14:30 America/New_York scans repeat the same 300 symbols.

The desired product is different:

1. Analyze current market structure, macroeconomic data, earnings, regulatory developments, geopolitical events, commodities, rates, volatility, and sector participation.
2. Turn that analysis into ranked focus categories and explicit honorable mentions.
3. Enumerate and validate the equities associated with those categories.
4. Produce three different 300-symbol cohorts, yielding exactly 900 unique core equities per weekday.
5. Preserve the current evidence, provenance, idempotency, classification, paper-only, and fail-closed boundaries.

The missing capability is therefore not a larger static list. It is a market-aware universe compiler with a strict separation between agent judgment and deterministic publication.

## Desired End State

Before the first weekday scan, the system publishes one immutable, provenance-backed daily universe containing exactly 900 unique core U.S. equities plus reserves. The core universe is partitioned into `open`, `midday`, and `afternoon` cohorts of exactly 300 symbols with zero overlap. Each selected symbol has a valid SEC identity, one focus-category rationale, a deterministic selection rank, and traceable source lineage.

Each scheduled scan consumes only its frozen cohort. Up to 10 event-discovery names may remain supplemental per scan, but they must be outside the entire 900-name core universe and outside all earlier same-day discoveries. Thus the guaranteed daily core coverage is 900 unique symbols; total unique daily coverage may be 900–930 when supplemental discovery produces candidates.

### Terminology

| Term | Meaning |
| --- | --- |
| Focus category | Audited market area receiving primary core quota |
| Honorable mention | Audited next-best category eligible to fill a declared category shortage |
| Reserve | Accepted, mapped security beyond the frozen core; never an intraday replacement |
| Supplemental discovery | New SEC/issuer-primary event candidate found during a scan, outside core and reserves |
| Evidence-source adapter | Collector for Catalyst evidence or approved security/source snapshots |
| Runtime adapter | Upstream execution surface for market research or independent audit |
| MCP client | User-facing host such as Claude Desktop or Codex that invokes Catalyst Edge; not an upstream universe runtime |

### Normative Invariants

| ID | Requirement |
| --- | --- |
| `INV-CORE` | Exactly 900 core tickers and 900 CIKs per eligible session |
| `INV-COHORT` | Exactly three frozen 300-name cohorts with zero pairwise overlap |
| `INV-PROVENANCE` | Every accepted name has validated identity, category rationale, and source lineage |
| `INV-IMMUTABLE` | Content artifacts and any started cohort are immutable |
| `INV-FAIL-CLOSED` | Invalid, stale, incomplete, or unauthorized inputs stop before Catalyst calls |
| `INV-SEPARATION` | Universe priority never changes Catalyst evidence scores or classification gates |
| `INV-NO-FALLBACK` | Static scanning is operator-declared rollback, never automatic substitution |

## Fixed Design Decisions

- Universe generation belongs in the Axe Catalyst Watchlist workspace, before dossier scoring.
- Catalyst Edge remains ticker-in/evidence-out; its MCP schemas, collectors, deterministic scorer, and classification semantics do not expand to own universe selection.
- Market research runs once before the first scan, not inline during all three scans.
- Research and audit roles are provider-neutral. A provider-specific proof does not become a production selection unless an approved runtime record and implementation-plan amendment name it.
- The research stage may propose categories, mappings, direct candidates, and priorities. It cannot publish an accepted ticker list.
- Deterministic code owns identity resolution, eligibility, deduplication, ranking tie-breaks, quota reconciliation, honorable-mention backfill, cohort allocation, hashing, and atomic publication.
- `INV-CORE`, `INV-COHORT`, and `INV-IMMUTABLE` govern core membership; v1 has no share-class exception.
- `INV-FAIL-CLOSED` and `INV-NO-FALLBACK` govern operational failure and rollback.
- Universe selection is prioritization evidence, not catalyst evidence, directional proof, alpha, or a trading recommendation.
- No brokerage, execution, order, portfolio-sizing, or autonomous trading capability is introduced.

## Proposed Approach

### Chosen Approach: Audited Research, Deterministic Compilation, Frozen Cohorts

Use a separate daily pipeline with three integrity zones:

1. **Market research** — an agent produces a structured, cited assessment of the current market and ranked focus categories.
2. **Independent audit** — a separate context reopens material sources, rejects unsupported categories, and emits the canonical category artifact.
3. **Deterministic compilation** — code joins accepted category mappings to an approved security-universe snapshot, validates identities against the SEC, ranks candidates, fills shortages from honorable mentions, allocates three cohorts, and atomically publishes the immutable daily manifest.

This reuses the proven reasoning and provenance shape of `daily-options-research` without reusing its trade-candidate limits or options score. It also preserves the current watchlist coordinator as the scanner rather than turning Catalyst Edge into a market-wide orchestration service.

### Architecture

```text
Primary market-research agent
  market structure + macro + events + geopolitics + sectors
                         |
                         v
              proposed market_focus.json
                         |
                         v
Independent source/category audit
                         |
                         v
               accepted market_focus.json
                         |
             +-----------+------------+
             |                        |
             v                        v
Approved security-universe       SEC ticker/CIK/
snapshot + classifications       exchange snapshot
             |                        |
             +-----------+------------+
                         v
            Deterministic universe compiler
       eligibility -> dedupe -> quotas -> backfill
                         |
                         v
            Immutable daily universe manifest
              900 core + reserves + checksums
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
      open: 300      midday: 300    afternoon: 300
          |              |              |
          +--------------+--------------+
                         v
             Existing scan coordinator
                         |
                         v
              Existing Catalyst Edge service
```

**Load-bearing invariant:** the research model never writes `active_universe.json`, never decides whether a ticker is a valid security, and never changes a published cohort. Only validated deterministic output can cross into the scanner.

These are application integrity boundaries, not OS security boundaries: the current jobs share the `axe` account. Research and audit processes write only to an inbox; the compiler is the sole accepted-artifact writer; accepted directories become read-only; and the scanner revalidates the manifest checksum before every run. OS-level service-account separation is a later hardening option, not a claim of this design.

## How It Works

### End-to-End Flow

1. Research produces cited focus categories, honorable mentions, mappings, and typed source health.
2. An independent audit accepts or rejects those claims and freezes the category contract.
3. Approved market and SEC snapshots enumerate and validate mapped U.S. equities.
4. Deterministic compilation selects 900 core names, 100–500 reserves, and three disjoint cohorts.
5. Atomic publication binds one accepted universe to the session before any scoring starts.
6. Each scheduled scan consumes one frozen cohort; supplemental discoveries use session-wide identity claims.

### 1. Daily market research

The primary agent executes a provider-neutral adaptation of the existing market-regime standard. It evaluates only facts material to universe selection:

- SPY, QQQ, IWM, and DIA trend and market structure;
- volatility and breadth;
- one-day, five-day, and one-month sector participation;
- 2-year and 10-year yields, curve shape, DXY, and material commodities;
- the latest Federal Reserve decision and upcoming macro releases;
- material fiscal, tariff, geopolitical, legal, and regulatory developments;
- recent and upcoming market-moving earnings;
- cross-asset or vertical-specific developments that could alter equity attention.

The agent ends with a regime label and two ordered sets:

- **focus categories** — areas that deserve core quota;
- **honorable mentions** — the next-best categories or adjacent markets available for deterministic backfill.

The research output is a proposal, not an accepted universe. It contains no final cohort assignment.

### 2. Research source-health model

Source health is represented independently from category confidence. One provider failure cannot be converted into a fact about the market or copied into every category score.

Research tracks these source families separately:

1. market/index/breadth;
2. volatility;
3. rates and macroeconomic releases;
4. sector and cross-asset participation;
5. earnings and corporate-event calendar;
6. fiscal, geopolitical, legal, and regulatory developments.

Every family records `fresh`, `delayed`, `stale`, `unavailable`, `permission_required`, or `schema_error`. Each focus category must cite at least one authoritative or primary source and one independently retrieved supporting source. A source family may be degraded without globally zeroing unrelated categories, but a category whose own required evidence is unavailable cannot be accepted.

Independence is based on originating publisher or dataset lineage, not URL count; two syndicated pages are one source. A single authoritative source may stand alone only through an explicit audited waiver. Source-family policy defines maximum observation age, maximum retrieval age, delayed-source tolerance, and cutoff timezone. The manifest records the applied policy revision, so `stale` is executable rather than subjective.

All retrieval treats model-supplied URLs and content as untrusted. Adapters allow HTTPS only, reject private/link-local destinations, revalidate redirects, enforce approved hosts where available, bound transfer and decompressed sizes, validate MIME/schema/row limits, hash content, and never execute instructions contained in retrieved text.

This directly prevents the failure observed in the July 28 options-research audit, where one provider-specific retrieval failure was generalized into universal instrument unavailability and contaminated all candidate scores.

### 3. Independent category audit

The audit runs in a separate context and must:

- verify the primary artifact checksum;
- reopen every material source used by accepted categories;
- distinguish unavailable data from negative evidence;
- remove unsupported claims and stale categories;
- verify that category inclusion/exclusion mappings follow from the cited thesis;
- confirm that the focus and honorable-mention ordering is internally consistent;
- preserve disagreements and typed degradation rather than silently rewriting history.

The production audit uses a different provider/model family from the researcher or a deterministic verifier that independently retrieves and checks every material claim. A new context using the same model is not sufficient independence by itself. The accepted artifact records both sides' provider, model, prompt revision, sources, and disagreements. A non-canonical or incomplete audit may be saved for diagnosis, but cannot publish a live universe.

### 4. Security-universe snapshot

The compiler consumes a provider-neutral snapshot rather than scraping arbitrary ticker lists. Each record supports:

- normalized ticker;
- issuer name;
- SEC CIK;
- exchange;
- security type or provider asset class;
- country/location;
- sector and optional industry/SIC classifications;
- source-specific weight or coverage rank;
- source observation date, retrieval time, URL, and content hash.

The initial design uses two independent roles:

- **candidate coverage and classification:** an approved broad-market holdings/security source. The validated prototype used BlackRock's official iShares Russell 3000 data download, which exposed 2,586 securities with sector, asset class, exchange, location, and fund weight as of 2026-07-30.
- **authoritative identity eligibility:** the SEC `company_tickers_exchange.json` snapshot. Only records resolving to one CIK on Nasdaq or NYSE survive.

The broad-market source is a replaceable adapter. Its automation, retention, and derived-output rights must be recorded in the watchlist-owned `config/source-policy.json` before live activation. A reachable public endpoint is not, by itself, permission.

Provider values normalize into versioned canonical enums before compilation. The adapter contract explicitly maps asset class, U.S. location, sector, exchange, weight, ADR, REIT, limited-partnership, foreign-domicile, missing-sector, and class-symbol behavior. SEC identity wins on exchange and CIK conflicts; all unresolved conflicts are typed rejections.

### 5. Category-to-security expansion

Each accepted category has an ordered mapping contract:

- included sectors;
- optional included industry/SIC tags when an approved source supplies them;
- excluded sectors/tags;
- explicit direct tickers supported by category evidence;
- quota weight;
- urgency rank;
- expiry/review time;
- ordered honorable-mention fallback categories.

The audited artifact also contains an ordered category-adjacency graph. Before quotas are calculated, every eligible security receives one deterministic primary category using the tuple `(direct nomination, focus before honorable mention, category rank, category_id)`; secondary memberships remain explanatory only and never consume a second slot.

The compiler enumerates every eligible record matching the accepted mappings before applying quotas. Direct ticker nominations receive a disclosed direct-relevance tier, but still pass the same identity, security-type, exchange, location, duplicate-CIK, and provenance validation as all other records.

### 6. Eligibility policy

A core or reserve candidate must satisfy all of the following:

- uppercase ticker matching the existing bounded ticker grammar after canonical class-symbol normalization;
- `Asset Class = Equity` or the equivalent approved security-type value;
- U.S. location under the selected broad-market universe contract;
- SEC CIK resolution;
- SEC exchange of Nasdaq or NYSE;
- one accepted focus or honorable-mention category;
- non-empty rationale and evidence reference;
- no duplicate ticker;
- no duplicate CIK;
- source snapshots within their configured freshness windows.

ETFs, funds, cash, options, futures, warrants, units, OTC securities, unsupported exchanges, malformed identifiers, and unresolved names are rejected with typed reasons. Rejected records remain countable in the build audit but never enter the accepted manifest.

### 7. Deterministic ranking

The agent ranks categories, not 2,500 individual securities. Within a category, deterministic ranking is:

1. direct evidence-backed nomination before classification-only membership;
2. primary selection tier before honorable mention;
3. category urgency and rank;
4. approved source coverage weight descending;
5. normalized ticker ascending as the final tie-break.

The ranking intentionally does not reuse Catalyst Edge's 0–100 evidence score or the daily-options 0–100 trade score. Those scores answer different questions after a ticker has already been selected.

The compiler stores each component and the final rank so the result is reproducible without asking the model to explain itself again.

### 8. Quota reconciliation and honorable mentions

Accepted category weights are normalized to 900 slots using a deterministic largest-remainder allocation. Configured minimum and maximum category shares prevent one broad category from consuming the entire day.

For each category:

1. fill its quota from validated primary members;
2. if the category is undersized, use unused validated names from its audited, ordered adjacency list;
3. then use the ordered honorable-mention categories;
4. fail if the accepted mapped pool is still undersized.

Every backfilled record was already mapped to an accepted focus or honorable-mention category. It is labeled `honorable_mention`, retains the shortage it filled, and preserves its own category rationale. Unmatched broad-market securities may appear in build diagnostics but are never a fallback. After every fill, the compiler rechecks ticker uniqueness, CIK uniqueness, exact count, and provenance.

If fewer than 900 valid names remain after the complete fallback ladder, publication fails. The compiler never lowers eligibility rules to satisfy the count.

### 9. Cohort allocation

After selecting the 900-name core, the allocator distributes each category across all three scans so the first scan does not receive every highest-ranked symbol while the afternoon receives only the tail.

The algorithm is deterministic:

- assign primary-category ownership before allocation;
- process accepted records by selection tier, primary-category rank, within-category rank, and ticker;
- maintain a per-category rotation cursor initially derived from stable category order;
- assign each record to the least-filled cohort; among tied cohorts, choose the first encountered from that category's rotation cursor, then advance the cursor;
- stop only when all three cohorts contain exactly 300 names;
- assert zero pairwise intersection and a 900-name union.

Golden fixture tests freeze the full ordered output, including multi-category, direct-nomination, and honorable-mention cases; prose is not the only executable definition.

The cohort names are semantic schedule slots, not mutable queue positions:

- `open` — 08:30 America/New_York;
- `midday` — 11:30 America/New_York;
- `afternoon` — 14:30 America/New_York.

`open` is a stable legacy slot label; its 08:30 execution is pre-market, not the 09:30 regular-session open.

A scheduled run resolves its slot from the configured schedule and session date. Manual recovery uses the immutable cohort or scan ID explicitly; it does not select the next uncompleted cohort by accident.

### 10. Immutable artifact contract

The accepted daily universe is a content-addressed envelope around a separately hashable payload:

```json
{
  "schema_version": 1,
  "universe_id": "cu_<sha256>",
  "payload_sha256": "<sha256>",
  "accepted_at": "2026-08-03T11:10:00Z",
  "payload": {
    "session_date": "2026-08-03",
    "valid_from": "2026-08-03T11:10:00Z",
    "expires_at": "2026-08-04T10:00:00Z",
    "research": {
      "surface": "...",
      "model": "...",
      "prompt_revision": "...",
      "cutoff": "...",
      "artifact_sha256": "..."
    },
    "audit": {
      "surface": "...",
      "model": "...",
      "cutoff": "...",
      "artifact_sha256": "..."
    },
    "source_policy_revision": "...",
    "source_snapshots": [],
    "source_health": [],
    "market_regime": {},
    "focus_categories": [],
    "candidates": [],
    "reserves": [],
    "cohorts": {
      "open": [],
      "midday": [],
      "afternoon": []
    }
  },
  "validation": {}
}
```

`payload` contains all logical inputs and outputs that define membership. The envelope's `universe_id`, `payload_sha256`, `accepted_at`, attempt metadata, and validation report are excluded from the payload hash. The payload's `valid_from` and other logical cutoffs are derived from accepted input artifacts rather than the compiler wall clock, so an identical retry hashes identically.

Each candidate contains at least:

- `ticker`, `cik`, `issuer_name`, and `exchange`;
- `category_ids` and primary `category_id`;
- `selection_tier` of `primary` or `honorable_mention`;
- category rationale and evidence references;
- source classification and source weight;
- deterministic rank components and global rank;
- rejection-free eligibility result;
- assigned cohort or reserve status.

Reserves are accepted, mapped candidates beyond the core 900, not unmatched broad-market filler. Policy v1 requires `core = 900`, `reserves = 100..500`, and therefore `total accepted candidates = 1,000..1,400`; any other count fails publication. Reserves support diagnosis and a future session build only—they never replace a member after acceptance.

### 11. Canonicalization and identity

Canonical payload bytes use UTF-8 JSON with sorted object keys, no insignificant whitespace, one trailing newline, UTC RFC 3339 timestamps, JSON `null` for missing values, decimal numbers normalized by schema, and arrays sorted by their declared immutable key. NaN and infinity are forbidden. Each array's order is part of its strict schema; adapters cannot rely on source row order.

Identity is content-addressed:

```text
payload_sha256 = sha256(canonical universe payload)
universe_id = cu_ + payload_sha256
cohort_id   = cc_ + sha256(universe_id | session_date | cohort_name)
scan_id     = cs_ + sha256(universe_id | cohort_id | scheduled_slot_cutoff)
attempt_id  = wall-clock attempt identifier, never part of scan identity
```

Changing any category, source snapshot, eligibility decision, candidate, rank, cohort, or reserve creates a new universe ID. Retrying identical inputs produces the same universe ID.

### 12. Publication and pointer semantics

Canonical payloads, attempt diagnostics, and acceptance state have separate storage identities:

```text
data/universes/YYYY-MM-DD/
  payloads/<universe_id>/
    universe-payload.json
  attempts/<attempt_id>/
    primary-research.json
    audit.json
    source-manifest.json
    rejected-candidates.jsonl
    acceptance-envelope.json
    validation.json
  accepted-universe.json
```

The compiler writes each attempt to a temporary sibling directory, validates every checksum and invariant, and writes the canonical payload separately. If the payload target already exists, it byte-compares canonical content and reuses it only on an exact match; the retry's diagnostics remain attempt-specific. Otherwise it `fsync`s files and directories and atomically renames the payload directory without overwrite. Under a per-session builder lock, it creates the accepted-universe pointer with first-writer-wins compare-and-swap semantics. The pointer contains the session date, universe ID, payload path/hash, authoritative acceptance-envelope path/hash, and supersession lineage.

An incomplete build never appears through the accepted pointer. Existing accepted artifacts are never modified in place. If a different universe is already accepted for that session, publication returns `accepted_universe_conflict`. Content artifacts are immutable; the session pointer may be superseded only with an authorized operator record containing actor, reason, prior/new IDs and hashes. Builder and scanner acquire locks in the same order, and compare-and-swap requires all three cohorts to remain `not_started`; otherwise supersession fails.

### 13. Scan consumption and retry behavior

The coordinator derives stable `scan_id` from the immutable scheduled slot cutoff, then atomically binds `cohort_id → scan_id` first-writer-wins before any dossier call. It persists the universe ID, cohort ID, exact cohort checksum, scheduled cutoff, actual first-attempt time, coordinator commit, Catalyst service commit, dependency-lock hash, registry and classification revisions, lookback, source-policy revision, calendar revision, discovery window, dynamic-state schema, and secret-free provider/config fingerprints in a versioned `scan_contract`; `scan_contract_sha256` covers every behavior-changing field.

Retry behavior:

- a partial retry reopens the same scan directory;
- every retry resolves through the cohort-to-scan binding and may not create a second scan;
- already persisted dossiers are reused;
- only missing tickers are scored;
- retries must match the complete scan contract and occur within the configured resume TTL;
- each dossier preserves its actual `as_of`; the design does not claim point-in-time provider reproducibility;
- after the resume TTL, an incomplete cohort fails rather than mixing evidence epochs;
- a completed scan returns its existing summary and cannot append or recommit decisions;
- record identity derives from `scan_id|ticker`, not a new wall-clock timestamp;
- one nonblocking workspace lock prevents overlapping cohort runs;
- a retry against a different universe or cohort checksum fails instead of mixing artifacts.

This extends the existing append-as-completed dossier behavior and idempotent decision ledger instead of replacing them.

### 14. Commit and delivery state

Live persistence currently spans multiple durable files. The dynamic design adds explicit scoring, report, commit, and delivery state to make crash recovery observable:

```text
scoring        -> scan contract fixed; zero or more immutable dossiers complete
prepared       -> dossiers and decisions complete, live files untouched
committing     -> durable reconciliation in progress
commit_complete -> ledgers, indexes, queue, and state agree by stable IDs
report_ready   -> byte-identical external report is eligible for emission
delivered      -> delivery adapter receipt is durably recorded
delivery_failed -> retry ceiling reached; report remains ready for operator recovery
```

The coordinator owns transitions through `report_ready`; the delivery adapter owns receipt states. Every transition has one writer, preconditions, durable evidence, and an idempotent recovery action. Recovery from `committing` reconciles stable IDs in append-only ledgers, the decision index, research queue, state, and summary. It never assumes that a missing final state update means earlier append operations did not happen. A completed scan may re-emit only the byte-identical report while delivery is unconfirmed.

Local report/commit effects are exactly-once by stable ID. External announcement is explicitly at-least-once unless the selected adapter proves a provider-side idempotency key or receipt lookup. A crash after provider acceptance but before local receipt may duplicate the same labeled delivery ID; operations reconcile that ID where the provider permits, and the system never claims exactly-once Slack delivery from local dedupe alone.

| Transition | Writer | Required durable evidence | Recovery |
| --- | --- | --- | --- |
| bound scan → `scoring` | coordinator | immutable scan contract and cohort binding | score only missing dossiers within resume TTL |
| `scoring` → `prepared` | coordinator | complete dossier and decision artifact hashes | validate hashes; do not score after transition |
| `prepared` → `committing` | coordinator | commit intent and stable record IDs | reconcile every target by ID |
| `committing` → `commit_complete` | coordinator | ledgers, indexes, queue, and state match intent | repeat reconciliation; never blind-append |
| `commit_complete` → `report_ready` | coordinator | immutable report bytes and delivery ID | recreate pointer to identical report |
| `report_ready` → receipt state | delivery adapter | adapter receipt or typed terminal error | retry identical bytes under same delivery ID |

### 15. Daily coverage state

Delivery deduplication and universe coverage remain separate concepts. `decision_index.json` continues to suppress unchanged candidate delivery for 72 hours; it does not prove daily ticker uniqueness.

The watchlist workspace adds `data/dynamic_state.json` with `schema_version: 1`. The current live legacy `data/state.json` is version 2, and older unversioned legacy files may also exist; both formats remain read-only migration inputs and are retired only after activation verification. The accepted-universe pointer and mode-transition record identify which mode is authoritative. Dynamic state adds:

- active `session_date` and `universe_id`;
- accepted manifest checksum;
- status for each cohort ID;
- exact core tickers completed per cohort;
- daily core union count;
- supplemental discovery tickers completed;
- session-wide supplemental ticker/CIK reservations by scan ID;
- commit/delivery status by scan ID;
- prior `last_success_at` and the existing decision-index lineage.

The end-of-day invariant is:

```text
core cohort sizes       = 300 / 300 / 300
core pairwise overlap   = 0 / 0 / 0
core union count        = 900
supplemental duplicates = 0
```

### 16. Supplemental event discovery

The existing bounded SEC/issuer-primary discovery lane remains complementary. It changes in three ways:

- exclude every ticker and CIK in the entire 900-name daily core, not only the active cohort;
- exclude all supplemental tickers already evaluated earlier that session date;
- persist canonical CIK and SEC snapshot identity in candidates, decisions, and daily exclusion state; reject any identity mismatch.

Discovery remains capped at 10 per scan and retains its source-event reconciliation. Reports distinguish core and supplemental coverage. Discovery never consumes a core slot and never excuses an incomplete core cohort.

Discovery windows are immutable schedule windows, not derived from global `last_success_at`: `open` covers the prior eligible session cutoff through the open cutoff; later slots cover `(prior slot cutoff, current slot cutoff]`. Completion order cannot change those windows. A recovered earlier slot reuses its original window, and prior/later same-day discovery CIKs remain excluded through the session ledger.

Before any supplemental dossier call, the coordinator atomically claims both ticker and CIK in a session-wide discovery reservation ledger keyed by `scan_id`. Later slots exclude completed and reserved identities; recovery reuses its original claims. A claim may be released only when no dossier was ever persisted for it. Once any dossier exists, the claim remains through session close even if the scan later fails, preventing an out-of-order recovery from evaluating the same issuer twice.

### 17. Scheduling

Market research, audit, compilation, and source validation run in a separate pre-market job. They must complete and publish an accepted universe at least 15 minutes before the 08:30 scan. Before implementation leaves shadow mode, the runtime contract must name the callable research and audit adapters, authentication, strict structured-output mode, source-reopening method, stage deadlines, retry/resume behavior, token/cost ceilings, and typed terminal failures. The 300-name live baseline already consumes approximately 466 seconds in the coordinator and 492 seconds end to end under a 900-second cron timeout; inline research would leave unsafe headroom and repeat expensive work.

Policy v1 uses these New York deadlines:

| Stage | Deadline |
| --- | --- |
| Job start | 06:30 |
| Research | 07:15 |
| Audit | 07:50 |
| Snapshot and compiler | 08:05 |
| Publication | 08:15 |

Each stage may retry only within its window; crossing a deadline produces a typed terminal failure and alert rather than compressing validation. Model/token and dollar ceilings are configuration values recorded in the run artifact.

The existing three scan times remain unchanged. `data/calendars/us-equities.json`, interpreted in `America/New_York`, defines session dates, DST, holidays, and early closes. It records its authoritative source, source revision, retrieval time, content checksum, generated-through date, update owner, and review cadence, and must cover at least 12 future months. A missing requested date or stale coverage fails scheduling. A holiday produces a typed skipped session. The first implementation preserves the existing 14:30 job on early-close days as a disclosed post-close scan; changing or compressing that slot requires a separate policy revision. Manual recovery records the requested session and slot explicitly.

Locks include owner, scan ID, acquisition time, and heartbeat. A stale lock is never stolen automatically; it produces an alert and operator recovery instruction. Later cohorts may run independently after the earlier process is confirmed dead, but end-of-day coverage remains incomplete until every frozen cohort succeeds.

Default freshness policy v1 is:

| Input | Maximum age at cutoff |
| --- | --- |
| Index, volatility, and breadth observations | 30 minutes |
| Sector and cross-asset observations | 60 minutes |
| Event and earnings calendar retrieval | 24 hours |
| Latest official macro release retrieval | 24 hours |
| Broad-universe holdings observation | Five eligible sessions |
| SEC identity retrieval | 24 hours |

Research and audit are accepted only for the named session and expire before the next session build. Provider policy may be stricter but never silently looser.

### 18. Failure policy

The following fail before scoring:

- no accepted universe for the current session date;
- expired research or source snapshot;
- audit missing or non-canonical;
- universe or cohort checksum mismatch;
- fewer or more than 900 core records;
- cohort size other than 300;
- overlap across cohorts;
- duplicate ticker or unapproved duplicate CIK;
- unresolved or unsupported security;
- missing category rationale or source lineage;
- compiler source-policy denial;
- conflicting active pointer or concurrent scan lock.

Research degradation remains typed. A missing source may remove a category or block research acceptance, but it cannot become bearish evidence or zero every unrelated category. Static `watchlist.json` remains a rollback fixture and audit reference, never an automatic failure substitute.

## Scope of Changes

1. **Universe research contract** — adapt the proven market-regime standard into structured focus-category and honorable-mention artifacts with source-family health and independent audit.
2. **Security-universe adapters** — add provider-neutral broad-market classification and SEC identity snapshots under explicit source policy.
3. **Deterministic compiler** — implement category expansion, validation, ranking, quota reconciliation, backfill, allocation, canonical hashing, and atomic publication.
4. **Coordinator consumption** — replace static file loading with accepted-universe/cohort validation while preserving existing scoring, classification, discovery, ledgers, reporting, and resume behavior.
5. **State and recovery** — introduce stable scan identities, daily coverage state, locks, commit reconciliation, and controlled migration from current version-2 or older unversioned legacy state files.
6. **Operations and observability** — add the separate pre-market job, slot-aware scans, build/scan health reporting, and operator-controlled activation and rollback.

### Repository Ownership

The implementation belongs primarily in `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist`. The local Catalyst Edge repository remains unchanged unless a reusable provider-neutral source-policy contract is intentionally extracted later. The MCP continues to accept one ticker and return one dossier.

### Out of Scope

- Changing Catalyst Edge's deterministic score, confidence formula, family weights, or `RESEARCH NOW`/`MONITOR`/`IGNORE` gates.
- Treating universe rank as evidence or directional confirmation.
- Brokerage, orders, execution, sizing, or automated trading.
- Predictive, profitability, or alpha claims.
- Market-outcome backtesting or threshold tuning.
- An intraday rebuild of the frozen 900-name core.
- Non-U.S. listings, OTC securities, funds, ETFs, derivatives, or crypto assets in the core universe.
- A universal industry ontology independent of the approved security snapshot; finer vertical taxonomies remain adapter capabilities.
- Silent fallback to stale or static universes.

## Alternatives Considered

### Option A: Rebuild an Independent 300-Name List Before Every Scan

Run full market research at 08:30, 11:30, and 14:30 and ask the model for more than 250 names each time.

**Advantages**: maximally current and conceptually close to the initial request.

**Why we rejected it**: independent runs cannot guarantee 900 unique names without a shared exclusion ledger; the same themes would naturally repeat names. Research would also run inside a scanner that already uses roughly half of its 900-second deadline. Different model outputs would make retries non-idempotent and could change the list after some dossiers were written.

### Option B: Event-First Discovery as the Entire Universe

Use current SEC 8-K and issuer-primary events to create the day's list, expanding the existing discovery cap until 900 names are found.

**Advantages**: every ticker begins with a fresh primary event and the existing provenance path is already implemented.

**Why we rejected it**: the SEC feed is issuer-event-first, not market/theme-first. It does not represent macro, geopolitical, sector-rotation, commodity, rate, or cross-market focus and cannot reliably produce 900 names without weakening event freshness or provenance.

### Option C: Static Broad-Index Rotation Without an Agent

Download a Russell 3000 or similar holdings universe and rotate 300 disjoint names through three scans using fund weight or ticker order.

**Advantages**: a structurally different system already knows a broad U.S. equity universe; allocation would be cheap, deterministic, and easy to validate.

**Why we rejected it**: it solves uniqueness but not relevance. The resulting coverage would still ignore current events, changing market regimes, geopolitical shocks, and sector/vertical focus—the central product requirement.

### Option D: Put Universe Selection Inside Catalyst Edge

Add a market-wide MCP tool and make the Catalyst service own broad discovery and dossier scoring.

**Advantages**: one service and one public API surface.

**Why we rejected it**: Catalyst Edge's current contract and collectors are intentionally ticker-scoped. Its GDELT and issuer registries cover reviewed issuers rather than a 900-name universe, and its registry caps at 200 issuers. Combining universe research with per-ticker evidence collection would blur source roles, increase request latency, and couple two independently recoverable systems.

## Trade-offs

| Decision | Trade-off | Mitigation |
| --- | --- | --- |
| One pre-market universe | Intraday macro regime changes do not reorder core cohorts | Keep cohorts immutable for auditability; use unique supplemental event discovery and rebuild next session |
| Independent audit required | More provider time and cost before the first scan | Run out of band with a firm publication deadline; persist resumable artifacts |
| Deterministic security expansion | Coarse source taxonomies may miss nuanced thematic relationships | Permit direct evidence-backed nominations and provider-neutral industry/SIC adapters; retain source/rationale fields |
| One ticker per CIK in v1 | Dual-class securities such as GOOG/GOOGL do not both consume core slots | A future versioned policy may introduce reviewed exceptions; v1 never does |
| No automatic stale/static fallback | A failed builder can stop the day's scans | Alert before 08:30, preserve diagnostic artifacts, and provide an explicit operator rollback mode |
| Broad-market source weight as tie-break | Fund weight favors larger companies | Category quotas and stratified cohorts preserve thematic breadth; weight is only an auditable within-category prior |
| 900 core plus up to 30 discovery names | Daily total may exceed 900 | Report core and supplemental counts separately; enforce zero duplicate evaluations |
| Source-policy gate on public downloads | Live activation may wait for rights review | Implement provider-neutral adapters and shadow mode first; do not equate accessibility with authorization |

## Solution Validation

### Target Case

The minimal executable form used the existing July 28 `EVENT-DRIVEN` research themes as a real focus input, BlackRock's current official iShares Russell 3000 data download as the broad candidate/classification source, and the SEC's current ticker/exchange JSON as the independent identity gate. BlackRock's sheet metadata reported 2,586 securities excluding cash and derivatives; the parser observed 2,591 raw holding-like rows before asset, location, exchange, identity, and duplicate-CIK filtering.

The prototype deliberately assigned a 150-name materials quota even though only 115 eligible materials issuers existed. This forced the honorable-mention path to fill a real 35-name shortage while preserving exact cohort and identity invariants.

### Minimal Executable Form

A throwaway read-only Python script fetched both live source artifacts, parsed the Russell 3000 holdings sheet, filtered U.S. equities, joined SEC CIK/exchange identity, deduplicated by CIK, expanded the research categories, applied deterministic quotas and honorable-mention backfill, allocated cohorts, and hashed canonical content. It did not write to either repository or mutate live state.

| Dimension | Desired | Measured | Delta |
| --- | ---: | ---: | ---: |
| Raw broad-market holding records parsed | Enough for 900 | 2,591 | 0 blocker |
| Eligible names after SEC validation and CIK dedupe | At least 900 | 2,494 | +1,594 reserve capacity |
| Core union | 900 | 900 | 0 |
| Open cohort | 300 | 300 | 0 |
| Midday cohort | 300 | 300 | 0 |
| Afternoon cohort | 300 | 300 | 0 |
| Pairwise cohort intersections | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| Unique CIKs in core | 900 | 900 | 0 |
| Forced materials shortage | 35 | 35 | 0 |
| Honorable mentions used | 35 | 35 | 0 |
| Canonical hash stable after JSON round trip | Yes | Yes | 0 |

Observed source identities:

- BlackRock snapshot date: `2026-07-30`
- BlackRock artifact SHA-256: `a8b885bab36e42e11e89ed71757c6a54196648b7fdecf7d689f3c49ee90ccdc3`
- SEC artifact SHA-256: `9684905b0ea10714903557ddbf3aaa91f18ed2d5923f07776b3076054d6456fc`
- Stress-universe canonical SHA-256: `e17d1a4913a169052481f163a05d108b234acf096fe2123e2dccd3d7f9a5e330`

### Reconciliation and Validation Boundary

The prototype validates the load-bearing mechanical premise: current real sources can supply enough classified, SEC-resolved equities to deterministically construct 900 unique CIKs, backfill a category shortage, partition 300/300/300 with zero overlap, and reproduce a canonical hash.

It does not validate that an automated daily research agent will always identify the best economic themes, that the independent audit runtime is available on Axe, that BlackRock automation/retention rights are approved, or that three dynamic shadow scans meet the target latency over multiple sessions. Those are explicit activation gates below, not claims delegated silently to implementation.

## Acceptance and Activation Gates

### Contract Tests

**Research, audit, and sources**

- `DU_INPUT_RESEARCH_SCHEMA` — reject unknown, missing, stale, or malformed research fields.
- `DU_SOURCE_POLICY_APPROVAL` — reject an absent, expired, or insufficient provider approval record.
- `DU_SOURCE_HEALTH_ISOLATION` — one provider failure cannot mutate unrelated category confidence or selection.
- `DU_AUDIT_PROVENANCE` — accepted research requires canonical audit, checksums, and reopened material sources.
- `DU_SECURITY_SNAPSHOT_SCHEMA` — validate every provider-neutral identity/classification field.
- `DU_SEC_IDENTITY_GATE` — reject unresolved, unsupported-exchange, malformed, fund, derivative, and OTC records.

**Compilation and allocation**

- `DU_UNIQUE_TICKER_AND_CIK` — reject every duplicate ticker or CIK.
- `DU_EXACT_CORE_900` — reject 899 or 901 core names.
- `DU_RESERVE_BOUNDS` — require 100–500 mapped reserves and 1,000–1,400 total accepted candidates.
- `DU_EXACT_COHORT_300` — reject any cohort other than 300.
- `DU_ZERO_COHORT_OVERLAP` — reject any pairwise intersection.
- `DU_HONORABLE_BACKFILL` — fill shortages by the declared ladder without weakening eligibility.
- `DU_DETERMINISTIC_ALLOCATION` — identical canonical inputs produce identical ranks, cohorts, and universe ID.

**Publication and recovery**

- `DU_ATOMIC_PUBLICATION` — interruption before acceptance leaves no new active pointer.
- `DU_IDENTICAL_PAYLOAD_REUSE` — identical builds reuse byte-identical payload content while preserving attempt-specific diagnostics.
- `DU_COHORT_SCAN_BINDING` — first writer binds one scheduled scan ID per cohort; a conflicting attempt fails.
- `DU_RESUME_TTL` — an expired incomplete scan cannot append new dossiers.
- `DU_SCAN_CONTRACT_MISMATCH` — any behavior-changing runtime input mismatch stops retry.
- `DU_SUPERSESSION_RACE` — pointer supersession fails once any cohort is no longer `not_started`.
- `DU_STALE_FALLBACK_FORBIDDEN` — missing current universe stops before Catalyst import.

**Discovery and downstream separation**

- `DU_DISCOVERY_DAILY_EXCLUSION` — discovery excludes the core 900 and prior same-day discoveries.
- `DU_DISCOVERY_ATOMIC_CLAIM` — concurrent and out-of-order slots cannot reserve or score the same supplemental ticker or CIK.
- `DU_SELECTION_CLASSIFICATION_SEPARATION` — universe priority cannot affect Catalyst classification gates.

### Integration Tests

- Build from fixture research, audit, broad-market, and SEC snapshots; verify exact hashes and cohorts.
- Run the same build twice and produce one accepted universe ID.
- Simulate process termination before and after every publication phase.
- Inject process termination around payload promotion, acceptance compare-and-swap, cohort binding, every commit transition, provider delivery success, and local delivery-receipt persistence.
- Start two builders concurrently and permit only one accepted publication.
- Fail several cohort ticker calls, retry the same scan ID, and score only missing dossiers.
- Recover slots out of completion order and preserve their immutable discovery windows and same-day CIK exclusions.
- Persist one supplemental dossier, fail its scan, run a later slot, then recover the earlier slot; assert one session claim and one evaluation for that ticker/CIK.
- Retry a completed cohort and append zero new decisions, signals, or delivery records.
- Simulate failure during each commit phase and reconcile by stable record IDs.
- Assert an invalid universe prevents Catalyst Edge construction and all provider calls.
- Migrate current version-2 and older unversioned legacy state formats while preserving the 72-hour decision index and append-only ledgers.
- Exercise old run directories that predate supplemental-discovery artifacts without treating them as current dynamic runs.

### Shadow Acceptance

Before activation:

1. Record source-policy approval for the broad-market adapter's automated access, retention, hashes, and derived internal outputs.
2. Generate real research, audit, and compiled universes for at least five consecutive eligible sessions and at least 30 isolated scan observations without changing live scan membership.
3. Human-review every focus category, every source-family degradation, all mapping rules, and a stratified sample of selected/rejected names.
4. Execute all three cohorts in an isolated workspace with external delivery disabled.
5. Verify 300/300/300 decisions, zero pairwise overlap, a 900-name core union, zero duplicate supplemental names, stable universe checksums, and valid append-only ledgers.
6. Demonstrate same-scan retry with no rescoring of completed dossiers and no duplicate delivery.
7. Retain raw durations and report p50/p95/max by slot and cold/warm cache. Before the sample can support p95, treat 720 seconds as a hard maximum; thereafter require p95 below 720 seconds, preserving at least 20% of the 900-second timeout.
8. Run the existing coordinator contract suite and the full Catalyst Edge offline suite without regression.
9. Enable universe publication first; enable dynamic scan consumption only after a valid accepted artifact is observed.

### Definition of Done

- A fresh audited universe is published before the first scan on every tested eligible session.
- Every accepted symbol has source-linked category rationale and SEC identity.
- Core daily coverage is exactly 900 unique tickers and 900 unique CIKs.
- Each scheduled scan evaluates exactly its frozen 300-name cohort.
- Supplemental discovery creates no same-day duplicate ticker or CIK.
- All retries are idempotent by universe, cohort, scan, and record identity.
- No partial build or partial live commit becomes delivery-eligible.
- Existing classification gates, paper-only wording, source provenance, and no-trading boundaries remain unchanged.
- Static rollback is operator-controlled and never silently triggered.
- Operations documentation includes schedules, locks, recovery, activation, rollback, source-policy status, and artifact locations.

## Implementation Phases

### Phase 0: Unblock the Operating Contracts

Production implementation is blocked until two machine-verifiable records exist:

1. One source-policy approval per provider and use case, stored in the watchlist repository's `config/source-policy.json`, naming endpoint, terms/account revision, transient versus retained use, permitted automation, retained fields, retention, content hashes, derived outputs, review owner, and expiry. Research citations, audit reopening, market data, holdings, calendar, and SEC identity reference their specific approval IDs; the compiler validates every referenced ID.
2. Research and audit runtime-adapter contracts naming callable surface, credentials, model/schema mode, source reopening, deadlines, retries, resume keys, cost ceilings, and terminal failures.

Until both validate, implementation is shadow-only: fixtures, adapters that do not schedule live retrieval, compiler logic, schemas, and isolated evaluation.

### Phase 1: Compiler and Artifact Contracts

Implement strict versioned models or JSON Schemas for proposed research, accepted audit, source manifest, universe payload/envelope, accepted pointer, dynamic state, commit state, and discovery identity. Unknown fields are forbidden; enums, timestamp rules, collection sizes, string lengths, referential integrity, numeric normalization, and array ordering are bounded and tested.

### Phase 2: Coordinator Integration and Shadow Runs

Add slot resolution, immutable scan contracts, daily coverage, discovery windows, commit recovery, and delivery receipts behind shadow mode. Only after the acceptance gates pass may an operator activate dynamic consumption.

## Migration and Rollback

Migration is explicit and non-destructive:

1. Verify and preserve `state.json`, `decision_index.json`, append-only decision/signal/discovery ledgers, and the static watchlist.
2. Introduce `data/dynamic_state.json` schema version 1 alongside legacy `data/state.json`; accept the current version-2 shape and older unversioned shape as read-only migration inputs, use the accepted pointer and mode-transition record to identify authority, and never infer daily coverage from the delivery index.
3. Build and validate a current universe in shadow mode.
4. Activate dynamic consumption behind an operator-controlled mode flag.
5. Preserve static `watchlist.json` and its provenance as the rollback fixture.

Rollback is an explicit operator action that disables dynamic consumption and restores the known static scanner contract. The transition records pre/post checksums, freezes the dynamic session ledger, displays an operating banner that the 900-unique contract is suspended, and selects the legacy record-ID mode.

Rollback never deletes dynamic universes, scan artifacts, or state history. Automatic fallback is forbidden because it would hide a research/compiler failure and silently violate `INV-NO-FALLBACK`.

## Open Concerns

- **Source-policy status:** the watchlist registry now records approved uses for bounded iShares holdings, the generated market calendar, and SEC identity. Research citations and independent audit reopening remain blocked, so no real research/audit artifact is activation-eligible.
- **Automated research/audit runtime:** a standalone untracked proof CLI now constructs bounded Codex-research and Claude-audit commands, but it is not scheduled or imported by the live scan path and both production runtime records remain blocked. Persisted attempts produced no successful research/audit pair: generic `gpt-5.6` was unsupported and a `gpt-5.6-terra` attempt exceeded its token ceiling. Separate capability probes proved Codex Sol search/schema output and Claude Code WebSearch/WebFetch structured output, but no complete research/audit artifacts or accepted pair exists. This is capability evidence, not a provider selection.
- **Proof-to-compiler integration:** the provider-proof research/audit models differ from the compiler's `ResearchProposal` and `AcceptedAudit` contracts, and no converter or orchestrator connects them. The Codex parser also reports no dollar cost, so its configured dollar ceiling cannot be evidenced. A successful CLI probe alone would therefore not satisfy the production runtime contract or produce compiler-ready input.
- **Claude integration boundary:** the proof uses the installed Claude Code CLI with `WebSearch`/`WebFetch`, not an Anthropic SDK or direct Claude API. Claude appears only in this manual proof path; the MCP and scheduled Watchlist path do not call it.
- **Calendar reproducibility and wiring:** `data/calendars/us-equities.json` identifies an `exchange_calendars` 4.13.2 XNYS build and passes the production-enabled loader in tests. The package is available only through an on-demand `uv --with` environment, is not declared or importable in the Catalyst service environment, and has no workspace generation/refresh command. The coordinator does not enable production-calendar loading. The recorded monthly refresh policy and operational production-calendar path are therefore not executable from the workspace.
- **Calendar contract completeness:** the current production JSON omits this design's retrieval-time, update-owner, review-cadence, session-date, and session open/close fields. Runtime eligibility is reduced to weekday-minus-retained-holidays. The current 4.13.2 XNYS source reports coverage through 2027-08-02, while the artifact claims generation through 2027-08-31. The artifact does not yet implement or reproducibly prove the full calendar contract described in section 17.
- **Static-path verification:** the remote unit/isolated suite passes 64/64 and Ruff passes. A 300-name default `async_main` integration test reaches live-state persistence with providers mocked. The 2026-08-03 11:30 ET scheduled run reached the real modified default path and failed closed on an IBOC SEC timeout; exact-run resume discarded and rescored the unreconciled dossier, then failed closed again when the source remained unavailable. Static membership, schedule, and invocation are preserved, but a successful post-edit scheduled run remains unobserved.
- **Operations path:** no pre-market research/audit/compiler job or dynamic runbook exists. Remote `AGENTS.md` and provenance document only the active static 300-name system.
- **Semantic quality is not alpha:** focus relevance can be reviewed and source-grounded, but this design does not establish predictive value or profitable selection. Outcome calibration remains a separate licensed-data program.

## Current State

The original baseline anchors below explain why the design was created. The reconciled operational state is maintained in the implementation plan: static 300-name membership and cron configuration remain live; the shadow implementation is preserved in local commit `5c4c1e8`; the modified default path has exercised fail-closed production and resume behavior but has not completed a successful post-edit scheduled run; Phase 0–2 dynamic code is fixture-only; the standalone provider proof is unscheduled; no accepted dynamic universe or dynamic state exists; and activation remains blocked. The `mini:` and local absolute-path anchors are live-only evidence, not portable repository links.

### Live Watchlist

- The committed watchlist is named `catalyst-300-fixed-2026-08-01` and contains exactly 300 tickers: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/data/watchlist.json:2-308`.
- Scheduled membership is explicitly fixed: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/data/watchlist-provenance.md:3-20`.
- `validate_watchlist` requires exactly 300 unique uppercase strings: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts/scan_coordinator.py:725-732`.
- Every run loads that file before creating the run-specific dossier ledger: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts/scan_coordinator.py:793-842`.
- Completeness requires every fixed and discovery ticker to have a dossier: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts/scan_coordinator.py:843-851`.
- Run decisions, report, and summary precede atomic live-state persistence: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts/scan_coordinator.py:852-930`.
- Runtime state is version 2, contains only last-run fields, and has no daily universe/cohort ledger: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/data/state.json:1-7`.
- The event-discovery lane ranks at most 10 new SEC/issuer-primary names by event recency: `mini:/Users/axe/.openclaw/workspace-catalyst-watchlist/scripts/scan_coordinator.py:476-507`.

### Catalyst Edge

- `ToolInput` requires one ticker: `catalyst_edge_mcp/models.py:71-78`.
- `catalyst_edge_score` exposes one-ticker evaluation: `catalyst_edge_mcp/server.py:133-149`.
- The service collects supported evidence only after receiving that ticker: `catalyst_edge_mcp/service.py:84-95`.
- The deterministic evidence score remains downstream of universe selection: `catalyst_edge_mcp/scorer.py:47-108`.
- The reviewed issuer registry is capped at 200 entries and is not a broad-market security master: `catalyst_edge_mcp/registry_config.py:55-78`.

### Reusable Historical Assets

- The existing research standard already covers market structure, macro, geopolitics, earnings, and sector participation: `/Users/ryanmonroe/.agents/skills/daily-options-research/references/research-standard.md:29-43`.
- Its current candidate funnel is intentionally limited to 15/8/5 and must not be reused as the universe ceiling: `/Users/ryanmonroe/.agents/skills/daily-options-research/references/research-standard.md:45-49`.
- The orchestrator provides a fail-closed staged-state pattern and same-day idempotency: `/Users/ryanmonroe/.agents/skills/daily-options-orchestrator/scripts/orchestrator.py:91-226`.
- The live 300 expansion demonstrated exact 300-symbol completeness and a 465.870-second coordinator runtime: `/Users/ryanmonroe/.claude_states/catalyst-edge-mcp/catalyst-300-commit-ready-08-01-26.md:14-31`.

## References

- [docs/research/2026-07-21-free-open-source-coverage-research.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-free-open-source-coverage-research.md)
- [docs/research/2026-07-21-catalyst-source-roadmap.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-catalyst-source-roadmap.md)
- [docs/research/2026-07-21-point-in-time-backtest-dataset-research.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-point-in-time-backtest-dataset-research.md)
- [TDD.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/TDD.md)
- [SEC EDGAR APIs and nightly bulk data](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC company ticker/exchange mapping](https://www.sec.gov/file/company-tickers-exchange)
- [iShares Russell 3000 ETF product and data download](https://www.ishares.com/us/products/239714/ishares-russell-3000-etf)
