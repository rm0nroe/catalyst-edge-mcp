# Catalyst Edge MCP — Go-to-Market Plan

**Status**: Current monetization source of truth.
**Scope**: Commercial positioning and delivery for the implemented Catalyst Edge MCP. This document does not select dynamic-universe research/audit runtimes, models, source permissions, or activation state.

The first commercial product is a customer-installed, local MCP delivered through founder-led, paid design partnerships. It is not a founder-operated monitoring service.

Sell the research outcome, not the protocol:

> Catalyst Edge gives an investment-research agent a compact, source-linked catalyst dossier for one ticker, with explicit confidence limits and data gaps.

Lead with faster evidence review, exact provenance, and reproducible integration. MCP is the delivery mechanism. Do not lead with AI, an “edge score,” predictive alpha, or a managed watchlist.

## Current product state

Implemented now:

- Customer-run local MCP over stdio or loopback streamable HTTP.
- `catalyst_edge_score` for one ticker per invocation.
- Compact catalyst dossier with deterministic, unbacktested scoring, confidence limits, typed missingness, and no investment recommendation.
- `catalyst_edge_claim_sources` for bounded pagination through every source supporting a grouped claim.
- Source-policy configuration and fail-closed behavior for unsupported, unavailable, or rights-gated evidence.

Not implemented or promised by the core product:

- Arbitrary document ingestion or ticker extraction.
- MCP-owned ticker lists, batching, watchlists, universe selection, or scheduling.
- `RESEARCH NOW`, `MONITOR`, or `IGNORE` classification.
- Alert-channel delivery, cloud hosting, customer tenancy, metering, or billing.
- Predictive alpha, calibrated returns, or investment advice.

A customer’s agent may read a document or list, extract tickers, and invoke Catalyst Edge once per ticker. That orchestration remains outside the MCP contract.

## Initial customer

Target:

- Agentic investment-research workflows, analysts/builders, and internal research tools that already have a ticker-selection process.
- Small public-equity teams are an initial ICP hypothesis, not a product boundary.
- Buyer: head of research, research-technology owner, portfolio manager, or technical founder responsible for the workflow.
- User: analyst, research engineer, or agent builder who needs “what changed, what supports it, and what should be checked next?”

Avoid retail traders, options-flow buyers, and anyone expecting proven alpha. Do not qualify customers by watchlist size; qualify them by a real need for source-linked, caveated catalyst evidence inside an agent workflow.

## First offer

Call it the **Catalyst Edge MCP Design Partner** engagement.

- 30-day installation and integration engagement.
- Install a versioned local release into one customer-controlled MCP environment.
- Configure only customer-approved, deployment-specific evidence sources and credentials.
- Integrate the two existing MCP tools into one customer agent or internal research workflow.
- Demonstrate repeated on-demand calls on five customer-selected tickers.
- Review one dossier, paginate one claim’s provenance, and inspect one explicit missing or rejected-data case.
- Deliver a repeatable configuration, onboarding runbook, and defined support boundary.
- No brokerage connection, execution, managed monitoring, alert delivery, arbitrary document input, or predictive-performance claim.

The design-partner fee pays for installation, integration, configuration, validation, and agreed support—not exclusive ownership of the MIT-licensed code. Paid continuation may cover defined support, release updates, or further integration only after the customer validates value.

Pricing remains a hypothesis to validate against the revised scope. Do not carry forward the former `$5,000` pilot or `$3,000/month` managed-service assumptions. Set an upfront paid engagement price only after discovery establishes installation complexity, support load, customer environment, and deployment-specific rights; scope down before discounting.

## Sales motion

1. Build a list of 40–50 named prospects with an existing or planned agentic research workflow.
2. Prioritize warm introductions, research-technology owners, public-equity teams discussing agent adoption, and firms hiring research-automation talent.
3. Qualify the MCP client/environment, current ticker-selection step, evidence-verification pain, source constraints, and owner of installation.
4. Ask for five tickers before the demonstration.
5. During the demonstration:
   - Invoke the single-ticker tool once per selected ticker.
   - Open one compact dossier.
   - Trace one grouped claim through every provenance page.
   - Show a rejected or missing-data case.
   - Compare the on-demand evidence workflow with the prospect’s current manual process.
6. Close directly into a paid installation/integration engagement with explicit acceptance criteria.
7. Use the design-partner review to validate paid continuation for support, updates, or further integration.

A concise outreach message:

> I built a local MCP that turns a ticker into a compact catalyst-research dossier with exact source provenance and explicit missing-data warnings. It uses deterministic, unbacktested scoring and does not make trade recommendations. If you send me five tickers, I can demonstrate the output and how it fits into an existing research agent. I’m opening two paid design-partner engagements for teams that want help installing and integrating it in their own environment.

## What must exist before the first paid engagement

