---
date: 2026-08-03T15:16:49-04:00
researcher: ryanmonroe
git_commit: c94f3731584679cfbc714ddcd4260526d2f9a821
branch: main
repository: catalyst-edge-mcp
type: adr
status: proposed-conditional
decision: "Render web, Render Postgres, Render cron, WorkOS AuthKit, conditional Stripe, minimal observability"
last_updated: 2026-08-03
last_updated_by: ryanmonroe
last_updated_note: "Aligned paid-intent activation gates with the current GTM plan"
---

# ADR: Conditional Hosted Pro architecture

## Status

**Proposed, conditional, and not authorized for implementation or deployment.**

This ADR's full build activates only if:

1. the self-serve Local Beta exists and produces at least 11,100 recent activation-linked,
   verified, price-aware Hosted Pro signups;
2. the separate raw verified intent rate maintains a one-sided 95% Wilson lower bound of at
   least 3% among qualified visitors shown the complete offer;
3. the exact paid output and claims receive the scoped legal decision required by
   `GTM_PLAN.md`;
4. centralized source/output rights pass;
5. the payment provider accepts the product;
6. the OAuth/client interoperability spike passes; and
7. Ryan explicitly authorizes the re-costed implementation target.

Until then, Local Beta remains customer-run with local SQLite and no hosted auth,
billing, tenancy, or operations.

Before the full-build gate, 350 recent qualifying signups permit only a separately
authorized 56-hour disposable compatibility spike; 1,350 permit only a separately
authorized scoped legal/source/payment-provider review. These are heuristic risk-budget
caps, not automatic spend, build, payment, or deployment authority. Qualifying intent
expires after 180 days unless voluntarily reconfirmed through the current self-serve offer.

## Context

The current package is a read-only local MCP with two tools, deterministic unbacktested
scoring, typed missingness, and fail-closed source policy. It has local stdio and loopback
Streamable HTTP but no public ingress, OAuth, tenants, rate metering, subscriptions,
PostgreSQL migrations, hosted collectors, incident process, or hosted deletion path.

The selected architecture must preserve:

- one ticker per score invocation and one bounded claim-source pagination tool;
- no recommendations, alpha/performance claims, alerts, brokerage, or execution;
- fail-closed source rights and typed provider failures;
- immutable claim/source IDs, exact counts, dedupe, corrections, and append-only audit;
- compact secret-free output and logs;
- a fully separate customer-owned Local Beta SQLite product; and
- an operating model supportable at the $29 price hypothesis.

## Decision

If the activation gates pass, build one US-region Hosted Pro v1 with:

- **Compute:** one Render paid Starter web service running the existing Python package as
  stateless Streamable HTTP at `/mcp`;
- **Database:** one paid same-region Render Postgres instance with integrated transaction-
  mode pooling and PITR;
- **Scheduled work:** separate Render cron services, with PostgreSQL advisory locks, for
  source collection, retention/deletion, backup export, and reconciliation;
- **OAuth:** WorkOS AuthKit as authorization server; the official `mcp` Python SDK remains
  the resource server and validates resource-bound bearer tokens through `TokenVerifier`;
- **Billing:** Stripe Checkout/Billing/Entitlements only after legal and provider approval;
- **Observability:** secret-free JSON logs, Render metrics/logs/health, one external uptime
  check, database audit/usage ledgers, and optional scrubbed Sentry Developer;
- **Distribution:** direct custom connector first. Anthropic directory submission is a
  later proof/distribution step, not a launch dependency; and
- **Data:** shared public evidence plus strictly principal-scoped identity, entitlement,
  usage, billing, and audit state. No query-content history or personal investing data.

Current list-price baseline is approximately $17/month before variable usage and optional
upgrades: about $13 for Starter web plus Basic-256 Postgres and four cron services at a
$1 minimum each. This is not the complete economic cost.

## Architecture

```text
Claude / Codex
      |
      | OAuth 2.1 + PKCE + RFC 8707 resource
      v
WorkOS AuthKit -------- browser consent/login
      |
      | resource-bound bearer token
      v
Render TLS ingress -> FastMCP /mcp
                         |
                         +-> verify scope + principal
                         +-> entitlement + atomic rate/meter check
                         +-> CatalystService
                         |      +-> SEC and approved providers
                         |      +-> typed partial failure
                         +-> append usage/audit result
                         |
                         v
               Render Postgres (private URL)
                 | shared_evidence schema
                 | control schema + RLS
                 | migration and advisory-lock state
                         ^
                         |
                 Render cron jobs

Stripe webhook -> signed/idempotent billing event -> entitlement state
Render/Sentry/Uptime -> secret-free operational telemetry
```

