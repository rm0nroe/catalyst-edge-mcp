---
date: 2026-08-03
research_target: thoughts/unknown-ticket/research/2026-08-03-RESEARCH-hosted-pro-architecture.md
companion_target: thoughts/unknown-ticket/design/2026-08-03-ADR-hosted-pro-architecture.md
status: resolved
cycles: 2
---

# Hosted Pro architecture research critique

## Cycle 1

The substance review found five nontrivial defects:

- **BLOCKER — quota cardinality:** one entitlement row could not represent both minute and
  monthly limits. Resolved by separating capability grants, rate-limit definitions, and
  atomic rate windows.
- **RISK — incomplete retry semantics:** the usage ledger lacked request matching and lease
  recovery fields while claiming general idempotence. Resolved by narrowing the guarantee
  to one metering charge, adding request HMAC, lease/attempt state and response digest, and
  specifying active, expired, mismatched and completed duplicate behavior without retaining
  arguments or response bodies.
- **GAP — RLS identity bootstrap:** principal lookup occurred before the RLS principal was
  available. Resolved with a minimal fixed-path `SECURITY DEFINER` resolver and explicit
  abuse/isolation tests.
- **RISK — SEC limiting was not global:** web and cron processes could issue independently.
  Resolved by requiring one PostgreSQL-backed token bucket for every SEC caller from launch.
- **RISK — fixed-cost baseline:** four selected cron services were priced as one. Resolved by
  changing the baseline from $14 to $17 and recalculating the affected sensitivity row.

No implementation, provider account, payment surface, deployment, or release was created.

## Cycle 2

The second pass found three nontrivial consistency defects:

- **BLOCKER — protocol request ID misuse:** JSON-RPC correlation IDs were modeled as a
  globally unique UUID. Resolved by using an internal operation UUID, making the optional
  Catalyst operation key explicitly principal-scoped, and retaining the protocol ID only as
  text correlation data.
- **RISK — HMAC rotation:** request fingerprints lacked a key version. Resolved with a
  persisted key ID, an overlap window, new-key-only writes, and reference-aware retirement.
- **GAP — research/ADR drift:** the research still described the superseded quota and usage
  schema. Resolved by bringing the research data model and retry limits into exact alignment
  with the ADR.

## Cycle 3

The final substance pass found three further launch defects:

- **BLOCKER — no first-user provisioning:** pre-RLS lookup required an existing active
  principal. Resolved with a fixed-path resolve-or-insert bootstrap that may create only a
  pending principal; it cannot activate access, and signed billing reconciliation remains
  the entitlement authority.
- **RISK — unfenced lease takeover:** a stale worker could complete after lease reclamation.
  Resolved with an incrementing lease generation required alongside owner identity for every
  heartbeat, completion, meter, and response-emission write.
- **RISK — unbounded client identifiers:** raw operation and protocol IDs could retain
  sensitive content or exceed index limits. Resolved by restricting operation keys to UUIDs,
  bounding/canonicalizing and digesting protocol IDs, and logging neither raw value.