- Deployment-specific commercial-rights review for every enabled source and customer-visible output.
- Versioned customer-installable release and a deliberate distribution channel.
- Product validation CI covering the local MCP contract and release artifact.
- Five-minute MCP-client onboarding target, repeatable customer configuration, installation runbook, and rollback procedure.
- Customer-specific acceptance criteria, support boundary, source-outage behavior, and ownership of the customer-controlled runtime.
- Order form/customer agreement, privacy and retention disclosure, acceptable-use policy, liability boundary, and support terms.
- Counsel review of the actual offer and deployment. A disclaimer alone is insufficient: compensated reports or analyses concerning securities can implicate the Investment Advisers Act, and the publisher exclusion is fact-dependent. [SEC guidance](https://www.sec.gov/divisions/investment/noaction/2015/jonathon-hendricks-012615-202a.htm)

Hosted-service controls such as monitored delivery channels, service backups, incident ownership, tenancy, and service-level operations are not prerequisites for the customer-installed base offer. Add them only if a later hosted or managed product is selected.

## Design-partner scorecard

Measure:

- Time from access to a successful customer-controlled installation.
- Time to first schema-valid invocation.
- Percentage of grouped claims whose provenance the customer can independently verify.
- Analyst-rated dossier usefulness and explicit missingness usefulness.
- Repeat tool usage in the integrated workflow.
- Integration friction, configuration failures, and support load.
- Paid continuation or expansion—the controlling demand signal.

Do not use returns, trading performance, missed monitored events, alert latency, or delivery cost per monitored customer as base-product success metrics.

## 30-day launch target

- Days 1–5: finalize the revised offer, acceptance criteria, pricing test, five-ticker demo, sample dossier, rights matrix, customer agreement, and support boundary.
- Days 6–10: establish the customer-installable release path, validation CI, repeatable configuration, and onboarding runbook; identify 40–50 qualified prospects.
- Days 11–20: run six qualified demonstrations and validate the customer environment, integration owner, willingness to pay, and support expectations.
- Days 21–30: close two paid design partners and complete the first customer-controlled installations/integrations that clear the agreed acceptance criteria.

The objective is paid, working customer integrations—not traffic, waitlist signups, a managed Watchlist, or an unsupported revenue claim.

## Execution pack

The current local execution materials are:

- [`docs/commercial/design-partner-package.md`](docs/commercial/design-partner-package.md): fixed delivery, ownership, support, acceptance, rollback, and continuation boundary.
- [`docs/commercial/release-readiness-plan.md`](docs/commercial/release-readiness-plan.md): versioned artifact, CI, configuration, onboarding, distribution, and rollback gates.
- [`docs/commercial/source-rights-matrix.md`](docs/commercial/source-rights-matrix.md): fail-closed deployment rights decisions and per-customer sign-off record.
- [`docs/commercial/customer-configuration-record.md`](docs/commercial/customer-configuration-record.md): secret-free environment, ownership, retention, source, and rollback record.
- [`docs/commercial/design-partner-pricing-decision.md`](docs/commercial/design-partner-pricing-decision.md): bounded cost, break-even, buyer-evidence, and owner-decision sheet with no preset price.
- [`docs/commercial/design-partner-order-form.md`](docs/commercial/design-partner-order-form.md): non-executable working draft for counsel and customer-specific completion.
- [`docs/demo/five-ticker-demo-runbook.md`](docs/demo/five-ticker-demo-runbook.md): repeated single-ticker calls, dossier review, full claim-source pagination, and missing/rejected-data proof.
- [`docs/demo/customer-installation-runbook.md`](docs/demo/customer-installation-runbook.md): timed artifact verification, clean install, actual client discovery, and state-preserving rollback.

These materials do not authorize a sale or deployment. A paid engagement still requires a completed rights record, counsel-approved terms, a release candidate that passes the release plan, an inserted price, and signatures.

## Distribution path

Customer installation is the initial commercial path, not a later fallback. Establish a versioned package/release channel, customer configuration contract, validation CI, and repeatable MCP-client onboarding before accepting the first engagement.

Validate these later options only when buyer demand requires them:

- Official MCP Registry discovery after a public distribution endpoint exists.
- Authenticated remote MCP.
- Hosted authentication, tenancy, metering, billing, and observability.
- Managed monitoring or alert delivery with the associated operational obligations.

The official registry hosts metadata, not packages or payments, and private-only servers are ineligible. It is a discovery channel after distribution exists—not the GTM itself. [Official MCP Registry documentation](https://modelcontextprotocol.io/registry/about)

## Explicit scope boundary

The personal Watchlist, static or dynamic universe selection, scheduling, `RESEARCH NOW`/`MONITOR`/`IGNORE`, Slack/Teams/private-channel alerts, and OpenClaw orchestration are optional downstream consumers or future add-ons. They are not core Catalyst Edge functionality, base-offer deliverables, pricing inputs, acceptance criteria, launch dependencies, code-readiness claims, or prerequisites for revenue.

Do not buy options data, build multi-tenant SaaS, or implement predictive backtesting before customer evidence shows those capabilities affect willingness to pay. The supporting commercialization audit remains historical input in [the GTM research note](/Users/ryanmonroe/Desktop/dev/catalyst-edge-mcp/thoughts/unknown-ticket/research/2026-08-01-RESEARCH-monetization-readiness.md); its superseded managed-Watchlist recommendation is historical only.