## Request sequence

1. Client discovers RFC 9728 protected-resource metadata for the exact `/mcp` resource.
2. Client authenticates with WorkOS using PKCE and DCR/CIMD as supported.
3. FastMCP validates signature, issuer, exact audience/resource, expiry, and
   `catalyst:read` scope. Token passthrough is prohibited.
4. Call a narrowly scoped `SECURITY DEFINER` bootstrap function that resolves an exact
   `(issuer, subject)` or inserts one `pending` principal on first authentication. It has a
   fixed `search_path`, returns only ID/state, and is the runtime role's only pre-RLS access.
   A pending principal receives a typed `subscription_required` response with the account
   URL; only billing reconciliation can activate its entitlement.
5. In one short PostgreSQL transaction:
   - `SET LOCAL app.principal_id` to that resolved ID for RLS;
   - require an active entitlement;
   - atomically enforce request/minute and request/month limits; and
   - acquire or reclaim a unique metering lease for a Catalyst operation key distinct from
     the MCP/JSON-RPC request ID.
6. Execute the unchanged validation, collection, normalization, scoring, and summary
   pipeline. Do not include auth/billing state in the dossier.
7. Complete the usage event with result class, duration, billable units, provider statuses,
   and a response digest. MCP/JSON-RPC IDs are correlation values only and are never used as
   persistent idempotency keys. A caller that supplies a Catalyst operation key receives
   **one meter charge per matching operation key/fingerprint**: a different fingerprint is
   rejected, an active lease returns retryable status, and an expired lease can be reclaimed.
   A completed duplicate returns a typed duplicate result without a second charge. The
   optional operation key must be a canonical UUID, not arbitrary text. Without one, the
   server assigns a new internal operation ID and makes no cross-call retry guarantee; SDK
   transport resumption remains separate. No arguments or response body are retained.
8. Return structured MCP output. Logs contain no tool arguments or output.

## OAuth contract

### Required endpoints and behavior

- `GET /.well-known/oauth-protected-resource/mcp` names the exact public MCP resource,
  WorkOS authorization server, and `catalyst:read` scope.
- Unauthenticated `/mcp` requests return `401` and `WWW-Authenticate` with
  `resource_metadata`.
- WorkOS metadata advertises supported registration path, PKCE S256, token endpoint, and
  revocation/refresh behavior.
- Authorization and token requests use RFC 8707 `resource` equal to the exact MCP URL.
- The resource server rejects wrong issuer, audience/resource, expiry, signature, scope,
  tenant state, or entitlement.
- OAuth tokens never flow to evidence providers or Stripe.

### Compatibility gate

The local SDK boundary test is necessary but insufficient. Before any hosted build is
called accepted, a disposable staging environment must prove:

- Claude.ai/Desktop fixed callback and consent;
- Claude Code loopback callback;
- Codex `codex mcp login` with configured `oauth_resource` and scope;
- CIMD where available and DCR fallback where not;
- refresh, revocation, expired token, removed entitlement, logout, and user deletion; and
- exact tool discovery and invocation after reauthentication.

No client credentials/M2M-only flow is a substitute for interactive compatibility.

## PostgreSQL design

### Schemas and roles

- `shared_evidence`: source observations, canonical events, event/source, claims,
  claim/source, insider facts/clusters, social buckets, collector state, source policy,
  and entity-match audit.
- `control`: principal, billing customer, subscription, entitlement, usage, billing event,
  security audit, rate window, deletion receipt, schema migration, and job lease.
- `mcp_runtime`: read shared evidence; principal-scoped access to control only through RLS;
  no DDL, migration, collector, or RLS-bypass rights.
- `identity_bootstrap_owner`: non-login owner of the exact resolve-or-insert bootstrap
  function; no update/delete, entitlement, billing, or shared-evidence rights.
- `collector_runtime`: write approved shared evidence and collector state; no billing or
  principal identity access.
- `migrator`: DDL only from pre-deploy/one-off migration command.

### Minimum tables

