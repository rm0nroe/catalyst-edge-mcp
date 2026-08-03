# Public Local Beta Release Readiness Plan

**Status:** Current execution plan for the builder-first self-serve GTM. This document
does not authorize publication. Ryan must approve the exact repository, release, PyPI,
MCP Registry, `.mcpb`, and landing-page targets before any public action.

## Release target

Ship one complete free `Catalyst Edge Local Beta` that a technical self-directed investor
can install without a call, interview, demonstration, custom integration, or customer
qualification.

Required channels:

- public GitHub repository and versioned GitHub release;
- PyPI wheel and source distribution;
- one copy-paste Codex stdio configuration path;
- one signed Claude Desktop `.mcpb` for the public Claude installation path; and
- MCP Registry metadata only after the permanent public package endpoint works.

Hosted access, authentication, billing, tenancy, dashboards, alerts, brokerage
integration, and managed support are outside this release.

## Gates

| Gate | Required evidence | Current state |
| --- | --- | --- |
| R0 — scope freeze | PRD/TDD/GTM agree on two local read-only tools, one ticker per call, deterministic unbacktested scoring, typed missingness, and no recommendation | Met; recheck after documentation/config changes |
| R1 — reproducible artifact | Clean reviewed commit; matching package version/tag; wheel and sdist install; SHA-256 manifest and release notes | Fresh uncommitted wheel/sdist proof passes exact inventory/install/tool probes; clean commit, tag, and final release record remain open |
| R2 — validation CI | Lock, lint, Python 3.10/3.14 tests, stdio/HTTP contracts, clean build, installed-artifact verification | PR #8 passed all three GitHub jobs for commit `3673039`; current changes require a new run |
| R3 — public configuration | SEC identity required; issuer/GDELT/Bluesky disabled by default; package metadata, `.env.example`, README, and runtime agree | Implemented; focused contracts and full 443-test suite pass locally |
| R4 — self-serve onboarding | Clean local wheel install plus actual Codex and Claude Desktop tool discovery without package-code edits | Fresh local SDK first attempt passed in 3.49 seconds; Codex/Claude user-path proof and `.mcpb` remain open |
| R5 — release sample | Five fixed public tickers produce five schema-valid dossiers, complete available claim pagination, and explicit missing/rejected evidence; one sanitized example is safe to publish | Existing local runner/proof is reusable; public-safe regenerated sample remains open |
| R6 — rollback | Prior artifact/configuration can be restored without deleting the local evidence store | Prior `0.1.0 -> 0.1.1 -> 0.1.0` proof passed; repeat for the final public candidate |
| R7 — publication authority | Public-source rights/defaults, package inventory, security notes, final target URLs, and exact publication actions are reviewed and explicitly approved by Ryan | Open; blocks publication |

Passing R0–R6 does not authorize R7. A paid Hosted Pro experience has a separate legal,
security, privacy, billing, and operating gate; it is not part of Local Beta readiness.

## Required CI lanes

The existing read-only workflow must run on pull requests and release tags:

1. `uv lock --check`.
2. `uv run ruff check .`.
3. `uv run pytest -q` on Python 3.10 and 3.14.
4. Tool/schema, stdio, loopback HTTP, and claim-pagination contract tests.
5. `uv build --no-sources` from a clean checkout.
6. Fresh wheel/sdist installation, exact entrypoint and two-tool discovery, and one
   schema-valid no-data call.
7. Package inventory checks excluding `.env`, credentials, SQLite/WAL state, cache,
   logs, demo output, and provider payloads.
8. SHA-256 and test summaries retained in the job summary/release record.

Live-provider checks remain opt-in and separate. External availability or one live
success never replaces offline contract validation.

## Version and artifact procedure

- The package version, git tag, wheel, sdist, `server.json`, and release notes must agree.
- Build from a clean reviewed commit after required CI passes.
- Include `LICENSE`, `README.md`, the packaged reviewed registry, public installation
  runbook, and release-sample runbook.
- Publish hashes for the wheel, sdist, and signed `.mcpb`.
- Retain the prior accepted artifacts/configuration for rollback.
- Do not publish customer data, personal Watchlist data, credentials, `.env`, local state,
  generated dossiers, or raw provider payloads.

## Public configuration contract

The public install must state:

- Python/`uv` and MCP-client prerequisites;
- the required monitored SEC identity format;
- SEC rate/fair-access behavior;
- issuer feeds, GDELT, Bluesky, options, and sentiment disabled by default;
- the exact review required before any opt-in source is enabled;
- local evidence-store path, retained fields, backup, and deletion behavior;
- loopback-only HTTP boundary and stdio default;
- source-outage and typed-missingness behavior;
- secret-free logs/diagnostics; and
- rollback commands that preserve the evidence store.

## Self-serve onboarding proof

Measure from artifact verification to exact two-tool discovery in each supported client:

1. Install the pinned wheel into a clean supported Python environment.
2. Configure a monitored SEC identity and absolute local evidence-store path.
3. Add the installed `catalyst-edge-mcp` executable to Codex and Claude Desktop.
4. Confirm exact discovery of `catalyst_edge_score` and
   `catalyst_edge_claim_sources`.
5. Invoke one ticker and inspect the unbacktested/no-recommendation warning.
6. Retain first-attempt duration, commands, versions, exits, corrections, and readback.

No interview or user call is required. The proof is an internal clean-environment QA run.

## Release-sample proof

Use fixed sanitized public tickers, never holdings or personal portfolio data. Retain:

- five separate schema-valid calls;
- one dossier showing method/model status, evidence, warnings, and next checks;
- every page of one available grouped claim with exact count/no duplicates;
- one typed missing/rejected-data case; and
- a sanitized 60–90 second example suitable for the launch page.

The sample proves the product contract, not alpha, returns, market-wide coverage, or
willingness to pay.

## Exit checklist

- [ ] Current diff is reviewed and committed without unrelated files.
- [ ] R0–R6 evidence is attached to the final release record.
- [ ] Runtime, `.env.example`, README, runbooks, rights matrix, and `server.json` agree.
- [ ] Codex and Claude Desktop exact two-tool onboarding is measured.
- [ ] Wheel, sdist, and signed `.mcpb` hashes match the final artifacts.
- [ ] Public-safe sample and security/source limitations are reviewed.
- [ ] Exact publication targets and actions receive explicit Ryan authorization.
