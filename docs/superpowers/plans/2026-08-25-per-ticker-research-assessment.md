# Per-Ticker Research Assessment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, source-linked research disposition and exact next action to every Catalyst Edge ticker dossier without changing scoring math.

**Architecture:** Preserve adapter, scoring, summary, and data-quality behavior. Add one pure builder that ranks compact scored evidence, derives a typed research assessment, and attaches it to the existing response before request options suppress source payloads.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest, pytest-asyncio, Ruff, uv

**Spec:** `docs/superpowers/specs/2026-08-25-per-ticker-research-assessment-design.md`

## Global Constraints

- Keep `DeterministicScorer`, score thresholds, family weights, confidence math, `scoring_method=deterministic_v1`, and `model_status=not_trained` unchanged.
- Add no dependency, provider, configuration, LLM synthesis, cross-ticker ranking, portfolio action, trade instruction, release, publication, or deployment.
- Use only canonical `clm_` IDs in claim lists; `primary_claim_id` remains nullable.
- Build the assessment from unsuppressed compact evidence so request output options cannot change it.
- Empty and degraded states must return a typed assessment rather than raise.

---

### Task 1: Typed research assessment builder

**Files:**
- Modify: `catalyst_edge_mcp/models.py:15-280`
- Create: `catalyst_edge_mcp/research.py`
- Test: `tests/test_research.py`

**Interfaces:**
- Consumes: `Evidence`, `Direction`, and an existing `list[str]` of dossier checks.
- Produces: `ResearchDisposition`, `ResearchAssessment`, and `build_research_assessment(evidence: list[Evidence], *, missing_families: set[str], stale_families: set[str], checks: list[str]) -> ResearchAssessment`.

- [ ] **Step 1: Write failing enum and empty-state tests**

```python
from catalyst_edge_mcp.models import ResearchDisposition
from catalyst_edge_mcp.research import build_research_assessment


def test_empty_evidence_is_insufficient_with_stable_gaps():
    result = build_research_assessment(
        [],
        missing_families={"technical", "filings_news"},
        stale_families={"technical"},
        checks=["Retry with lookback_days=30 to check a wider filing window."],
    )

    assert result.disposition == ResearchDisposition.INSUFFICIENT_EVIDENCE
    assert result.primary_claim_id is None
    assert result.supporting_claim_ids == []
    assert result.contradicting_claim_ids == []
    assert result.blocking_gaps == ["filings_news", "technical"]
    assert result.next_action.startswith("Retry with lookback_days=30")
```

- [ ] **Step 2: Run the empty-state test and verify it fails**

Run: `uv run --frozen pytest tests/test_research.py::test_empty_evidence_is_insufficient_with_stable_gaps -v`

Expected: FAIL because `ResearchDisposition` and `catalyst_edge_mcp.research` do not exist.

- [ ] **Step 3: Add the response models**

```python
class ResearchDisposition(str, Enum):
    REVIEW_NOW = "review_now"
    MONITOR = "monitor"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ResearchAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: ResearchDisposition
    primary_claim_id: str | None = Field(default=None, pattern=r"^clm_[0-9a-f]{64}$")
    supporting_claim_ids: list[str] = Field(default_factory=list, max_length=20)
    contradicting_claim_ids: list[str] = Field(default_factory=list, max_length=20)
    blocking_gaps: list[str] = Field(default_factory=list, max_length=20)
    next_action: str = Field(min_length=1, max_length=500)
```

- [ ] **Step 4: Implement the minimal empty-state builder**

```python
def build_research_assessment(
    evidence: list[Evidence],
    *,
    missing_families: set[str],
    stale_families: set[str],
    checks: list[str],
) -> ResearchAssessment:
    gaps = sorted(missing_families | stale_families)
    if not evidence:
        return ResearchAssessment(
            disposition=ResearchDisposition.INSUFFICIENT_EVIDENCE,
            blocking_gaps=gaps,
            next_action=checks[0],
        )
    raise NotImplementedError
```

- [ ] **Step 5: Run the empty-state test and verify it passes**