```text
control.principal
  id uuid pk
  issuer text not null
  subject text not null
  state text not null
  created_at timestamptz not null
  deletion_requested_at timestamptz null
  deleted_at timestamptz null
  unique (issuer, subject)

control.billing_customer
  principal_id uuid pk/fk
  provider text not null
  customer_id text unique not null

control.subscription
  id uuid pk
  principal_id uuid fk not null
  provider_subscription_id text unique not null
  state text not null
  current_period_start/end timestamptz
  provider_occurred_at timestamptz not null

control.entitlement
  principal_id uuid fk not null
  capability text not null
  state text not null
  valid_from/to timestamptz
  primary key (principal_id, capability)

control.rate_limit
  principal_id uuid fk not null
  capability text not null
  window_seconds integer not null
  limit_value integer not null
  primary key (principal_id, capability, window_seconds)

control.rate_window
  principal_id uuid fk not null
  capability text not null
  window_seconds integer not null
  window_start timestamptz not null
  units integer not null
  primary key (principal_id, capability, window_seconds, window_start)

control.usage_event
  id uuid primary key
  principal_id uuid fk not null
  operation_key uuid null
  protocol_request_id_sha256 char(64) null
  tool text not null
  request_hmac text not null
  request_hmac_key_id text not null
  units integer not null
  state/result_class text not null
  duration_ms integer null
  lease_owner uuid null
  lease_expires_at timestamptz null
  lease_generation bigint not null
  attempt_count integer not null
  response_sha256 text null
  occurred_at/completed_at timestamptz
  unique (principal_id, operation_key)

control.billing_event
  provider text not null
  provider_event_id text not null
  event_type/object_id text not null
  occurred_at/processed_at timestamptz
  payload_sha256 text not null
  status text not null
  primary key (provider, provider_event_id)
```

Every principal-scoped table has RLS. Tests must show that a transaction with principal A
cannot read, update, meter, or delete principal B. Shared evidence never acquires a
principal ID merely because it was requested by that principal.

The identity bootstrap function is owned by `identity_bootstrap_owner`, has a fixed schema-
qualified body and `search_path`, and grants only `EXECUTE` to `mcp_runtime`. It can select
an exact issuer/subject or `INSERT ... ON CONFLICT` one `pending` principal; it cannot
enumerate, update, delete, activate, or grant entitlement. Tests must prove exact matching,
concurrent first-login convergence, inactive-principal denial, no arbitrary SQL/search-path
substitution, and no access to any other principal field. Checkout/account linking and
signed billing reconciliation use separate scoped code paths after RLS is established.

`request_hmac` is an HMAC over the canonical tool request with a dedicated rotatable key; it
detects operation-key reuse without storing query content. `request_hmac_key_id` selects the
verification key. Rotation retains the prior verification key through the maximum operation
retention/lease window, new rows use only the new key, and retirement is blocked while a live
row still references the old key. An operation key is accepted only as a canonical UUID. A
protocol request ID is first bounded to 256 UTF-8 bytes, canonicalized by JSON type/value,
and stored only as a SHA-256 digest; raw protocol IDs are neither persisted nor logged.

Rate-limit consumption and lease acquisition are atomic. Each reclaim increments
`lease_generation`. Heartbeat, completion, metering, and response emission succeed only when
both `lease_owner` and `lease_generation` still match the pending row; a stale worker must
discard its result. Only an expired lease may be reclaimed. Abandoned attempts remain
auditable and never consume a second unit for the same operation key. Re-executed provider
reads can occur after a genuine lease expiry, but they remain read-only and pass through the
same global provider limiter.

### Migration strategy

1. Add a narrow store protocol shaped by existing `EvidenceStore` callers.
2. Make the composition root inject a SQLite or PostgreSQL implementation.
3. Preserve SQLite unchanged for Local Beta.
4. Add numbered SQL migrations and a separate migration command; hosted app startup
   verifies schema version but does not mutate it.
5. Port schema and methods to `psycopg`/pool with PostgreSQL equivalents.
6. Prove deterministic IDs, dedupe, pagination, correction lineage and export counts on
   identical fixtures for SQLite and PostgreSQL.
7. Start Hosted Pro with a new empty hosted evidence database. **No Local Beta import.**

Rollback uses the prior compatible application release and retains the database. Additive
migrations remain. Destructive schema changes require expand/migrate/contract and a proven
PITR restore; down-migrations that discard data are not the primary rollback mechanism.

## Collection and source policy

- Disable in-web-process GDELT/Bluesky lifecycle loops in hosted mode.
- Run each due collector from a separate cron command.
- Acquire a PostgreSQL advisory lock keyed by collector/source before work; duplicate or
  overlapping delivery exits successfully without collection.
