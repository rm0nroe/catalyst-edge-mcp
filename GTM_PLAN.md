# Catalyst Edge MCP — Go-to-Market Plan

**Status:** Current monetization source of truth.
**Decision date:** 2026-08-03.
**Scope:** Product positioning, audience, distribution, and monetization for the
implemented local Catalyst Edge MCP.

## Decision

Catalyst Edge is a product-led, self-serve research tool for analysts and builders.

**Builders explicitly include retail traders and technically capable individual
investors who assemble their own Claude, Codex, Cursor, or other MCP research
workflows.** The initial audience is defined by behavior and technical comfort—not by
employer, assets under management, or professional title.

The launch motion does not include customer interviews, no-demo problem interviews,
counsel quote requests, prospect lists, boutique-fund targeting, founder-led demos, or
design-partner sales.

## Product promise

> Ask your AI research agent what changed for a ticker, why it matters, what contradicts
> it, and show every source and missing-data warning.

Lead with faster, auditable research. Do not lead with the protocol, an “edge score,” or
institutional procurement language.

Do not promise “make money,” alpha, predictive performance, buy/sell signals, investment
advice, options flow, comprehensive market coverage, or execution. The user's desired
outcome is better investing decisions; the product's supported promise is evidence
organization, provenance, explicit uncertainty, and reduced research friction.

## Current product

Implemented:

- Customer-run local MCP over stdio or loopback streamable HTTP.
- `catalyst_edge_score` for one ticker per invocation.
- Compact catalyst dossier with deterministic, unbacktested scoring, confidence limits,
  contradictions, typed missingness, and no investment recommendation.
- `catalyst_edge_claim_sources` for bounded pagination through every source supporting a
  grouped claim.
- Source-policy configuration and fail-closed behavior for unsupported, unavailable, or
  rights-gated evidence.
- Reproducible local `0.1.1` wheel and source distribution with clean-install, two-tool,
  onboarding, rollback, and package-hygiene evidence.

Not implemented or promised:

- A conventional retail UI.
- MCP-owned ticker lists, batching, watchlists, universe selection, or scheduling.
- `RESEARCH NOW`, `MONITOR`, or `IGNORE` classification.
- Alerts, brokerage integration, trade execution, cloud hosting, customer tenancy,
  metering, or billing.
- Predictive alpha, calibrated returns, or investment advice.

The absence of a UI means the initial retail audience is technical and AI-native. A
user's agent may extract tickers from another source and invoke Catalyst Edge once per
ticker; that orchestration remains outside the MCP contract.

## Launch offer

### Catalyst Edge Local Beta

Release the complete local product free and self-serve:

- public GitHub repository;
- PyPI wheel and source distribution;
- signed Claude Desktop `.mcpb` for one-click installation;
- one copy-paste Codex/PyPI installation path; and
- MCP Registry listing after the permanent public artifacts are verified.

No call, interview, demonstration, custom installation, application, or customer
qualification is required.

Public MIT distribution requires Ryan's explicit authorization. The repository, PyPI,
MCP Registry, and package artifacts must not be published merely because this plan names
them.

### Hosted Pro paid-intent test

Place one future paid option beside the free install:

> Hosted Pro — $29/month, coming soon.

The signup asks for email, MCP client, and whether the user would definitely pay $29/month
for zero-install hosted access and managed updates. It uses double opt-in, deduplication, the
exact offer/version shown before response, and—when available—a privacy-preserving link to
successful Local Beta activation. Raw page views, downloads, unverified emails, “maybe,”
staff, bots, QA, and duplicate responses do not count as activation-linked paid intent. The
price remains a hypothesis, not established willingness to pay.

The current research-backed decision gates are:

1. **350 recent activation-linked, verified, price-aware signups:** Ryan may separately
   authorize at most a 56-hour disposable OAuth/client compatibility spike. This does not
   authorize a hosted product build.
2. **1,350 recent activation-linked, verified, price-aware signups:** Ryan may separately
   authorize one scoped legal/source/payment-provider review. This does not authorize
   payment, customer delivery, or the full build.
3. **11,100 recent activation-linked, verified, price-aware signups:** the complete Hosted
   Pro build may be reconsidered and re-costed. This is not automatic build authority.

“Recent” means within 180 days or voluntarily reconfirmed through the current self-serve
offer. Separately, the raw verified “definitely yes” intent rate must maintain a one-sided
95% Wilson lower bound of at least 3% among unique qualified visitors shown the full offer.
The activation-link yield is reported separately; no activation floor is invented.

