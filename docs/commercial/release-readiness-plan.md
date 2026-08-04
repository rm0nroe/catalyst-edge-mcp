# Public Local Beta Release Readiness Plan

**Status:** Published 2026-08-04 through the public GitHub release, PyPI, Codex stdio
configuration, and MCP Registry. The Claude one-click `.mcpb` is excluded until
production-trusted signing is verifiable. The landing-page target remains unresolved and
must not be invented.

## Release target

Ship one complete free `Catalyst Edge Local Beta` that a technical self-directed investor
can install without a call, interview, demonstration, custom integration, or customer
qualification.

Required channels:

- public GitHub repository and versioned GitHub release;
- PyPI wheel and source distribution;
- one copy-paste Codex stdio configuration path;
- one manual Claude Desktop stdio path using the pinned PyPI package while the trusted
  one-click `.mcpb` channel is withheld; and
- MCP Registry metadata only after the permanent public package endpoint works.

Hosted access, authentication, billing, tenancy, dashboards, alerts, brokerage
integration, and managed support are outside this release.

## Gates

| Gate | Required evidence | Current state |
| --- | --- | --- |
| R0 — scope freeze | PRD/TDD/GTM agree on two local read-only tools, one ticker per call, deterministic unbacktested scoring, typed missingness, and no recommendation | Met after publication documentation and configuration recheck. |
| R1 — reproducible artifact | Clean reviewed commit; matching package version/tag; wheel, sdist, and MCPB install; SHA-256 manifest and release notes | PR #15 merged the SEC claim fix at `f387d1c`. GitHub and PyPI serve the exact reviewed wheel `6a9d0910...` and sdist `5383f14a...`. The 47-member unsigned MCPB `53cd8a77...` remains compatibility QA only and is excluded from distribution. |
| R2 — validation CI | Lock, lint, Python 3.10/3.14 tests, stdio/HTTP contracts, clean build, installed-artifact and MCPB verification | The security refresh updates locked `cryptography` from vulnerable `49.0.0` to fixed `50.0.0`. Python dependency audit, npm audit, Ruff, all 463 tests on both Python versions, deterministic builds, inventory, and installed stdio/HTTP probes pass. Publication-workflow PRs #17–#19 also passed the complete six-check validation and CodeQL set. |
| R3 — public configuration | SEC identity required; issuer/GDELT/Bluesky disabled by default; package metadata, `.env.example`, README, and runtime agree | Implemented. Public PyPI URLs and pinned Codex/Claude manual stdio instructions now agree with the loopback-only runtime and disabled-by-default sources. |
| R4 — self-serve onboarding | Clean local wheel install plus actual Codex and Claude Desktop tool discovery without package-code edits | A fresh isolated PyPI 0.1.1 install discovers exactly `catalyst_edge_score` and `catalyst_edge_claim_sources` and returns the typed no-data case. Codex has an enabled global stdio registration pinned to `catalyst-edge-mcp==0.1.1`; prior Claude manual stdio QA discovered the same two tools. The trusted Claude one-click channel remains withheld. |
| R5 — release sample | Five fixed public tickers produce five schema-valid dossiers, complete available claim pagination, and explicit missing/rejected evidence; one sanitized example is safe to publish | The public-readiness wheel produced five schema-valid SEC-only HOOD/AAPL/NVDA/TSLA/RKLB dossiers and typed missingness. HOOD returned one real two-filing claim; two one-source pages reconciled `2 returned = 2 unique = total_sources`, with terminal `next_cursor=null`, SEC-only `primary_regulator` sources, and `approved` policy decisions. Ryan approved the Evidence Terminal launch package on 2026-08-03. |
| R6 — rollback | Prior artifact/configuration can be restored without deleting the local evidence store | Met for the QA path. The materialized isolated SQLite store retained its exact SHA-256, sentinel, 11-table schema, and `ok` integrity result across uninstall of the unsigned fallback, install/configuration of the self-signed QA artifact, and fresh Claude/Codex calls. |
| R7 — publication authority | Public-source rights/defaults, package inventory, security notes, final target URLs, and exact publication actions are reviewed and explicitly approved by Ryan | Met for public GitHub, `v0.1.1`, PyPI, Codex, and MCP Registry on 2026-08-04. Claude `.mcpb` and unresolved landing-page deployment are excluded. |

The paid Hosted Pro experience retains a separate legal, security, privacy, billing, and
operating gate; it is not part of Local Beta readiness.

## Hosted Pro measurement boundary

The Local Beta page may include `Hosted Pro — $29/month, coming soon` only as a paid-intent
measurement surface. It must separate raw verified intent from the activation-linked subset,
use double opt-in and deduplication, retain offer version/source, exclude bots/staff/QA/
duplicates/“maybe,” and keep successful Local Beta activation privacy-preserving.

The current plan uses three recent activation-linked thresholds:

- **350:** separately authorize at most a 56-hour disposable OAuth/client spike;
- **1,350:** separately authorize one scoped legal/source/payment-provider review; and
- **11,100:** re-cost and reconsider the complete build with observed data.

The first two are heuristic risk-budget caps. The last is a safeguarded planning gate, not
automatic implementation authority. Intent expires after 180 days unless voluntarily
reconfirmed through the current self-serve offer. The raw verified intent rate must also
retain a one-sided 95% Wilson lower bound of at least 3%; activation yield is reported
separately. No auth, billing, tenancy, hosted operations, payment, or paid delivery belongs
to R0–R7.

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
- Publish hashes for the wheel and sdist. Do not attach the unsigned or self-signed MCPB.
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
3. Add the pinned PyPI executable to Codex or Claude Desktop over stdio.
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

- [x] Current diff is reviewed and committed without unrelated files.
- [x] R0–R6 evidence is attached to the release record.
- [x] Runtime, `.env.example`, README, runbooks, rights matrix, and `server.json` agree.
- [x] Codex and Claude Desktop manual stdio exact two-tool onboarding is measured.
- [x] Wheel and sdist hashes match the final tagged artifacts; MCPB is excluded.
- [x] Public-safe sample and security/source limitations are reviewed.
- [x] Paid-intent measurement copy, double opt-in, deduplication, offer-version/source,
      activation-link privacy, raw-intent denominator, and exclusion rules are reviewed.
- [x] Exact feasible publication targets and actions received Ryan authorization.

## Completed publication sequence

Completed in the authorized order:

1. Landed the security/readiness follow-up after fresh CI.
2. Rebuilt and verified the exact final wheel and sdist from reviewed `main`.
3. Published the repository and GitHub release `v0.1.1` with the reviewed wheel, sdist,
   and checksum manifest, but no MCPB.
4. Published PyPI project `catalyst-edge-mcp` and verified a clean isolated install from
   the permanent endpoint.
5. Published MCP Registry name `io.github.rm0nroe/catalyst-edge-mcp` after PyPI verification.
6. Recorded the unresolved landing-page target; no domain or unrelated deployment was
   invented.
