# Per-Ticker Research Assessment Design

## Goal

Make each Catalyst Edge dossier tell an analyst or builder what to review next without changing the public deterministic score, making a predictive claim, or producing a trading instruction.

This is the first half of objective D: improve actionable research now, then evaluate predictive accuracy only after rights-cleared point-in-time outcomes are available.

## Scope

The change is limited to the existing ticker-in, evidence-out MCP response. It does not add cross-ticker ranking, portfolio state, Watchlist classifications, an LLM synthesis step, data providers, model promotion, publication, or deployment.

## Architecture

Keep the current path intact and append one pure assessment step:

```text
adapters -> normalized evidence -> scorer -> summary
                                      |
                                      v
                    research assessment -> response
```

`DeterministicScorer` continues to own score, direction, confidence, and evidence contributions. A new deterministic builder consumes the compact scored evidence, data-quality state, and evidence-specific checks. The builder never changes the score or selects a trade.

The same builder can consume a future promoted `trained_softmax` result because it depends on the existing scored-evidence contract, not on deterministic-v1 internals.

## Response Contract

Add a required `research` object to `CatalystEdgeResponse`:

```json
{
  "disposition": "review_now",
  "primary_claim_id": "clm_...",
  "supporting_claim_ids": ["clm_..."],
  "contradicting_claim_ids": ["clm_..."],
  "blocking_gaps": ["options_flow", "technical"],
  "next_action": "Open SEC accession ... and review the filed item text and exhibits."
}
```

The disposition enum is:

- `review_now`: a fresh, directional, reviewable observation exists.
- `monitor`: evidence exists, but it is neutral, weak, discovery-only, not material, or lacks a reviewable source.
- `insufficient_evidence`: no fresh normalized evidence exists.

`primary_claim_id` is nullable because some valid adapters expose source-linked evidence before it has a canonical stored claim. Claim lists include only canonical immutable claim IDs and never synthetic candidate identifiers.

## Deterministic Rules

Rank compact evidence using the current product ordering: absolute contribution descending, timestamp descending, then a stable evidence identity. The first item is the primary observation.

Assign `review_now` only when the primary observation:

1. is bullish or bearish;
2. has evidence confidence of at least `0.50`, matching the existing low-confidence warning boundary;
3. is not marked `discovery_only` or `not_material`; and
4. has at least one source record.

Assign `monitor` for every other non-empty evidence set. Assign `insufficient_evidence` for an empty set.

Supporting claims are canonical claims in the primary direction. Contradicting claims are canonical claims in the opposite direction. Preserve rank order and omit duplicates. Neutral claims appear in the dossier but not in either claim list.

`blocking_gaps` is the stable, de-duplicated union of missing and stale evidence families. It explains coverage constraints without treating missing evidence as bearish evidence.

`next_action` targets the primary observation using the existing evidence-specific verification language. When that observation has no specialized check, reuse the first existing dossier check. The no-evidence fallback remains the current wider-window retry.

## Components

- `models.py`: add `ResearchDisposition` and `ResearchAssessment`; require `research` on `CatalystEdgeResponse`.
- `research.py`: add the pure assessment builder and evidence-specific next-action selection.
- `summary.py`: expose the existing per-evidence check logic for reuse; preserve current `next_checks` output.
- `service.py`: build the assessment after compacting scored evidence and before response construction.
- Tests and contract fixtures: prove response semantics and preserve existing scoring output.

No new dependency, configuration, abstraction layer, or runtime service is needed.

## Data Flow

1. Adapters collect and normalize evidence as today.
2. The scorer calculates unchanged contributions and edge fields.
3. The service compacts evidence with contradiction preservation.
4. Existing summary and check generation run.
5. The research builder ranks the compact evidence and derives the assessment.
6. Request options may suppress source payloads or raw signals, but the assessment is built from the unsuppressed internal evidence so its disposition is stable.
7. The response returns the unchanged edge, summary, evidence, data quality, and checks plus the new research object.

## Failure and Safety Behavior

The builder is total for every valid response state: empty evidence produces `insufficient_evidence`; missing contexts or claim IDs remain valid; duplicate claim IDs are removed deterministically.

The assessment does not inspect raw provider payloads, credentials, portfolio state, or future returns. It emits no `buy`, `sell`, expected-return, or execution language. Provider failures remain represented by existing typed family statuses, warnings, and reason records.

Shadow-model failures remain response-invisible. The new assessment consumes only the public scorer result, so enabling a shadow scorer cannot change it.

## Compatibility and Release Boundary

The new required response field is an intentional MCP response-contract addition. Existing fields and scoring values remain unchanged. Contract documentation and fixtures must be updated with the implementation.

This branch may be committed locally, but it does not authorize a package release, PyPI publication, production deployment, data purchase, model promotion, or predictive marketing claim.

## Verification

Use one focused test module for the pure builder and update only the service and contract tests affected by the response field.

Required checks:

1. Empty evidence returns `insufficient_evidence` with the wider-window next action.
2. Directional, source-linked, sufficiently confident evidence returns `review_now`.
3. Neutral, low-confidence, discovery-only, not-material, or source-free evidence returns `monitor`.
4. Supporting and contradicting canonical claims are ranked and de-duplicated deterministically.
5. Missing and stale families become stable blocking gaps without affecting score or direction.
6. Source/raw-signal suppression does not alter the assessment.
7. Shadow scoring cannot alter the public response.
8. Existing scorer math tests remain byte-for-byte unchanged.

Run the focused tests first, then `uv run --frozen pytest`, `uv run --frozen ruff check .`, and `uv build --no-sources`.

## Deferred Work

- Cross-ticker research queues remain in the separate Watchlist system.
- Portfolio-aware actions remain out of scope.
- Predictive accuracy work waits for written rights and real point-in-time outcome data.
- Release, publication, deployment, and runtime acceptance require separate exact-version gates.