Run: `uv run --frozen pytest tests/test_research.py::test_empty_evidence_is_insufficient_with_stable_gaps -v`

Expected: PASS.

- [ ] **Step 6: Add failing review, monitor, ranking, and de-duplication tests**

```python
@pytest.mark.parametrize(
    "direction,confidence,materiality,with_source",
    [
        (Direction.NEUTRAL, 0.9, "material", True),
        (Direction.BULLISH, 0.49, "material", True),
        (Direction.BULLISH, 0.9, "discovery_only", True),
        (Direction.BULLISH, 0.9, "not_material", True),
        (Direction.BULLISH, 0.9, "material", False),
    ],
)
def test_non_reviewable_primary_is_monitor(direction, confidence, materiality, with_source):
    item = claim_evidence("a", direction=direction, confidence=confidence, materiality=materiality)
    if not with_source:
        item.sources = []
    result = build_research_assessment(
        [item], missing_families=set(), stale_families=set(), checks=["Fallback check."]
    )
    assert result.disposition == ResearchDisposition.MONITOR


def test_review_now_ranks_and_deduplicates_canonical_claims():
    primary = claim_evidence("a", contribution=8, direction=Direction.BULLISH)
    supporting = claim_evidence("b", contribution=4, direction=Direction.BULLISH)
    supporting_duplicate = supporting.model_copy(deep=True)
    contradiction = claim_evidence("c", contribution=-3, direction=Direction.BEARISH)

    result = build_research_assessment(
        [contradiction, supporting_duplicate, primary, supporting],
        missing_families={"options_flow"},
        stale_families=set(),
        checks=["Fallback check."],
    )

    assert result.disposition == ResearchDisposition.REVIEW_NOW
    assert result.primary_claim_id == primary.context.claim_id
    assert result.supporting_claim_ids == [supporting.context.claim_id]
    assert result.contradicting_claim_ids == [contradiction.context.claim_id]
    assert result.blocking_gaps == ["options_flow"]
```

The `claim_evidence` test helper must build a `make_evidence(...)` fixture with `EvidenceContext(materiality=...)`, a canonical `clm_` ID made from the repeated hex character, and at least one source.

- [ ] **Step 7: Run the focused tests and verify they fail**

Run: `uv run --frozen pytest tests/test_research.py -v`

Expected: FAIL at the non-empty `NotImplementedError`.

- [ ] **Step 8: Implement stable ranking, reviewability, and claim partitioning**

```python
def _claim_id(item: Evidence) -> str | None:
    return item.context.claim_id if item.context else None


def _identity(item: Evidence) -> tuple[str, str, str, str]:
    source_record = (
        item.sources[0].accession_or_record_id
        if item.sources and item.sources[0].accession_or_record_id
        else ""
    )
    return (_claim_id(item) or "", item.family, item.signal, source_record)


def _rank(evidence: list[Evidence]) -> list[Evidence]:
    return sorted(
        evidence,
        key=lambda item: (-abs(item.contribution), -item.timestamp.timestamp(), _identity(item)),
    )


def _reviewable(item: Evidence) -> bool:
    materiality = item.context.materiality if item.context else None
    return (
        item.direction != Direction.NEUTRAL
        and item.confidence >= 0.50
        and materiality not in {"discovery_only", "not_material"}
        and bool(item.sources)
    )
```

Complete `build_research_assessment` by ranking, choosing the primary item, selecting `review_now` or `monitor`, collecting unique same-direction and opposite-direction canonical claim IDs in rank order, excluding the primary ID from `supporting_claim_ids`, and using `checks[0]` until Task 2 adds primary-specific selection.

- [ ] **Step 9: Run the focused tests**

Run: `uv run --frozen pytest tests/test_research.py -v`

Expected: PASS.

- [ ] **Step 10: Commit Task 1**

```bash
git add catalyst_edge_mcp/models.py catalyst_edge_mcp/research.py tests/test_research.py
git commit -m "feat: derive per-ticker research assessments"
```

### Task 2: Evidence-specific next action and service integration

