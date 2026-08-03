---
date: 2026-08-03T15:16:49-04:00
researcher: ryanmonroe
git_commit: c94f3731584679cfbc714ddcd4260526d2f9a821
branch: main
repository: catalyst-edge-mcp
topic: "Conditional Hosted Pro architecture after the Local Beta paid-intent gate"
tags: [research, hosted-pro, mcp, oauth, postgres, billing, observability, unit-economics]
status: complete
last_updated: 2026-08-03
last_updated_by: ryanmonroe
last_updated_note: "Added follow-up research for the paid-intent economics and staged decision gate"
---

# Research: Conditional Hosted Pro architecture

**Date**: 2026-08-03T15:16:49-04:00
**Researcher**: ryanmonroe
**Git Commit**: `c94f3731584679cfbc714ddcd4260526d2f9a821`
**Branch**: `main`
**Repository**: `catalyst-edge-mcp`

## Research question

If the self-serve Local Beta produces enough `Hosted Pro — $29/month` paid intent,
which remote MCP hosting, database, OAuth, billing, observability, deployment, and
operations architecture should Catalyst Edge adopt, under what economics and gates,
and what must remain separate from the local product?

## Decision summary

The provisional `Render + Render Postgres + WorkOS AuthKit + Stripe` hypothesis
**survives, with material conditions**:

- **Render survives and becomes the selected compute/database candidate.** It is the
  best match for the existing Python/Docker process, long Streamable HTTP requests,
  same-platform private networking, active health replacement, deploy rollback, and
  singleton cron behavior. The current selected-topology cash baseline is about
  **$17/month**: Render's
  July 2026 example prices a Starter web service plus Basic-256 Postgres at about $13,
  and the four specified cron services each have a $1 monthly minimum.
- **WorkOS AuthKit survives as the conditional OAuth choice.** It documents the fullest
  current MCP 2025-11-25 feature match: OAuth metadata, PKCE, DCR, CIMD, RFC 8707
  resource indicators, and resource-bound token audience. Its free tier covers the
  paid-intent scale. A real Claude and Codex round trip is still mandatory.
- **Stripe survives only as the first provider to seek approval from.** Its Checkout,
  Billing, Entitlements, webhook, and idempotency surfaces fit. Stripe's restricted-
  business policy can require additional review for financial services. Catalyst's exact
  non-advisory research-software classification is not proven. No payment account or
  checkout should be opened before the scoped product/legal decision and provider
  eligibility confirmation.
- **Sentry is optional, not foundational.** Start with secret-free JSON application
  logs, Render metrics/logs, one external uptime check, database-backed audit/usage
  records, and a tested restore runbook. The free Sentry Developer plan is useful for
  errors/traces but must be configured to exclude MCP arguments, outputs, tokens, email,
  and ticker history.

This is a conditional architecture recommendation, not build or deployment authority.
`GTM_PLAN.md` still requires a paid-intent threshold derived from cost and a scoped legal
decision before payment or paid securities-analysis delivery.

## Fact, inference, recommendation, and unknown convention

- **Fact** means directly observed repository behavior, a current official vendor
  statement, or a reproduced local test.
- **Inference** means a conclusion drawn from those facts for Catalyst's workload.
- **Recommendation** means the conditional design to adopt if all acceptance gates pass.
- **Unknown** means a load-bearing item that remains unproved and must not be presented
  as current capability.

## Repository constraints

### Current authority

