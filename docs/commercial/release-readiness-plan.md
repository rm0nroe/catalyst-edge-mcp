# Customer-Installable Release Readiness Plan

**Status:** Plan only. No public package, hosted service, registry listing, or release automation is authorized by this document.

## Release target

Deliver a pinned wheel and source distribution for Python 3.10+ that a customer can install into one controlled MCP environment, verify from hashes, configure without editing package code, connect to an MCP client, and roll back to the prior pinned version.

The initial channel should be a private, access-controlled release handoff agreed with the customer. PyPI, MCP registries, remote hosting, tenancy, billing, and managed alerts remain demand-gated later decisions.

## Gates

| Gate | Required evidence | Current state |
| --- | --- | --- |
| R0 — scope freeze | product specification/technical specification/GTM agree on two local read-only tools, one ticker per call, deterministic unbacktested scoring, typed missingness, and no recommendation | Met locally; recheck at release candidate |
| R1 — reproducible artifact | Clean build creates wheel and sdist from the declared version; both install; SHA-256 manifest and release notes exist | Local RC `0.1.1` proof passes; still partial until built from a clean reviewed commit after CI |
| R2 — validation CI | Lock check, lint, offline test suite, contract tests over stdio and loopback HTTP, supported-Python matrix, and installed-artifact smoke all pass | Workflow implemented and locally reproduced on Python 3.10/3.14; installed wheel passed stdio and loopback HTTP; GitHub-hosted run still required |
| R3 — configuration contract | Reviewed `.env.example`, customer-owned credential rules, source allowlist/denylist record, local state path, retention decision, and secret-free diagnostics | Fail-closed template exists; customer facts, rights rows, owners, retention, and approval remain open |
| R4 — five-minute onboarding | Clean-machine runbook reaches MCP tool discovery within five timed minutes after Python, `uv`, and client prerequisites | Local MCP SDK first attempt passed in 2.679 seconds; named customer client/environment proof remains open |
| R5 — demo acceptance | Five separate ticker calls, one dossier review, complete claim pagination, and one missing/rejected case pass | RC `0.1.1` automated proof passes A4/A6/A7; customer review/acknowledgement remains open |
| R6 — rollback | Prior artifact/configuration can be restored without deleting customer evidence | Local `0.1.0 -> 0.1.1 -> 0.1.0` proof passed with unchanged evidence-store hash |
| R7 — delivery authority | Completed deployment rights record, counsel-approved terms, price, signatures, and customer owner | Open; blocks paid delivery |

R7 is the final release gate. Passing technical gates does not authorize delivery.

The current local evidence and exact remaining boundary are recorded in
[`docs/validation/release-candidate-0.1.1-2026-08-02.md`](../validation/release-candidate-0.1.1-2026-08-02.md).
The adjacent JSON record is the read-only input to the deterministic local evidence audit.

## Required CI lanes

One required workflow should run on pull requests and release tags:

1. `uv lock --check`.
2. `uv run ruff check .`.
3. `uv run pytest -q` on the minimum and current supported Python versions; expand the matrix only to versions actually supported by dependencies and tested locally.
4. Contract tests for tool discovery, strict input schemas, structured output, stdio, loopback streamable HTTP, and claim pagination.
5. `uv build --no-sources` from a clean checkout.
6. Install the built wheel in a fresh environment, verify `catalyst-edge-mcp`, `catalyst-edge-score`, and `catalyst-edge-smoke` entry points, then run offline tool discovery and one schema-valid no-data call.
7. Verify the sdist contains the license, README, packaged registry, and no `.env`, SQLite state, cache, or credential material.
8. Produce SHA-256 hashes and retain the test summary with the release candidate.

Live provider checks must remain opt-in and separate from required offline CI because they use credentials, external availability, rate limits, and time-sensitive evidence. A live success does not replace contract validation.

## Version and artifact procedure

- Use semantic versions; the package version, git tag, wheel, sdist, and release notes must agree.
- Build only from a clean, reviewed commit after all required CI passes.
- Name the manifest `catalyst-edge-mcp-<version>-SHA256SUMS.txt` and include both artifacts.
- Record Python versions, `uv.lock` hash, test count, and artifact hashes in release notes.
- Do not bundle `.env`, customer registries, credentials, SQLite/WAL files, logs, demo output, or provider payloads.
- Keep the previous accepted artifacts and configuration available through the engagement rollback window.

## Customer configuration contract

The handoff must state, without secrets:

- package version and hash;
- Python and `uv` prerequisites;
- stdio or loopback HTTP transport and customer-owned process supervisor;
- exact enabled source IDs and the signed rights record for each;
- SEC identity ownership and contact-monitoring responsibility;
- registry file path and hash when a customer-specific registry is used;
- evidence-store path, backup owner, retention duration, and deletion owner;
- outbound hosts and expected request ceilings;
- credential injection method and rotation owner;
- source-outage and typed-missingness behavior;
- log destination and confirmation that raw credentials/payloads are excluded;
- rollback version, configuration backup, and restore command.

Unknown or unsigned sources remain disabled. A credential never changes a rights decision.

## Five-minute onboarding test

Start the timer only after the supported Python runtime, `uv`, customer MCP client, artifact, and required configuration values are available. Stop when the client lists both tools.

The runbook must require no package-code edits and no credential copying into client-visible chat. Record:

- start/end time;
- platform, Python, `uv`, and client versions;
- artifact hash result;
- install command and exit status;
- configuration validation result;
- tool-discovery readback;
- every manual correction.

The first attempt is the metric. Fix the runbook or package when the target is missed; do not edit the timing record.

## Rollback test

1. Back up the current configuration and SQLite database using the customer-approved method.
2. Install the prior pinned wheel by exact version/artifact path.
3. Restore the prior configuration without overwriting secrets or the evidence store.
4. Restart the customer-owned MCP process.
5. Verify both tools are discoverable and make one schema-valid call.
6. Record versions, hashes, commands, outputs, and any data migration warning.

No release with a one-way schema migration may enter the initial design-partner engagement without a separately tested restore path.

## Exit checklist

- [ ] R0-R7 have evidence attached to the customer release record.
- [ ] Release artifacts and hashes match on the customer machine.
- [ ] The exact deployed source set matches the rights matrix.
- [ ] Five-minute onboarding and rollback were measured, not inferred.
- [ ] Five-ticker demo proof was regenerated from the accepted artifact.
- [ ] Customer acceptance exceptions, if any, are explicit and signed.