**Files:**
- Modify: `catalyst_edge_mcp/summary.py:190-250`
- Modify: `catalyst_edge_mcp/research.py`
- Modify: `catalyst_edge_mcp/service.py:30-390`
- Modify: `tests/test_research.py`
- Modify: `tests/test_service.py`

**Interfaces:**
- Consumes: `evidence_check(item: Evidence) -> str | None`, the Task 1 builder, compact scored evidence, missing/stale sets, and existing checks.
- Produces: `CatalystEdgeResponse.research: ResearchAssessment` for every service response.

- [ ] **Step 1: Add a failing primary-specific action test**

```python
def test_primary_observation_owns_next_action():
    primary = claim_evidence("a", contribution=8, direction=Direction.BULLISH)
    primary.sources[0].accession_or_record_id = "0001045810-26-000001"

    result = build_research_assessment(
        [primary],
        missing_families=set(),
        stale_families=set(),
        checks=["Generic fallback."],
    )

    assert result.next_action == (
        "Open SEC accession 0001045810-26-000001 and review the filed item text and exhibits."
    )
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `uv run --frozen pytest tests/test_research.py::test_primary_observation_owns_next_action -v`

Expected: FAIL because the builder returns `Generic fallback.`.

- [ ] **Step 3: Extract the existing per-evidence check logic**

Add `evidence_check(item: Evidence) -> str | None` to `summary.py`. Move the existing filing accession, open-market Form 4, proposed-sale, and correction branches from `next_checks` into this function. Make `next_checks` call it while preserving its current newest-first order and three-check bound.

- [ ] **Step 4: Use the primary-specific check in the builder**

```python
primary_action = evidence_check(primary)
return ResearchAssessment(
    ...,
    next_action=primary_action or checks[0],
)
```

- [ ] **Step 5: Run summary/event and research tests**

Run: `uv run --frozen pytest tests/test_research.py tests/test_event_synthesis.py -v`

Expected: PASS with existing `next_checks` assertions unchanged.

- [ ] **Step 6: Add failing service integration assertions**

Extend `test_all_success_fixture_has_complete_coverage` to assert `response.research.disposition == ResearchDisposition.REVIEW_NOW`. Extend `test_no_adapter_response_is_explicit` to assert `INSUFFICIENT_EVIDENCE`, the five blocking gaps, and the existing retry as `next_action`. Add a test that evaluates the same source-backed evidence with default output options and with `include_sources=False, include_raw_signals=False`, then asserts both `research` objects are equal.

- [ ] **Step 7: Run the service tests and verify they fail**

Run: `uv run --frozen pytest tests/test_service.py -v`

Expected: FAIL because `CatalystEdgeResponse` requires `research` but the service does not provide it.

- [ ] **Step 8: Build and attach the assessment before output suppression**

In `CatalystService.evaluate`, after computing `compact`, `checks`, `missing`, and `stale`, call:

```python
research = build_research_assessment(
    compact,
    missing_families=missing,
    stale_families=stale,
    checks=checks,
)
```

Pass `research=research` to `CatalystEdgeResponse`. Keep `_apply_options` after this call so source suppression cannot change the assessment.

- [ ] **Step 9: Run focused integration tests**

Run: `uv run --frozen pytest tests/test_research.py tests/test_service.py tests/test_event_synthesis.py -v`

Expected: PASS.

- [ ] **Step 10: Commit Task 2**

```bash
git add catalyst_edge_mcp/summary.py catalyst_edge_mcp/research.py catalyst_edge_mcp/service.py tests/test_research.py tests/test_service.py
git commit -m "feat: attach research assessment to dossiers"
```

### Task 3: Public contract, release verifier, and documentation

**Files:**
- Modify: `tests/contract/test_mcp_contract.py:215-240`
- Modify: `scripts/verify_release.py:195-230`
- Modify: `tests/unit/test_release_verifier.py:15-65`
- Modify: `README.md:115-155`
- Modify: `tests/contract/test_documentation.py`

**Interfaces:**
- Consumes: required `CatalystEdgeResponse.research` schema and the typed no-data response.
- Produces: MCP output schema, release verification, and README examples that all require and describe the same research object.

- [ ] **Step 1: Update the contract test before implementation artifacts**

Change the expected output-schema required list to include `research` between `evidence` and `data_quality`, then assert:

```python
research = tool.outputSchema["$defs"]["ResearchAssessment"]
assert set(research["properties"]["disposition"]["$ref"].split("/"))
assert set(tool.outputSchema["$defs"]["ResearchDisposition"]["enum"]) == {
    "review_now",
    "monitor",
    "insufficient_evidence",
}
```

- [ ] **Step 2: Run the contract schema test**

Run: `uv run --frozen pytest tests/contract/test_mcp_contract.py::test_CT_RESPONSE_SCHEMA -v`

Expected: PASS because the Pydantic response model now exposes the required field.

- [ ] **Step 3: Make the release verifier require the new no-data assessment**

Add `research` to `_validate_no_data`'s exact required key set. Validate that it is a dictionary with `disposition == "insufficient_evidence"`, `primary_claim_id is None`, empty claim lists, and a non-empty `next_action`.

Update `_Result.structuredContent` in `tests/unit/test_release_verifier.py` with:

```python
"research": {
    "disposition": "insufficient_evidence",
    "primary_claim_id": None,
    "supporting_claim_ids": [],
    "contradicting_claim_ids": [],
    "blocking_gaps": [
        "filings_news",
        "insider_trading",
        "options_flow",
        "social",
        "technical",
    ],
    "next_action": "Retry with lookback_days=30 to check a wider filing window.",
},
```

- [ ] **Step 4: Run release verifier tests**

Run: `uv run --frozen pytest tests/unit/test_release_verifier.py -v`

Expected: PASS.

- [ ] **Step 5: Document all three dispositions**

Update README's result explanation to state that `research.disposition` prioritizes research only and is not a trade signal. Add a `research` object to each JSON example: `review_now` for the directional example, `monitor` for the partial neutral example, and `insufficient_evidence` for the no-data example.

Extend `test_README_JSON_EXAMPLES_PARSE_AND_INCLUDE_REQUIRED_BEHAVIORS` to assert that the three disposition values are present and that every response example contains a non-empty `next_action`.

- [ ] **Step 6: Run documentation and contract tests**

Run: `uv run --frozen pytest tests/contract/test_documentation.py tests/contract/test_mcp_contract.py tests/unit/test_release_verifier.py -v`

Expected: PASS.

- [ ] **Step 7: Run the full verification suite**

```bash
uv run --frozen pytest
uv run --frozen ruff check .
uv build --no-sources
git diff --check
```

Expected: all tests pass, Ruff reports no errors, wheel and sdist build successfully, and `git diff --check` emits no output.

- [ ] **Step 8: Commit Task 3**

```bash
git add README.md catalyst_edge_mcp tests scripts/verify_release.py docs/superpowers/plans/2026-08-25-per-ticker-research-assessment.md
git commit -m "docs: publish research assessment contract"
```

### Task 4: Exact-head final audit

**Files:**
- Read: all changed files
- Test: full repository

**Interfaces:**
- Consumes: the complete feature branch.
- Produces: an exact-head local verification receipt; no push, PR, release, publication, or deployment.

- [ ] **Step 1: Inspect the complete branch diff**

Run: `git diff --stat origin/main...HEAD && git diff --check origin/main...HEAD && git status -sb`

Expected: only the safe worktree ignore, design/plan, research assessment implementation, focused tests, verifier, and README are changed; the worktree is clean.

- [ ] **Step 2: Re-run exact-head verification**

```bash
uv run --frozen pytest
uv run --frozen ruff check .
uv build --no-sources
```

Expected: the same green result at the final `git rev-parse HEAD`.

- [ ] **Step 3: Record the local handoff**

Report the branch name, exact HEAD, commits, test result, Ruff result, build result, and the explicit boundary that production remains version `0.1.4` until a separately authorized exact-version release and deployment.