**Fact.** `GTM_PLAN.md` makes the free self-serve Local Beta current, describes Hosted
Pro as a $29 price hypothesis, prohibits building auth/billing/tenancy/hosting before
paid intent, and requires one scoped legal decision before accepting payment or enabling
the exact paid securities-analysis experience
([GTM_PLAN.md:64-98](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/GTM_PLAN.md#L64-L98)).
It excludes interviews, prospecting, founder demos, design-partner sales, alpha claims,
recommendations, and execution
([GTM_PLAN.md:127-168](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/GTM_PLAN.md#L127-L168)).

**Recommendation.** Keep the landing-page paid-intent form limited to email, MCP client,
and the explicit $29 willingness question. Do not substitute outreach or a sales cohort
for product-led evidence.

### Current runtime and storage

**Fact.** The package is Python 3.10+, Pydantic v2, and official MCP Python SDK v1;
FastMCP serves stdio and stateless Streamable HTTP
([TDD.md:23-50](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/TDD.md#L23-L50)).
`build_service()` is the sole production composition root, while enabled GDELT and
Bluesky lifecycle loops start inside the server lifespan
([server.py:31-98](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/server.py#L31-L98),
[server.py:103-124](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/server.py#L103-L124)).

**Fact.** Local HTTP is intentionally restricted to loopback by `Settings.from_env()`
([settings.py:118-120](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/settings.py#L118-L120)).
The TDD requires OAuth/equivalent auth, TLS, per-principal/request limits, health/readiness,
structured secret-free logs, provider circuit-breaker metrics, and network controls before
non-loopback hosting
([TDD.md:590-602](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/TDD.md#L590-L602)).

**Fact.** `EvidenceStore` is a synchronous concrete SQLite implementation. It enables
WAL and foreign keys, creates schema in-process, depends on `sqlite3.Row`, `?`
placeholders, `INSERT OR IGNORE`, and a process-local `RLock`
([evidence_store.py:1-13](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/evidence_store.py#L1-L13),
[evidence_store.py:102-290](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/evidence_store.py#L102-L290)).
Claim/source relations and entity audits are append-only/idempotent and must retain their
immutable IDs and unique constraints in a hosted port
([TDD.md:367-377](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/TDD.md#L367-L377)).

**Inference.** A shared hosted process cannot use this SQLite file safely as its durable
multi-instance system of record. A PostgreSQL port is required. It should retain explicit
SQL and introduce only the narrow storage boundary necessary to inject a PostgreSQL
implementation; an ORM rewrite is not justified.

### Current source and output boundary

**Fact.** SEC is the public baseline under fair-access controls. Issuer feeds, GDELT,
Bluesky, vendor APIs, options, OHLC, and user data are disabled, conditional, prohibited,
or outside scope under the current rights matrix
([docs/commercial/source-rights-matrix.md:7-41](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/docs/commercial/source-rights-matrix.md#L7-L41)).
Public reachability or credentials do not establish paid reuse/output rights. The paid
boundary is expressly unresolved
([docs/commercial/source-rights-matrix.md:73-75](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/docs/commercial/source-rights-matrix.md#L73-L75)).

**Recommendation.** Hosted Pro v1 remains SEC-only unless each additional centralized
source receives a source-specific paid-output decision. Use one monitored SEC identity,
official hosts, a global request limiter below the SEC ceiling, bounded derived facts,
official links, and no indiscriminate filing-body retention.

## Comparable paid MCP products

### Observed patterns

| Product | Current public pattern | What it establishes |
| --- | --- | --- |
| Financial Datasets | Hosted MCP; OAuth 2.1 for interactive clients, API key for programmatic clients; $20/1,000 credits or $200/month for 100,000 requests | MCP access is an authenticated surface on top of a vendor-owned account, entitlement, and request-credit system. [Pricing](https://www.financial-datasets.ai/pricing), [MCP docs](https://docs.financialdatasets.ai/mcp-server) |
| Intrinio | Hosted HTTP MCP; OAuth/API key; access included with subscriptions and the subscription tier controls datasets | MCP is a delivery channel for an existing licensed-data product, not a separate directory-billed product. [MCP](https://intrinio.com/mcp) |
| NexusForge EU Finance | Free 100 calls/day; Pro €29/month for 5,000/day with an API key; Stripe checkout; Scale €199/month with 99.9% SLA | $29 is present at the low end of paid financial MCP, paired with explicit call limits and support. [Pricing](https://nexusforge.tools/en/pricing/) |
| Elite Stock Research | Remote MCP included with a $19.99/month Pro product; hashed, revocable API keys | A small financial MCP can sell zero-install access through vendor-owned credentials. [MCP](https://www.elitestockresearch.com/mcp) |
| Daloopa | Read-only remote financial MCP secured with OAuth; public price not shown | Established data vendors also use OAuth and read-only tools; lack of public price prevents direct economics comparison. [MCP](https://www.daloopa.com/products/mcp) |

**Fact.** These products authenticate and meter access themselves. Claude, Codex, MCP
directories, and registries provide connection/discovery surfaces; they do not collect
the vendor's subscription revenue.

**Inference.** Catalyst should meter successful tool invocations against its own
principal/entitlement record. Do not depend on a directory for billing, identity, tenant
state, or support. A flat $29 subscription with a documented fair-use/request ceiling is
more consistent with current small MCP products than per-tool microbilling.

**Unknown.** Comparable public prices do not prove willingness to pay for Catalyst's
narrow evidence/provenance product, especially without licensed market data.

## Compute comparison

Scores are Catalyst-weighted inference, not vendor facts: HTTP/streaming 20,
Python/Docker 10, warm lifecycle 10, singleton jobs 15, network/secrets 10,
health/rollback/logs 15, regions/SLA 10, and cost/operations 10.

| Platform | Score | Current evidence and Catalyst conclusion |
| --- | ---: | --- |
| **Render** | **91** | Native Python/Docker, paid always-on service, responses up to 100 minutes, same-region private network, active health replacement, zero-downtime deploys, rollback, and cron max-one-run semantics. Current small-business example: Starter web + Basic-256 Postgres about $13/month; cron minimum $1/month. **Select.** [Web](https://render.com/docs/web-services), [health](https://render.com/docs/health-checks), [cron](https://render.com/docs/cronjobs), [rollback](https://render.com/docs/rollbacks), [price example](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses) |
| **Google Cloud Run** | **90** | Arbitrary containers, streaming, scale-to-zero/minimum instances, request timeout up to 3,600 seconds, Jobs, VPC, Secret Manager, probes, revisions, traffic rollback, and 99.95% SLA. Scheduler is at-least-once and requires a DB lease. **Lowest-cash elastic alternative.** [Overview](https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run), [timeouts](https://docs.cloud.google.com/run/docs/configuring/request-timeout), [pricing](https://cloud.google.com/run/pricing) |
| Azure Container Apps | 84 | Arbitrary containers, scale-to-zero, jobs, VNet, Key Vault, probes, revisions and 99.95% SLA. Effective continuously streamed connection duration still requires proof. **Credible, not preferred.** [Overview](https://learn.microsoft.com/en-us/azure/container-apps/overview), [jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs), [pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/) |
| Railway | 80 | Docker, SSE, 15-minute HTTP maximum, overlap-skipping cron, private network, variables, health checks, four regions; Pro $20 included usage. Runtime health and newly documented DB recovery require stronger proof. **Viable but weaker than Render.** [Limits](https://docs.railway.com/networking/public-networking/specs-and-limits), [cron](https://docs.railway.com/guides/cron-workers-queues), [pricing](https://docs.railway.com/pricing) |
| **AWS ECS Fargate** | **80** | OCI containers, no task-duration ceiling, VPC/secrets, ALB timeouts, CloudWatch, deployment circuit breaker, multi-AZ ECS SLA. EventBridge is not exactly once and the topology adds ALB/NAT/IP/log costs. **Maximum-control option, premature now.** [Services](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_services.html), [Fargate price](https://aws.amazon.com/fargate/pricing/), [SLA](https://aws.amazon.com/ecs/sla/) |
| Fly.io Machines | 75 | Cheap always-on/auto-start Machines and many regions, but health checks do not restart failed Machines and scheduled starts are intentionally fuzzy. **Reject for lowest-ops.** [Health](https://fly.io/docs/reference/health-checks/), [schedule](https://fly.io/docs/machines/flyctl/fly-machine-run/), [pricing](https://fly.io/docs/about/pricing/) |
| Vercel | 65 | OCI/Python/FastAPI streaming and 30-minute Pro/Enterprise duration are newly plausible, but cron can duplicate/overlap and private VPC is Enterprise. **Rule out for v1 rather than assuming incompatibility.** [FastAPI](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel), [duration](https://vercel.com/changelog/vercel-functions-can-now-run-up-to-30-minutes), [cron](https://vercel.com/docs/cron-jobs/manage-cron-jobs) |
| Cloudflare Workers/Containers | 61 | Workers stream while connected and are inexpensive; Containers sleep, cold-start, and lack general built-in stateless autoscaling. Cron is not exactly once and Python Workers remain beta. **Rule out as a lift-and-shift; it implies a Worker/Durable Object replatform.** [Limits](https://developers.cloudflare.com/workers/platform/limits/), [Containers](https://developers.cloudflare.com/containers/), [pricing](https://developers.cloudflare.com/workers/platform/pricing/) |
| AWS App Runner | 30 | 120-second total request timeout, no native scheduled jobs, and closed to new customers. **Reject.** [Limits/availability](https://docs.aws.amazon.com/apprunner/latest/dg/apprunner-availability-change.html) |

## Database comparison

| Database | Current evidence | Catalyst conclusion |
| --- | --- | --- |
| **Render Postgres** | Standard PostgreSQL; paid integrated transaction-mode PgBouncer; private same-region URL; AES-256 at rest; paid PITR 3 days on Hobby/7 on Pro; logical exports retained 7 days. [Pooling](https://render.com/docs/postgresql-connection-pooling), [connections](https://render.com/docs/postgresql-creating-connecting), [backups](https://render.com/docs/postgresql-backups) | **Select with Render.** Lowest integration/operations surface. Prove pool restart, migration rollback, PITR restore, and cutover. |
| **Neon Launch** | Usage-priced Postgres, scale-to-zero, pooling, 7-day restore; typical intermittent 1GB example $15/month. Private networking and SLA require Scale. [Pricing](https://neon.com/pricing), [pooling](https://neon.com/docs/connect/connection-pooling), [security](https://neon.com/docs/security/security-overview) | **Select only with Cloud Run alternative.** Independent and elastic, but public TLS below Scale and possible double cold start. |
| Supabase Postgres | Pro $25/month with Micro/8GB, daily 7-day backups, pooled connections; PITR starts around $100/month and requires larger compute. [Pricing](https://supabase.com/pricing), [connections](https://supabase.com/docs/guides/database/connecting-to-postgres), [backups](https://supabase.com/docs/guides/platform/backups) | Strong platform, but unnecessary breadth and cost if Auth is not selected. |
| Railway Postgres | Standard image plus volume, HA/pool templates and newly documented WAL/PITR workflow. [Postgres](https://docs.railway.com/databases/postgresql), [PITR](https://docs.railway.com/volumes/point-in-time-recovery) | More self-operated than managed Postgres; recovery maturity requires a real drill. |
| RDS / Cloud SQL / Azure Flexible Server | Mature standard PostgreSQL, private networks, encryption, backup/PITR, and optional multi-zone HA. [RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html), [Cloud SQL backup](https://docs.cloud.google.com/sql/docs/postgres/backup-recovery/backups), [Azure price](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/) | Best control/maturity, materially more configuration and cash. Use only in architecture C. |
| Turso/libSQL | $5.99 Developer, SQLite import/export, 10-day PITR, Python clients; remote PRAGMA/transaction differences and single-primary writes. [Pricing](https://turso.tech/pricing), [limitations](https://docs.turso.tech/cloud/limitations), [PITR](https://docs.turso.tech/features/point-in-time-recovery) | Not actually zero-change and poorly matched to shared evidence plus entitlement/audit state. Do not select. |
| LiteFS | Pre-1.0, unsupported by Fly, async single writer, with explicit stale-election/data-loss warning when combined with autostop. [Status](https://fly.io/docs/litefs/), [replication](https://fly.io/docs/litefs/how-it-works/) | **Reject.** Lower code churn does not outweigh hosted data-loss/operations risk. |

## OAuth and MCP-client compatibility

### Protocol baseline

**Fact.** MCP 2025-11-25 remote authorization uses RFC 9728 protected-resource
metadata, OAuth/OIDC authorization-server discovery, PKCE, RFC 8707 resource indicators,
and token-audience validation. Token passthrough is prohibited. Pre-registration or CIMD
is preferred; DCR is an optional fallback
([authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization),
[changelog](https://modelcontextprotocol.io/specification/2025-11-25/changelog)).

**Fact.** Claude requires an unauthenticated `401` challenge with a
`resource_metadata` link. The protected `resource` must exactly match the configured MCP
URL, including `/mcp`. Claude uses PKCE S256, uses the first listed authorization server,
supports CIMD when advertised, and otherwise falls back to DCR. Claude.ai uses a fixed
callback; Claude Code uses loopback callbacks
([authentication](https://claude.com/docs/connectors/building/authentication),
[testing](https://claude.com/docs/connectors/building/testing)).

**Fact.** Codex documents Streamable HTTP MCP with bearer and OAuth authentication,
`codex mcp login`, OAuth scopes, and an RFC 8707 `oauth_resource` setting. It does not
promise provider-specific CIMD behavior
([Codex MCP](https://developers.openai.com/codex/mcp),
[configuration](https://developers.openai.com/codex/config-reference)).

### Provider matrix

| Provider | Current documented fit | Decision |
| --- | --- | --- |
| **WorkOS AuthKit** | MCP guide documents metadata, PKCE, DCR, CIMD, RFC 8707 resource indicators, and resource-bound `aud`; free through 1M MAU, optional custom domain $99/month. [MCP](https://workos.com/docs/authkit/mcp), [pricing](https://workos.com/pricing) | **Conditional selection.** Use the official `mcp` SDK `TokenVerifier`, not examples for the separate `fastmcp` package. |
| Auth0 | MCP auth, DCR, CIMD, PKCE, rotation, and RFC 8707 with the compatibility profile; free through 25K MAU. [MCP](https://auth0.com/ai/docs/mcp/intro/overview), [resource profile](https://auth0.com/ai/docs/mcp/guides/resource-param-compatibility-profile), [pricing](https://auth0.com/pricing) | Strong fallback; more configuration, and CIMD clients currently do not support Auth0 Organizations. |
| Stytch | DCR, beta CIMD, scopes, revocation, MCP docs; resource-to-audience behavior is not explicit. [MCP](https://stytch.com/docs/connected-apps/guides/mcp-auth-overview), [pricing](https://stytch.com/pricing) | Conditional, with more app-owned authorization UI. |
| Clerk | DCR, PKCE, verification, revocation and an Express MCP guide; no documented CIMD or RFC 8707 resource binding. Free through 50K MRU; Pro $20/month annually. [MCP](https://clerk.com/docs/expressjs/guides/ai/mcp/build-mcp-server), [pricing](https://clerk.com/pricing) | Incomplete for the preferred path; testable through DCR fallback. |
| Supabase Auth | Beta OAuth server with PKCE, DCR, refresh, discovery, JWT/JWKS and consent; no custom scopes, documented CIMD, or dynamic RFC 8707 binding. Pro $25/month. [MCP](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication), [pricing](https://supabase.com/pricing) | Do not select yet. |
| Self-hosted | Can implement every requirement | Reject at $29: Catalyst would own consent, registration, key rotation, recovery, abuse, audit, refresh/revocation, and incident response. |

### Reproduced official-SDK boundary spike

**Fact.** With installed official `mcp==1.28.1`, an in-process Starlette test using a
fake token verifier produced:

```text
GET /.well-known/oauth-protected-resource/mcp -> 200
POST /mcp without bearer -> 401 with resource_metadata for the exact /mcp resource
POST /mcp with a locally verified catalyst:read token -> 200
negotiated protocol -> 2025-11-25; server SDK version -> 1.28.1
```

The metadata contained the exact resource, the authorization server, scope
`catalyst:read`, and bearer header method. This proves the official SDK's resource-server
boundary, RFC 9728 route/challenge, verifier hook, scope check, and authenticated
Streamable HTTP initialization. It does not exercise DNS, TLS, WorkOS, browser consent,
DCR/CIMD, PKCE exchange, refresh/revocation, Claude, or Codex.

**Unknown / blocking proof.** Create a disposable WorkOS staging configuration and run
one Claude custom-connector OAuth flow plus one Codex OAuth login only after explicit
authority to create that external state.

## Anthropic directory boundary

**Fact.** Submission requires a Team/Enterprise organization and directory authority,
HTTPS remote MCP over Streamable HTTP or SSE, OAuth for authenticated services, accurate
tool annotations, separation of read/write capabilities, public documentation,
privacy/support information, populated test credentials, examples, and full-tool testing.
Acceptance and verification are discretionary. Money, crypto, or asset-transfer tools are
prohibited; financial research tools are not categorically prohibited
([submission](https://claude.com/docs/connectors/building/submission),
[review criteria](https://claude.com/docs/connectors/building/review-criteria),
[directory policy](https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy)).

**Inference.** Catalyst is plausibly a read-only research connector because it has no
transfer, execution, or personalized portfolio path. Consumer-facing finance is a
high-impact domain under Anthropic policy; disclosure and qualified-human-review rules
may apply. Whether Catalyst's deterministic score is treated as investment advice is
unresolved
([Anthropic Usage Policy](https://www.anthropic.com/legal/aup)).

**Recommendation.** Directory submission is a post-production proof and distribution
step. It is not an architecture, billing, or paid-launch prerequisite. Do not claim
eligibility or verification before Anthropic accepts the exact connector.

## Billing comparison

| Provider | Current price and mechanics | Product-policy fit | Decision |
| --- | --- | --- | --- |
| **Stripe** | US cards 2.9% + $0.30; Billing pay-as-you-go 0.7% of billing volume; Tax Basic no-code 0.5% per registered transaction. Checkout, customer portal, subscriptions, Entitlements, signed webhooks. [Billing pricing](https://stripe.com/billing/pricing), [Tax](https://stripe.com/pricing), [Entitlements](https://docs.stripe.com/billing/entitlements) | Financial services can require additional diligence/approval. Catalyst's non-advisory software classification is unknown. [Restricted businesses](https://stripe.com/legal/restricted-businesses) | **First conditional choice.** Seek written eligibility for the exact product after the legal output decision. |
| Paddle | Merchant of record, tax/compliance/fraud/chargeback protection, subscriptions and customer support included at 5% + $0.50. [Pricing](https://www.paddle.com/pricing) | AUP prohibits regulated financial products and investment/financial advice, trading signals and strategies. Catalyst avoids those claims, but classification remains risky. [AUP](https://www.paddle.com/help/start/intro-to-paddle/what-am-i-not-allowed-to-sell-on-paddle) | Do not select without explicit written acceptance; current wording is the least favorable. |
| Lemon Squeezy | Merchant of record, tax filing, subscriptions, payment recovery and billing support at 5% + $0.50, with possible edge-case fees. [Pricing](https://www.lemonsqueezy.com/pricing) | Reviews every store; prohibits regulated services and anything restricted by payment processors. [Products](https://docs.lemonsqueezy.com/help/getting-started/prohibited-products), [activation](https://docs.lemonsqueezy.com/help/getting-started/activate-your-store) | Credible MoR fallback if the exact store is approved; not pre-approved by public docs. |

**Fact.** Stripe and Paddle explicitly require idempotent webhook consumers because
events can duplicate and arrive out of order
([Stripe webhooks](https://docs.stripe.com/webhooks),
[Paddle webhooks](https://developer.paddle.com/webhooks/about/how-webhooks-work/)).

**Recommendation.** The internal entitlement record is authoritative for request-time
access. Billing webhooks update it through a transaction that first inserts a unique
provider event ID. Duplicate events become successful no-ops. Out-of-order events are
resolved from provider object state/timestamp, not delivery time. Never perform MCP
authorization by calling the billing provider synchronously.

## Hosted data model

### Shared public evidence

Keep one shared set of public/source-policy records: source observations, canonical events,
event/source and claim/source relations, entity-match audit, collector state, and source
policy. Preserve current immutable `clm_` and `src_` derivation, unique fingerprints,
correction lineage, and append-only audits. Shared evidence has no principal or tenant ID.

### Principal-specific control state

Use a separate PostgreSQL schema for:

- `principal`: internal UUID, authorization-server issuer/subject, state, created/deleted
  times; unique `(issuer, subject)`;
- `billing_customer` and `subscription`: provider IDs, state, current period, and last
  provider event time; no card data;
- `entitlement`: principal, capability (`catalyst:read`), state, and valid times;
- `rate_limit` and `rate_window`: separate per-principal/capability minute and monthly limit
  definitions plus atomic window counters;
- `usage_event`: internal operation UUID, optional principal-scoped UUID operation key,
  bounded/digested protocol request correlation, request HMAC and key version, fenced
  lease/attempt state, billable units, result class, duration, response digest, and times;
  no prompt, raw tool arguments, dossier, ticker, protocol ID, or response body;
- `billing_event`: unique provider event ID, type, object ID, occurred/processed times,
  payload hash and status; do not retain full raw payload indefinitely; and
- `security_audit`: login/consent/token/admin/delete events with pseudonymous principal,
  internal operation ID and outcome; no client correlation value, tokens, or MCP content.

Apply PostgreSQL row-level security to every principal-scoped table. In each transaction,
set the authenticated principal ID and test cross-principal denial. The runtime role must
not own or bypass RLS. Shared evidence is read-only to the MCP runtime except through
explicit collector/migration roles.

Do not use an MCP/JSON-RPC request ID as a persistent idempotency key: the protocol allows
string or numeric correlation IDs and reuse across connections. A Catalyst operation key is
an explicit, separate, principal-scoped option. Without one, the server assigns an internal
operation UUID and promises no cross-call retry idempotence. HMAC key IDs are stored, prior
verification keys overlap through the maximum live-operation window, and retirement is
blocked while referenced by a live row.

The pre-RLS identity bootstrap is a fixed-path, non-login-owned function that can only resolve
an exact trusted issuer/subject or converge concurrent first logins on one new `pending`
principal. It cannot activate or grant access; pending users receive the self-serve account
URL, and only billing reconciliation activates entitlement. Lease takeover increments a
generation fence: heartbeat, completion, metering and response emission must match both
owner and generation. Operation keys must be canonical UUIDs; protocol IDs are bounded,
type/value-canonicalized, digested, and never stored or logged raw.

### Explicitly excluded

Hosted Pro v1 stores no holdings, portfolios, prompts, brokerage data, personalized
watchlists, MCP-owned ticker lists, alerts, or execution state. It does not retain a
principal's query ticker history. Local Beta SQLite remains customer-owned and separate;
there is **no default import or synchronization path**.

## PostgreSQL port boundary

**Recommendation.** Use numbered, immutable SQL migrations plus `psycopg` and its pool.
Preserve the existing explicit SQL and method behavior. Avoid an ORM and a general data
platform.

Required dialect/operations changes include:

- move DDL out of `EvidenceStore._connect()` into a pre-deploy migration command;
- replace `sqlite3.Row`, `?`, `INSERT OR IGNORE`, integer booleans, and implicit row IDs
  with PostgreSQL row factories, `%s`, `ON CONFLICT DO NOTHING`, booleans, identity/
  `bigserial`, and `RETURNING`;
- use `TIMESTAMPTZ` and `JSONB` where the current schema stores timestamps/JSON text;
- inject the store and pool from the composition root instead of opening a path inside
  adapters/tools;
- run collectors as a separate cron process; do not start one lifecycle loop per web
  replica;
- use a PostgreSQL advisory lock/lease in every scheduled job even though Render suppresses
  overlap; and
- retain a state-preserving DB rollback: code rollback never reverses an additive migration,
  and destructive migrations require an expand/migrate/contract sequence.

## Observability, SLO, backup, deletion, and support

### Minimum launch controls

- Secret-free JSON logs: timestamp, environment, release SHA, request ID, pseudonymous
  principal ID, tool, status, duration, billed units, provider status/error class. No
  token, email, ticker, arguments, output, headers, query strings, or raw provider body.
- Render service metrics and health checks for `/health/live` and `/health/ready`.
  Readiness checks process startup, migrations, and a bounded DB query; they do not call
  external evidence providers.
- One external HTTPS uptime check. UptimeRobot's current free plan permits commercial use,
  50 monitors and five-minute checks
  ([plan](https://uptimerobot.com/pricing/)).
- Sentry Developer only if scrubber tests pass; current free plan includes one user,
  5,000 errors, 5GB logs, 5M spans, and one uptime/cron monitor
  ([pricing](https://sentry.io/pricing/)).
- Provider circuit metrics: requests, successes, typed failures, `429`, timeouts, breaker
  state, and last success age by provider—never response bodies.
- Database-backed audit, usage, billing idempotency, rate-limit, and deletion receipts.

### Initial objectives, not customer SLA

- Availability SLO: 99.5% monthly for the MCP ingress, excluding declared maintenance and
  upstream evidence-provider outage; publish no SLA until measured and contract-backed.
- Latency SLO: 95% of completed score calls under 10 seconds; all provider work remains
  bounded by current timeouts and returns typed partial results.
- RPO: 15 minutes, consistent with continuous paid Postgres backup and Render's inability
  to restore within the most recent ten minutes.
- RTO: four hours for database restore, secret rebind, service cutover, and readback.
- Restore proof before payment, then quarterly: restore PITR to a new database, reconcile
  row/constraint/claim counts, run read-only tool checks, and destroy the recovery instance
  only after evidence is retained.

### Retention and deletion proposal

- Request application logs: 14 days; Sentry events/traces: at most 30 days.
- Usage and security audit: 90 days online, unless a longer statutory/security requirement
  is documented.
- Billing IDs and accounting records: retain only as required for finance/tax/disputes;
  payment provider retains card data.
- Principal deletion request: revoke auth sessions, disable entitlement immediately,
  delete identity linkage and online audit/usage within 30 days, and retain only records
  required by law with a deletion receipt.
- Shared SEC-derived evidence is not principal data and is governed by source policy, not
  account deletion. Any source correction/takedown follows source-specific policy.

These periods are product recommendations, not legal conclusions. The privacy/legal review
must confirm them before launch.

## Unit economics at $29

### Known transaction arithmetic

At current US list prices:

```text
Stripe Payments + Billing + Tax Basic
  fee = 29*2.9% + $0.30 + 29*0.7% + 29*0.5% = $1.489
  net before variable service cost = $27.511

Paddle or Lemon Squeezy list fee
  fee = 29*5% + $0.50 = $1.95
  net before variable service cost = $27.05
```

This excludes international-card/currency fees, refunds, disputes, credits, tax
registrations, support, incidents, and legal/engineering labor.

For fixed monthly cash cost `F`, variable cost per active subscriber `V`, transaction
fees `P`, and one-time build/legal cost basis `B`:

```text
contribution C = 29 - P - V
cash break-even subscribers = ceil(F / C)
3x cash safety subscribers = ceil(3F / C)
12-month build recovery subscribers = ceil((12F + B) / (12C))
paid-intent signup threshold = ceil(build recovery subscribers / expected conversion)
```

### Sensitivity, not forecasts

| Scenario | Assumptions | Contribution | Cash break-even | 3x cash safety | 12-month build-recovery subscribers | Paid-intent signups |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Low | `F=$17`, `V=$0.25`, `B=$8,000`, 30% conversion | $27.26 | 1 | 2 | 26 | 87 |
| Base | `F=$26`, `V=$0.75`, `B=$15,000`, 20% conversion | $26.76 | 1 | 3 | 48 | 240 |
| High | `F=$64`, `V=$2.50`, `B=$25,000`, 10% conversion | $25.01 | 3 | 8 | 86 | 860 |

The infrastructure values are anchored to current list prices. `V`, `B`, conversion, and
support/incident labor are assumptions because no Hosted Pro workload or conversion data
exists. Legal cost is not quoted and must be inserted into `B`, not treated as zero.

**Recommendation.** Do not adopt a single paid-intent count from this document. At the
architecture review, Ryan must choose the internal build-cost basis and acceptable
conversion assumption. The resulting formula becomes the recorded gate. The table shows
why one subscriber can cover cash infrastructure but cannot justify the build.

## Three complete conditional architectures

### A — selected lowest-operations stack

Render Starter web + Render Postgres + Render cron + WorkOS AuthKit + Stripe conditional
Checkout/Billing/Entitlements + Render logs/metrics + external uptime + optional scrubbed
Sentry.

- Baseline cash: about $17/month before growth, payment fees, optional workspace/support,
  Sentry upgrade, and legal/engineering labor.
- Lock-in: Render deployment configuration and WorkOS identity records; application remains
  OCI/PostgreSQL/OAuth based.
- Main failure modes: single small web instance, WorkOS/client audience mismatch, cron/
  migration overlap, DB restore/cutover errors, payment eligibility, and source-rights
  rejection.
- Scale thresholds: add a second web instance only after a concurrency/load test; keep DB
  pool bounded; move rate counters to Redis only when PostgreSQL contention is measured;
  move to Render Pro/HA only when revenue and an external SLA require it.

### B — lowest-cash elastic stack

Cloud Run service + Neon Launch + Cloud Run Job/Cloud Scheduler + WorkOS + conditional
Stripe + Google logs/metrics + external uptime/Sentry.

- Can scale compute toward zero; actual cost is workload-dependent and Neon estimates a
  typical intermittent 1GB database at $15/month.
- Cross-provider public TLS below Neon Scale, dual cold starts, variable billing, and
  at-least-once scheduling increase proof and operations burden.
- Select only if measured Render traffic/cost shows a material advantage.

### C — maximum portability/control stack

ECS Fargate + ALB + private RDS PostgreSQL + EventBridge Scheduler + WorkOS/Auth0 +
conditional Stripe + CloudWatch/OpenTelemetry/Sentry.

- Standard OCI, PostgreSQL, VPC, mature HA/PITR, and fine-grained controls.
- ALB, NAT/public IP, task, database, logs, scheduler, secrets, and support produce a
  materially higher and topology-dependent cost.
- Select only after scale, enterprise procurement, region, or SLA requirements exceed
  Render's operating envelope.

## Acceptance gates

Hosted Pro may be built only after the paid-intent formula is approved and cleared. It may
accept payment only after all gates below pass:

1. **GTM gate:** actual Local Beta paid-intent evidence clears the recorded cost formula.
2. **Legal/output gate:** one scoped decision covers exact dossier fields, scoring language,
   compensation, users/jurisdictions, disclosure, and distribution.
3. **Source-rights gate:** every centralized source has automation, retention, paid derived
   output, attribution, deletion, and redistribution decisions; unresolved means disabled.
4. **Payment gate:** written provider acceptance of the exact product and marketing; test
   checkout only until approved.
5. **OAuth gate:** exact Claude.ai/Desktop, Claude Code, and Codex flows prove metadata,
   PKCE, DCR/CIMD fallback, audience/resource, refresh, revocation, logout, and expiry.
6. **Tenant gate:** cross-principal tests prove RLS, entitlement, metering, rate limits,
   deletion, and absence of content/query-history retention.
7. **Billing gate:** signed webhooks, duplicate/out-of-order events, idempotent entitlement
   changes, cancellation, failed payment, refund, dispute, and reconciliation pass.
8. **Transport gate:** initialize, tool discovery, one populated score, claim pagination,
   disconnect/reconnect, SIGTERM drain, and request timeout pass through real ingress.
9. **Operations gate:** live/ready checks, circuit metrics, secret rotation, deploy rollback,
   migration rollback, alert delivery, incident runbook, and support channel pass.
10. **Recovery gate:** PITR restore to a new DB, count/constraint/immutable-ID reconciliation,
    cutover, and rollback meet RPO/RTO.
11. **Directory gate:** if pursued, Anthropic test credentials, tool annotations, privacy,
    support, examples, finance-policy review, and submission readback pass. Directory
    acceptance is not assumed.

## Verification performed in this research

- `uv run pytest -q tests/contract/test_mcp_contract.py -k 'HTTP_DISCOVERY or HTTP_INVOCATION'`
  — 2 passed.
- `uv run pytest -q tests/test_evidence_store.py tests/test_settings.py` — 34 passed.
- Official SDK in-process OAuth boundary spike — metadata `200`, unauthenticated `401`
  with `resource_metadata`, authenticated initialize `200`, protocol 2025-11-25, SDK 1.28.1.
- No account, external OAuth tenant, payment product, database, cloud service, deployment,
  or directory submission was created.

## Code references

- [`GTM_PLAN.md:81-98`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/GTM_PLAN.md#L81-L98) — Hosted Pro hypothesis and build/legal gate.
- [`TDD.md:590-602`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/TDD.md#L590-L602) — current hosted-service prerequisites.
- [`catalyst_edge_mcp/server.py:31-124`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/server.py#L31-L124) — composition root and in-process collectors.
- [`catalyst_edge_mcp/settings.py:118-120`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/settings.py#L118-L120) — loopback-only HTTP enforcement.
- [`catalyst_edge_mcp/evidence_store.py:102-290`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/evidence_store.py#L102-L290) — SQLite/WAL schema and in-process migration behavior.
- [`catalyst_edge_mcp/collection_lifecycle.py:131-261`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/collection_lifecycle.py#L131-L261) — lifecycle scheduler that must move out of hosted web replicas.

## Architecture documentation

The conditional decision and implementation boundary are recorded in
[thoughts/unknown-ticket/design/2026-08-03-ADR-hosted-pro-architecture.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/thoughts/unknown-ticket/design/2026-08-03-ADR-hosted-pro-architecture.md).

## Historical context

- [thoughts/unknown-ticket/research/2026-08-01-RESEARCH-monetization-readiness.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/thoughts/unknown-ticket/research/2026-08-01-RESEARCH-monetization-readiness.md) — Local Beta and Hosted Pro decision boundary.
- [docs/commercial/source-rights-matrix.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/commercial/source-rights-matrix.md) — current fail-closed source/output rights record.
- [docs/commercial/release-readiness-plan.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/commercial/release-readiness-plan.md) — Local Beta release proof; Hosted Pro is explicitly separate.

## Related research

- [docs/research/2026-07-21-free-open-source-coverage-research.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-free-open-source-coverage-research.md)
- [docs/research/2026-07-21-point-in-time-backtest-dataset-research.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/docs/research/2026-07-21-point-in-time-backtest-dataset-research.md)

## Open questions

- Which internal build-cost and paid-intent conversion assumptions should become the GTM
  gate? Answered conditionally in the follow-up research below; Ryan's approval remains
  required before the recommendation becomes the recorded product gate.
- Will Stripe, Lemon Squeezy, or another provider approve the exact non-advisory product?
- Will the exact WorkOS configuration complete OAuth with Claude.ai/Desktop, Claude Code,
  and Codex, including refresh and revocation?
- Will Anthropic classify the deterministic score as a high-impact financial decision or
  investment-advice surface, and will it accept the connector into the directory?
- Which jurisdictions and deletion/retention periods will the scoped legal decision allow?
- What are measured calls/user/month, concurrency, storage, egress, support, and incident
  load after Local Beta? Until measured, variable costs and scale thresholds are estimates.

## Follow-up Research 2026-08-03T15:56:06-04:00

### Question

What build-cost, operating-cost, conversion, retention, and evidence assumptions should
govern the `$29/month` Hosted Pro paid-intent gate, and what staged decision rule is best
supported by current evidence?

### Recommendation

Do **not** use the earlier illustrative `$15,000` build cost or `20%` intent-to-paid
conversion as the product gate. Fresh bottom-up and market research does not support either.

Use three cumulative, self-serve gates:

1. **350 activation-linked, verified, price-aware signups:** authorize at most a 56-hour
   disposable OAuth/client interoperability spike. No hosted product build.
2. **1,350 activation-linked, verified, price-aware signups:** authorize the single scoped
   legal/source/payment-provider review, subject to an explicit target and spending approval.
3. **11,100 recent activation-linked, verified, price-aware signups:** safeguarded base-case
   threshold at which the complete payment-ready Hosted Pro build can be considered.
   Recalculate from actual workload, review cost, and observed funnel data before authorizing
   implementation.

These are investment gates, not forecasts or claims of customers. If only a raw email/
willingness form exists and successful Local Beta use cannot be linked, do not apply the
activation-linked thresholds: report the raw cohort separately and treat its conversion as
unresolved.

At `$29`, the best current decision is therefore to release and measure Local Beta plus the
price-explicit intent surface, not build Hosted Pro. The infrastructure bill is inexpensive;
the PostgreSQL port, OAuth, RLS, billing, metering, recovery, privacy, and ongoing operations
are not. If the base full-build gate proves unattainable, stop or re-test scope and price—do
not weaken the evidence standard to make the build appear justified.

### What changed from the first model

The earlier sensitivity table used hypothetical `B=$8k/$15k/$25k` and `30%/20%/10%`
conversion inputs. It was labeled illustrative, but current evidence now provides stronger
planning ranges:

- **Conversion:** the best current B2B software dataset reports `3–5%` as good freemium
  conversion and `8–12%` as great, not `20%` as a normal base case. [ChartMogul and
  ProductLed's 2026 Conversion Report](https://chartmogul.com/reports/saas-conversion-report/)
  surveyed 200 B2B software products and reports a `5.5%` regular-freemium median. OpenView's
  450-plus-respondent 2022 benchmark independently reports `5%` free-to-paid conversion and
  `6%` visitor-to-free signup. [OpenView 2022 Product
  Benchmarks](https://openviewpartners.com/2022-product-benchmarks/)
- **Waitlist evidence:** no credible transparent aggregate benchmark was found for
  prelaunch SaaS waitlist-to-paid or local/open-source-to-hosted conversion. Freemium is the
  nearest proxy, not a direct fact about Catalyst. A 77-study willingness-to-pay meta-
  analysis found hypothetical willingness averaged `21%` above real willingness, reinforcing
  that a `$29` form response is directional rather than a payment commitment. [Schmidt and
  Bijmolt](https://doi.org/10.1007/S11747-019-00666-6)
- **Build effort:** the repository contains about 10,400 application and 7,000 test lines.
  It has no current hosted OAuth, tenant control plane, PostgreSQL migration layer,
  subscription system, externalized collectors, or hosted deletion/incident machinery. The
  payment-ready ADR maps to `440–680` raw engineering hours and `550–850` hours after a `1.25`
  trust-boundary planning multiplier.
- **Labor value:** BLS reports a `$133,080` median annual software-developer wage. Current
  professional-occupation compensation data supports about `$93/hour` fully loaded; this
  model rounds to `$95/hour`. [BLS software developers](https://www.bls.gov/ooh/Computer-and-Information-Technology/Software-developers.htm),
  [BLS employer compensation](https://www.bls.gov/news.release/ecec.nr0.htm)
- **Specialist review:** the scoped product/output, source-rights, privacy/retention, and
  provider review is estimated at `22–50` specialist hours. Clio's 2025 billing dataset puts
  the US lawyer average at `$349/hour` and corporate work at `$461/hour`; the model uses the
  latter. This is a reserve, not a counsel quote or legal clearance. [Clio 2026 rate
  comparison](https://www.clio.com/resources/legal-trends/compare-lawyer-rates/)
- **Maintenance:** the architecture implies `16–36` engineering hours/month for security
  and releases, auth/billing support, source drift, monitoring/incidents, restore drills,
  deletion, and audit upkeep. The `$17/month` Render baseline is only cloud cash cost.

### Bottom-up work breakdown

| Payment-ready workstream | Raw hours |
| --- | ---: |
| Hosted composition, container, Render configuration, health and drain | 24–36 |
| PostgreSQL store port, pooling, migrations and fixture parity | 80–120 |
| Control schema, roles, RLS, identity bootstrap and isolation tests | 56–88 |
| OAuth metadata, WorkOS, token validation and real-client compatibility | 48–72 |
| Metering, rate windows, HMAC rotation, fenced leases and SEC limiter | 56–88 |
| Stripe Checkout, portal, webhooks, entitlements and reconciliation | 48–72 |
| Collector decoupling, locks, cron, retention and deletion jobs | 36–56 |
| Secret-free telemetry, alerts, privacy controls and runbooks | 36–56 |
| Ingress/load, rollback, PITR restore, cutover and end-to-end proof | 56–92 |
| **Raw total** | **440–680** |
| **Planned at 1.25 multiplier** | **550–850** |

The largest repository-grounded surfaces are the SQLite-specific evidence store
([`evidence_store.py:102-290`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/evidence_store.py#L102-L290)),
the in-process composition/collection lifecycle
([`server.py:31-124`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/c94f3731584679cfbc714ddcd4260526d2f9a821/catalyst_edge_mcp/server.py#L31-L124)),
and the conditional acceptance surface recorded in the companion ADR. Local Beta SQLite,
customer data, additional sources, directory submission, multi-region HA, and brokerage or
advice remain outside this estimate.

### Recommended economic inputs

| Input | Upside | Base | Stress | Basis |
| --- | ---: | ---: | ---: | --- |
| Planned engineering hours | 550 | 700 | 850 | Bottom-up WBS with 1.25 multiplier |
| Engineering value/hour | $95 | $95 | $95 | Rounded BLS loaded-labor benchmark |
| Specialist review hours | 22 | 36 | 50 | Scoped review work breakdown |
| Specialist reserve/hour | $461 | $461 | $461 | Clio corporate billing average; not a quote |
| One-time economic cost `B` | $62,392 | $83,096 | $103,800 | Engineering plus specialist reserve |
| Maintenance hours/month | 16 | 24 | 36 | Bottom-up operating work breakdown |
| Fixed monthly economic cost `F` | $1,537 | $2,297 | $3,437 | Maintenance at $95/hour plus $17 cloud baseline |
| Activated intent -> paid within 6 months | 8% | 5% | 2.5% | 2026 freemium proxy; Catalyst remains unmeasured |
| Annual gross-revenue retention factor | 75% | 50% | 25% | Constant-hazard GRR sensitivity; Catalyst remains unmeasured |
| Qualified visit -> verified intent | 6% | 4.5% | 3% | ChartMogul/OpenView/Unbounce sensitivity |

The retention range is deliberately wide and uses **gross revenue retention only**—no
expansion revenue. ChartMogul's 2025 retention dataset reports `23%` GRR for AI-native
products below `$50/month`; that anchors the stress case. The `50%` and `75%` cases are
planning sensitivities, not interpolations from the report's non-comparable B2B NRR metric.
The exponential curve further assumes a constant churn hazard and no contraction. None of
these are observed Catalyst performance. [ChartMogul 2025 retention
report](https://chartmogul.com/reports/saas-retention-the-ai-churn-wave/)

### Transaction and contribution calculation

For one `$29` domestic-card monthly subscription:

```text
Stripe Payments       = 29*2.9% + $0.30 = $1.141
Stripe Billing        = 29*0.7%         = $0.203
Stripe Tax Basic      = 29*0.5%         = $0.145
total payment leakage P                 = $1.489
machine variable reserve V              = $0.750 (planning inference)
monthly contribution C                  = 29 - 1.489 - 0.750 = $26.761
```

The pricing inputs are current official list prices: [Stripe
Payments](https://stripe.com/pricing), [Stripe
Billing](https://stripe.com/billing/pricing), and [Stripe Tax
Basic](https://stripe.com/tax/pricing). International cards, currency conversion, refunds,
disputes, registrations, filing, and incident spikes remain excluded.

The `$0.75` variable reserve has no Catalyst workload behind it; it is retained only as a
clearly labeled base inference until calls, storage and egress are measured. The following
shows its effect on the unsafeguarded three-month-lag point estimate:

| Per-subscriber machine `V` | Contribution | Required payers | Activation-linked signups |
| ---: | ---: | ---: | ---: |
| $0.00 | $27.511 | 417 | 8,340 |
| **$0.75** | **$26.761** | **429** | **8,580** |
| $2.50 | $25.011 | 459 | 9,180 |
| $5.00 | $22.511 | 510 | 10,200 |

WorkOS AuthKit remains `$0` below one million monthly active users; a custom domain would add
`$99/month` and is excluded. [WorkOS pricing](https://workos.com/pricing) Render's selected
topology is about `$17/month`: roughly `$13` for web/database plus four `$1` cron minimums.
[Render cost example](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses)

### Churn-aware 24-month recovery

The first formula incorrectly treated every converted signup as paying from month zero for
every recovery month. The revised model charges 24 calendar months of fixed cost and applies
a three-month planning midpoint—not a conservative bound—within the six-month conversion
window, so a converted payer has a 21-month revenue horizon:

```text
expected paid months M(r) = sum from month 0 to 20 of r^(month/12)
required initial payers    = ceil((B + disposable_spike + 24F) / (C * M(r)))
required intent signups    = ceil(required initial payers / intent_to_paid)
```

| Scenario | Expected paid months | Cumulative 24-month cost | Initial payers | Activation-linked intent signups | Steady active subscribers |
| --- | ---: | ---: | ---: | ---: | ---: |
| Upside | 16.70 | $104,600 | 235 | 2,938 | 163 |
| **Base** | **12.52** | **$143,544** | **429** | **8,580** | **224** |
| Stress | 8.36 | $191,608 | 857 | 34,280 | 299 |

This table is a sensitivity, not the recommended investment gate. The cumulative cost adds
the `$5,320` disposable spike to the WBS/legal reserve and 24
months of fixed economic cost. It does not reuse the spike cohort's contribution to justify
later spending. “Steady active subscribers” is the count needed to cover monthly cost plus
straight-line 24-month recovery without cohort churn.

No visitor-equivalent is claimed: the probability that a price-aware signup also supplies
linkable Local Beta activation is unknown. Any traffic number that ignores that step would
be a lower bound, not an equivalent acquisition requirement.

Conversion timing alone changes the base point estimate:

| Conversion lag | Expected paid months | Required payers | Point-estimate signups at 5% |
| ---: | ---: | ---: | ---: |
| 0 months | 13.36 | 402 | 8,040 |
| 3 months | 12.52 | 429 | 8,580 |
| 6 months | 11.52 | 466 | 9,320 |

The recommended full-build gate uses the six-month lag, adds a `10%` economic-model reserve
for excluded costs/time value, and requires the one-sided 95% binomial lower projection at a
true `5%` conversion assumption to cover the resulting `513` required payers. That produces
`11,013` qualifying signups, rounded up to **11,100**. This protects against counting noise
conditional on `5%`; it does not prove that Catalyst's true conversion is 5%.

### Why the staged gates are 350, 1,350, and 11,100

Using the base `5%` six-month conversion, `50%` annual GRR factor, three-month conversion
lag, and `$26.761` contribution gives about `$335.05` expected 21 paid-month contribution
per converted payer.

| Reversible decision | Cumulative cost basis | Required payers | Required activation-linked signups | Recommended rounded gate |
| --- | ---: | ---: | ---: | ---: |
| 56-hour compatibility spike | $5,320 | 16 | 320 | **350** |
| Spike plus 36-hour scoped specialist review | $21,916 | 66 | 1,320 | **1,350** |
| Spike, complete payment-ready build and 24-month operations | $143,544 point estimate | 513 after 10% reserve and six-month lag | 11,013 with one-sided conversion allowance | **11,100** |

The first two thresholds are **heuristic risk-budget caps**, not ROI or value-of-information
estimates. The spike cap is `$5,320 / 350 = $15.20` per recent qualifying signal; cumulative
spike/review exposure is `$21,916 / 1,350 = $16.23` per signal. Those ratios bound exploratory
spend but do not establish recoverable revenue or the economic value of the information. Each
expense still needs separate approval based on whether it can change the next decision. The
thresholds do not cumulatively authorize the full build. Actual quotes replace reserves;
actual funnel, retention, support, and workload data replace benchmarks as soon as they exist.

Qualifying intent expires after 180 days, matching the proxy's six-month conversion window.
Older users count only if they voluntarily reconfirm the current exact offer through the
self-serve surface; no outbound reconfirmation is implied or authorized. This limits cohort
aging but does not convert stated intent into revealed demand.

### Measurement rule

Count a signup toward the recommendation only when all of the following are true:

- the visitor saw the exact feature boundary, `$29/month`, billing cadence, and “coming
  soon” timing before answering;
- the email is double-opt-in verified and deduplicated;
- the user selected a supported MCP client;
- the answer is an explicit “Definitely yes, I would subscribe at $29/month”; and
- successful Local Beta use is linked by a privacy-preserving activation receipt or
  equivalent opt-in proof. Raw downloads and page visits are not activation.

Record offer version, acquisition source, analyst/builder cohort, and timestamp. Exclude
bots, staff, QA, duplicates, “maybe,” and unpriced waitlist emails. Report raw verified
price-aware intent separately when activation linkage is unavailable.

For the intent-rate denominator, use every unique qualified visitor shown the complete
offer. Pre-register a read after at least 250 qualified exposures and four weeks. Report the
one-sided 95% Wilson lower bound, not only the observed percentage. Wilson intervals are
better behaved than naive normal intervals for small binomial samples and rates near zero.
[NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), [Brown, Cai and
DasGupta](https://projecteuclid.org/journals/statistical-science/volume-16/issue-2/Interval-Estimation-for-a-Binomial-Proportion/10.1214/ss/1009213286.pdf)

The sample is self-selected. Its interval describes comparable exposed traffic, not all
analysts or builders. Do not present an opt-in sample as population-representative. [AAPOR
standards](https://aapor.org/standards-and-ethics/)

Every staged gate requires its cumulative recent activation-linked signup count. Separately,
the raw price-aware intent surface must maintain a one-sided 95% Wilson lower bound of at
least `3%` for the benchmarked event:

```text
verified + definitely-yes price-aware signups
-----------------------------------------------
unique qualified visitors shown the complete offer
```

At the initial `n=250` preregistered read, at least `12` raw qualifying signups are required:
the observed rate is `4.8%` and the one-sided lower bound is approximately `3.02%`. Recompute
the bound at each later gate using the full eligible cohort and separately by material source.
The `3%` floor is the downside acquisition assumption, not a population confidence claim.

Report activation-link yield separately as:

```text
recent activation-linked qualifying signups
---------------------------------------------
recent raw verified price-aware signups
```

No activation-yield floor is claimed until Catalyst measures it; the absolute staged counts
remain activation-linked. Do not inherit the `3%` raw-intent benchmark for the stricter joint
event.

### Decision sequence

1. Complete and release Local Beta only through its existing publication authorization
   gate.
2. Publish the exact price-aware, double-opt-in measurement surface with activation-linked
   and raw-intent cohorts separated.
3. At 350 qualifying signups, with the Wilson floor also passing, re-cost and, if explicitly
   authorized, run only the capped compatibility spike.
4. At 1,350, with the Wilson floor also passing, re-cost and, if explicitly authorized,
   obtain only the scoped legal/source/payment-provider decision. No quote shopping or
   broadened advisory work.
5. Do not authorize the full build before the recomputed gate clears; the current safeguarded
   base gate is 11,100 recent activation-linked qualifying signups, plus the separate raw-
   intent Wilson floor.
6. If a lawful self-serve checkout eventually exists, replace benchmark conversion with
   actual first-payment and first-renewal cohorts. Form intent never becomes “validated MRR.”
7. Recompute by acquisition source and cohort; do not let a small warm-audience result mask
   weak broader demand.

### Fact, inference, and unknown boundary

- **Fact:** current vendor prices, BLS/Clio benchmarks, repository surfaces, and published
  survey/sample results are cited above.
- **Inference:** the WBS hours, 1.25 multiplier, specialist hours, maintenance load,
  retention scenarios, and Catalyst conversion scenarios are planning judgments grounded in
  those facts. They are not quotes or observed Catalyst metrics.
- **Unknown:** actual Local Beta traffic, activation, signup conversion, paid conversion,
  churn, support load, calls/user, storage/egress, legal cost, provider eligibility, and
  client compatibility.
- **Stop gate:** no auth, billing, tenancy, hosted operations, payment account, deployment,
  or paid delivery is authorized by this recommendation.
