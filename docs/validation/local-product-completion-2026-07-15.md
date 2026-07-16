# Local Product Acceptance Boundary — 2026-07-15, corrected 2026-07-16

## Outcome

The zero-subscription Catalyst Edge MCP meets the current documented local
acceptance corpus. This is not a claim of general SEC document understanding.
Optional paid evidence families, hosted distribution, and broader semantic
extraction remain explicit future capabilities rather than blockers for this
bounded local release.

## Automated verification

- `uv lock --check`: passed.
- `uv run ruff check .`: passed.
- `uv run pytest -q`: 372 tests passed.
- `uv build`: source distribution and wheel built successfully.
- Wheel inspection confirmed the automatic lifecycle, strict registry loader,
  and packaged reviewed JSON registry are included.
- Stdio and streamable-HTTP MCP contract tests passed.

## Real-case product evaluation

The 25-case official-SEC evaluation passed primary-link provenance,
classification, accepted-timestamp freshness, distinct-event behavior, and
dossier direction within the recorded corpus. It exposed and closed
bankruptcy-priority, merger-delisting, and recorded Item 8.01 specificity
defects. See
`real-catalyst-evaluation-2026-07-15.md`.

No numeric scorer changes were made because the corpus has no forward-return
labels. The scorer remains deterministic and explicitly unbacktested.

The `sec-primary-document-v1` enrichment layer records rule identity and version
and supports only explicit completed debt offerings, entered or amended equity
distribution agreements, actual repurchase activity, and filed prospectus
supplements. Proposed, negated, unsupported, and multiple-specific-event cases
remain generic. Representative HTML, table, inline-XBRL, amendment, and
near-match fixtures verify those fail-closed semantics.

## Live acceptance

- A 30-day official-SEC run over AAPL, NVDA, TSLA, RKLB, and BRK-B completed.
- NVDA's recorded Item 8.01 debt-offering wording matched the bounded
  primary-document rule and retained a SHA-256 hash without retaining the body.
- TSLA financial results and RKLB's material agreement classified correctly.
- AAPL and BRK-B correctly returned `no_observations` for the 30-day window.
- A bounded GDELT refresh completed for all five reviewed issuers; subsequent
  `catalyst-edge-health` output reported all five as `fresh`.
- Final RKLB smoke returned `configuration_ready=true`, SEC provenance,
  fresh directional SEC evidence, fresh GDELT evidence, and
  `launch_ready=true`.

Expected typed limitations remained: issuer feed unavailable for RKLB,
insufficient Bluesky comparison sample, licensed options/OHLC unavailable, and
the deterministic scorer not backtested.
