---
date: 2026-08-01T16:09:00-04:00
researcher: ryanmonroe
git_commit: 3ddec750ae025c8b990ecfbad0b0346c8c625595
branch: codex/dynamic-market-universe-tdd
repository: catalyst-edge-mcp
topic: "Find the PRD/TDD, verify implementation completion, and identify the remaining path to monetization"
tags: [research, catalyst-edge, mcp, monetization, product-readiness, self-serve]
status: complete
commercial_decision_status: superseded-by-builder-first-product-led-plan
last_updated: 2026-08-02
last_updated_by: ryanmonroe
last_updated_note: "Reconciled to the current self-serve Local Beta and Hosted Pro paid-intent decision"
---

# Research: Catalyst Edge MCP monetization readiness

## Decision status

`GTM_PLAN.md` is the current monetization authority. The earlier managed-Watchlist and
customer-installed design-partner recommendations are superseded and must not be
executed.

The current direction is:

- analysts and builders, including retail traders and technically capable individual
  investors who build their own AI research workflows;
- a complete free self-serve `Catalyst Edge Local Beta`;
- a `Hosted Pro — $29/month` paid-intent test before hosted infrastructure is built; and
- no interviews, counsel quote requests, prospect lists, boutique-fund targeting,
  founder-led demos, or design-partner sales.

## Product readiness

- `PRD.md` and `TDD.md` define a standalone local MCP that answers what changed for a
  ticker, what supports or contradicts it, how confident an agent should be, and what to
  check next.
- The implementation exposes two read-only tools over stdio and loopback HTTP:
  `catalyst_edge_score` and `catalyst_edge_claim_sources`.
- Scoring is deterministic, documented, unbacktested, and non-advisory. Missingness is
  typed and never becomes bearish evidence.
- The bounded local implementation has passed offline contracts, real SEC semantic
  evaluation, provenance pagination, package build/install, rollback, and local SDK
  onboarding evidence.
- The product does not implement a UI, alerts, portfolio personalization, brokerage
  execution, cloud tenancy, authentication, billing, or predictive-performance claims.

## Distribution readiness as of 2026-08-02

- PR #8 merged at `987710a17f2ea911435069dfbe6d982c10f77600` after successful Python
  3.10, Python 3.14, and installed-artifact GitHub checks for head `3673039`.
- The repository remains private.
- No git tag, GitHub release, PyPI project, MCP Registry publication, or signed `.mcpb`
  exists.
- `server.json` and package metadata are prepared but do not constitute publication.
- The current local work changes public defaults to SEC-only: issuer feeds, GDELT, and
  Bluesky are disabled unless explicitly enabled after source/output review.
- The public README, release plan, rights matrix, release-sample runbook, and local-user
  installation runbook are aligned to the builder-first self-serve path.
- The full 443-test suite, lock check, Ruff, fresh wheel/sdist build/install, exact two-tool
  stdio/HTTP probes, package inventory, and 3.49-second SDK onboarding pass locally for
  the uncommitted public-default changes.

These are point-in-time facts. They prove technical preparation, not public availability,
paid demand, investment performance, or legal clearance for Hosted Pro.

## Current release path

1. Finish and verify the conservative public configuration.
2. Build the final candidate from a clean reviewed commit and rerun required GitHub CI.
3. Prove exact two-tool onboarding in Codex and Claude Desktop.
4. Regenerate a fixed-ticker, public-safe sample dossier/provenance artifact.
5. Build, sign, and test the Claude Desktop `.mcpb`; manual Claude configuration is
   pre-release QA only and does not satisfy the public distribution requirement.
6. Present the exact GitHub, release, PyPI, Registry, `.mcpb`, and landing-page targets to
   Ryan for explicit publication authorization.
7. Launch the free Local Beta and measure package/install/support and Hosted Pro signup
   evidence without interviews or outbound prospecting.

## Source and claims boundary

- SEC is the public baseline when the user supplies a monitored compliant identity.
- Issuer feeds remain disabled pending source-specific reuse decisions.
- GDELT's official terms permit commercial use and redistribution but require a GDELT
  citation/link; the current output does not yet implement that requirement, so GDELT
  remains disabled by default.
- Bluesky remains disabled pending a documented user-content, privacy, retention, and
  deletion boundary.
- Options flow, OHLC, vendor APIs, sentiment, and user portfolio data remain unavailable
  or out of scope unless separately rights-cleared and implemented.
- Public claims remain evidence organization, provenance, explicit uncertainty, and
  reduced research friction—never alpha, returns, recommendations, or execution.

## Hosted Pro boundary

The local server is intentionally stdio/loopback-only. Hosted Pro would require
authentication, TLS, tenant isolation, per-principal rate limits, request limits,
metering/billing, secret-free observability, backups, incident response, and source rights.
Do not build those controls until paid-intent evidence clears the cost threshold.

Before accepting payment or enabling the exact paid securities-analysis experience,
obtain one scoped legal decision on the product/output/claims and jurisdictions. This is a
paid-launch gate, not discovery or counsel quote-shopping.

## Historical context

- The personal Watchlist and dynamic-universe systems are downstream consumers, not core
  product, GTM, pricing, or release dependencies.
- The former design-partner commercial documents are retained only as non-executable
  history and possible future operational controls.
- Historical verification records remain immutable evidence of the version and workflow
  they tested; they should not be rewritten to simulate the new GTM.

## Open questions

- Will Ryan authorize public MIT distribution after reviewing the exact targets?
- What final signed `.mcpb` and update path will be used?
- What sanitized example best demonstrates provenance without implying alpha?
- What hosted build/operating cost determines the minimum paid-intent threshold?
- What exact output can a future paid Hosted Pro product expose after the scoped legal
  decision?