The first two thresholds are heuristic risk-budget caps, not ROI claims. The full-build gate
uses a six-month conversion lag, 10% economic reserve, and a one-sided conversion allowance
on the base 5% proxy. Recompute from actual workload, conversion, retention, support, legal,
and provider data before every authorized expense. The supporting calculations and source
limits are in
[`thoughts/unknown-ticket/research/2026-08-03-RESEARCH-hosted-pro-architecture.md`](thoughts/unknown-ticket/research/2026-08-03-RESEARCH-hosted-pro-architecture.md).

Do not build authentication, billing, tenancy, or hosted operations before the safeguarded
full-build gate clears and Ryan explicitly authorizes the exact implementation.

Counsel quote-shopping is not a launch action. Before accepting payment or enabling a
paid securities-analysis experience, obtain one scoped legal decision on the exact paid
output, marketing claims, and distribution model. That is a paid-launch gate, not market
discovery.

## Release gate

Complete these steps before requesting public-release authorization:

1. Make the public default source set conservative and rights-cleared. Require a valid
   SEC identity, disable conditional or unclear sources by default, keep GDELT disabled
   until its required attribution/linking is implemented and tested, and align the rights
   record with runtime configuration.
2. Produce one clean reviewed `0.1.1` commit and tag, run the existing CI on GitHub, and
   verify the released wheel, source distribution, hashes, rollback, and exact two-tool
   discovery.
3. Build and test one signed Claude `.mcpb` plus the copy-paste Codex/PyPI install path.
4. Prepare one public page and one real, sanitized dossier/provenance example.
5. Present the exact repository, package, Registry, and landing-page targets to Ryan for
   explicit publication authorization.

## One launch surface

The page contains:

- the product promise above;
- a 60–90 second real dossier/provenance example;
- `Install free` for Claude and Codex;
- the `Hosted Pro — $29/month, coming soon` paid-intent signup;
- explicit unbacktested, non-advisory, and bounded-coverage limitations; and
- documentation, source policy, security notes, and issue reporting.

Use public release content and package discovery to reach the audience. Measure package
downloads, successful-install reports, support burden, raw verified Hosted Pro intent, the
activation-linked subset, unique qualified offer exposures, and acquisition source. Read the
Wilson bound after at least 250 qualified exposures and four weeks; 12 qualifying raw intent
responses at `n=250` produce an approximately 3.02% one-sided lower bound. These are
product-led signals; no interviews, calls, prospect spreadsheet, or outbound cohort is
needed.

## Decision after launch

- **Paid intent clears 350:** re-cost and request separate authorization only for the capped
  compatibility spike.
- **Paid intent clears 1,350:** re-cost and request separate authorization only for the
  scoped legal/source/payment-provider decision.
- **Paid intent clears 11,100:** re-estimate the complete economics using observed cohorts;
  consider a remote MCP build only if every legal, rights, payment, OAuth, tenant, billing,
  transport, operations, recovery, and explicit-authorization gate still passes.
- **Paid intent does not appear:** keep Local Beta free, improve or stop based on actual
  adoption and support evidence, and do not manufacture revenue through consulting or
  founder-led services.

## Explicit exclusions

Do not:

- run eight no-demo problem interviews or any substitute interview cohort;
- request two or three counsel quotes or conduct counsel quote-shopping;
- target small funds or boutique firms as the default audience;
- assemble named-prospect or warm-introduction lists;
- sell custom demonstrations, design partnerships, or bespoke integrations;
- publish a proof-only repository instead of the actual product;
- revive the historical `$199 for 90 days`, `$49/month`, or `$399/year` paid local beta;
- build hosted infrastructure before the safeguarded 11,100-signup gate, re-costing, and
  explicit implementation authorization;
- build a mass-market UI, alerts, brokerage integration, institutional administration,
  licensed options data, or predictive backtesting before the product-led path requires
  it; or
- market alpha, investment performance, trade signals, recommendations, or execution.

## Relationship to historical commercial documents

The documents under `docs/commercial/` that describe a customer-specific design-partner
engagement are superseded and non-executable. Their release verification, source-rights,
configuration, rollback, and security controls may be reused where they apply to a public
local release. Their prospecting, discovery, customer acceptance, pricing, order-form,
custom installation, and founder-support assumptions are not part of the current plan.

The PRD and TDD remain the product boundary. The personal Watchlist, dynamic universe,
OpenClaw orchestration, and scheduled scanning remain separate downstream systems and are
not GTM prerequisites.