- From launch, every web and cron process acquires permits from one PostgreSQL-backed global
  SEC token bucket before any SEC request. Process-local concurrency remains a secondary
  guard only. Prove aggregate fair-access behavior across simultaneous web and collector
  processes; Redis is considered only if measured PostgreSQL contention warrants it.
- Hosted v1 is SEC-only unless a source's paid centralized automation, retention,
  transformation, attribution, deletion, and output rights all pass.
- Provider outage/rights failure remains typed missingness and cannot create directional
  evidence or readiness credit.

## Billing and entitlements

Stripe is conditional. It is not authorized by this ADR.

If approved:

- use hosted Checkout and customer portal; do not collect card data;
- use one recurring $29 product and a single `catalyst:read` entitlement;
- accept only required signed webhook types;
- insert the provider event ID before effects; duplicates return `2xx` as no-ops;
- fetch/reconcile provider object state when event order is ambiguous;
- update subscription and entitlement atomically;
- never grant access from a checkout success redirect alone;
- never revoke a paid entitlement solely because one webhook delivery is late;
- test trial/no-trial decision, payment success/failure, cancellation at period end,
  immediate revocation policy, refund, dispute, duplicate, replay and provider outage; and
- reconcile active provider subscriptions to internal entitlements daily under a job lock.

If Stripe rejects the product, stop and review a provider explicitly willing to carry the
exact product. Do not relabel the output to evade provider policy. Paddle's current AUP is
not the fallback default. Lemon Squeezy is conditional on store approval.

## Limits and abuse controls

Initial limits are configuration, not marketing promises:

- request body and MCP message size ceiling;
- one ticker and existing lookback maximum per score call;
- per-principal concurrent request cap;
- per-principal rolling minute and monthly tool-call limits;
- global SEC provider concurrency/start-rate ceiling;
- bounded provider timeouts, no unbounded retry, and existing typed partial response;
- account/email verification and token revocation on abuse; and
- no user-supplied URLs, source credentials, holdings, prompts, or provider selection.

Do not set numeric paid-plan call limits until Local Beta/paid-intent workload assumptions
are recorded. Comparable products show explicit limits, but their workload is not
Catalyst's workload.

## Health and operations

### Endpoints

- `/health/live`: process event loop responds; no dependency calls.
- `/health/ready`: schema version is accepted, DB query passes, migration is not pending,
  and required configuration is present. It does not query SEC or other sources.

### Telemetry

Log only release, internal operation ID, pseudonymous principal, tool, status, duration,
usage units, provider status/error class and circuit state. Never log a protocol request ID,
operation key, token, authorization header,
email, ticker, MCP arguments/output, raw provider body, URL query strings, or Sentry
breadcrumbs containing them.

Required dashboards/alerts:

- ingress availability, 4xx/5xx, latency and active requests;
- OAuth challenge/token failures by class without identity content;
- entitlement denials and rate-limit counts;
- provider calls, successes, 429, timeout, schema/permission failures, breaker and last
  success age;
- PostgreSQL connections, pool wait, storage, CPU, locks, migration version and job lease;
- webhook duplicates/failures/reconciliation drift; and
- deletion and restore job completion.

### SLO and recovery

- internal availability objective: 99.5% monthly, no external SLA initially;
- p95 completed score call: under 10 seconds;
- RPO: 15 minutes;
- RTO: four hours;
- quarterly restore rehearsal after the mandatory pre-payment restore proof; and
- deploy rollback plus database cutover must include real client readback, not dashboard
  health alone.

## Privacy and deletion

- Do not persist query ticker, prompt, dossier, or tool arguments in usage/audit state.
- Request logs: 14 days. Error/trace telemetry: at most 30 days. Usage/security audit:
  proposed 90 days subject to legal confirmation.
- On deletion: revoke sessions and entitlement immediately; remove identity linkage and
  online usage/audit within 30 days; retain only statutory billing records and a minimal
  deletion receipt.
- Shared public/source-policy evidence is not deleted with a principal because it is not
  principal-owned. Source-specific takedown/correction rules still apply.

## Deployment and rollback

1. Build a digest-pinned OCI image from an authorized clean commit.
2. Run CI-equivalent lock/lint/tests/build and installed-artifact checks.
3. Run additive migration through the migrator role.
4. Deploy staging; run OAuth/client, cross-tenant, billing sandbox, transport and restore
   acceptance.
5. Deploy production only after explicit deployment/payment authority.
6. Render routes traffic only after readiness passes; the app handles SIGTERM and drains
   in-flight MCP calls within the configured shutdown window.
7. Roll back application to a known build artifact/digest. Configuration and DB state are
   separately versioned and read back.
8. For data loss, PITR creates a new DB. Verify counts/constraints/tool results, change the
   private connection, and retain the original until the recovery is accepted.

## Rejected alternatives

- **Local SQLite on a persistent disk:** disables Render zero-downtime behavior, lacks
  multi-instance coordination/tenant state, and couples recovery to one volume.
- **Turso/libSQL:** easier SQLite migration does not remove driver, transaction, PRAGMA,
  concurrency and tenancy work; shared evidence/control data favors PostgreSQL.
- **LiteFS:** pre-1.0/unsupported and carries explicit stale-leader/data-loss risks.
- **Vercel:** now technically plausible for some FastAPI streaming, but overlapping cron,
  beta long duration and Enterprise private networking add lifecycle risk.
- **Cloudflare:** inexpensive but requires a Workers/Containers/Durable Objects replatform
  rather than a low-risk Python lift-and-shift.
- **AWS App Runner:** 120-second timeout, no native scheduler, unavailable to new users.
- **Self-hosted OAuth:** disproportionate security and operations risk for a $29 validation
  stage.
- **Paddle as automatic MoR:** its AUP's investment-advice/signals language creates a
  load-bearing eligibility question, not a shortcut around Stripe review.

## Consequences

### Positive

- Lowest current operations surface while preserving OCI/PostgreSQL/OAuth portability.
- Same-provider private app/database traffic, managed pooling/PITR, long requests,
  health replacement, rollback and singleton cron.
- Local Beta stays simple and customer-owned.
- Shared evidence avoids duplicate per-tenant storage; RLS isolates control state.
- External auth and hosted checkout minimize password/card handling.

### Negative

- PostgreSQL is a real implementation port, not a connection-string change.
- WorkOS, Stripe and Render create vendor dependencies and still require exact acceptance
  proofs.
- A $17 cash baseline understates engineering, legal, support and incident cost.
- One small instance has no initial HA guarantee; 99.5% is an objective, not an SLA.
- Anthropic directory status remains discretionary and may impose finance-policy limits.

## Scale transitions

- **One to two web replicas:** only after concurrency/load testing of the launch-time global
  SEC limiter; prove no duplicate collectors or usage events.
- **Database upgrade/HA:** when measured connection/storage/CPU headroom or an external SLA
  requires it, and recurring revenue covers the upgrade with safety margin.
- **Redis/rate service:** only when atomic PostgreSQL counters/leases are measured as a
  bottleneck.
- **Render to ECS/RDS:** when region, private network, compliance, procurement, SLA, or
  scale requirements justify the additional control plane. Keep OCI, PostgreSQL,
  numbered SQL migrations and standard OAuth to preserve this path.

## Acceptance checklist

- [x] Paid-intent gate formula and owner inputs recorded in `GTM_PLAN.md` and the research:
      350 capped spike, 1,350 scoped review, 11,100 safeguarded full-build reconsideration.
- [ ] Scoped paid-output/legal decision complete.
- [ ] Hosted source-rights matrix complete; unresolved sources disabled.
- [ ] Payment provider eligibility confirmed in writing.
- [ ] WorkOS staging plus Claude/Codex compatibility matrix passes.
- [ ] PostgreSQL fixture parity and migration rollback pass.
- [ ] RLS/cross-principal tests pass with non-owner runtime role.
- [ ] Request/rate/usage idempotency and reconciliation pass.
- [ ] Billing webhook duplicate/out-of-order/refund/cancel/failure tests pass.
- [ ] Real Render ingress initialize/discovery/score/pagination/disconnect/drain passes.
- [ ] Cron overlap and PostgreSQL advisory lock pass.
- [ ] Secret rotation, health replacement and release rollback pass.
- [ ] PITR restore, reconciliation, cutover and RPO/RTO pass.
- [ ] Privacy retention/deletion flow and receipts pass.
- [ ] Support/incident channel and runbook exist.
- [ ] Anthropic directory checklist passes if submission is pursued.
- [ ] Ryan explicitly authorizes the exact build/deployment/payment actions.

## Research basis

See
[thoughts/unknown-ticket/research/2026-08-03-RESEARCH-hosted-pro-architecture.md](https://github.com/rm0nroe/catalyst-edge-mcp/blob/main/thoughts/unknown-ticket/research/2026-08-03-RESEARCH-hosted-pro-architecture.md).
