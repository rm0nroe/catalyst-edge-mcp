# Catalyst Edge MCP Design Partner Package

**Status:** Commercial package baseline; customer-specific price, sources, environment, and terms remain open until discovery and counsel review.

## Outcome

The 30-day engagement ends with one versioned Catalyst Edge MCP release installed in one customer-controlled environment and integrated into one existing agent or internal research workflow. The customer can invoke one ticker at a time, inspect a compact dossier, recover every source counted by one grouped claim, and recognize explicit missing or rejected data.

The engagement does not promise alpha, returns, recommendations, monitoring, alerts, arbitrary document ingestion, MCP-owned batching, cloud hosting, or brokerage execution.

## Included deliverables

1. One kickoff session covering the customer MCP client, runtime owner, security constraints, ticker-selection handoff, and permitted source set.
2. One versioned wheel and source distribution, SHA-256 manifest, release notes, and installation command for the customer-controlled environment.
3. Configuration of only the sources approved in the signed deployment rights record. Credentials remain customer-controlled and process-local.
4. Integration of `catalyst_edge_score` and `catalyst_edge_claim_sources` into one customer workflow.
5. A demonstration using exactly five customer-selected tickers and one invocation per ticker.
6. Joint review of one complete dossier, every page of one claim's source records, and one missing or rejected-data case.
7. Customer-specific installation, configuration, operating, troubleshooting, and rollback instructions.
8. Up to eight founder support hours during the 30-day term, scheduled on business days. This is an initial packaging hypothesis to validate, not a service-level agreement.
9. One in-scope patch release for a reproducible acceptance defect. New sources, workflows, transports, and features require a change order or later engagement.

## Ownership and operating boundary

| Area | Customer | Provider |
| --- | --- | --- |
| MCP host, client, network, device, and user access | Owns and administers | Receives only agreed access needed for installation/support |
| Source accounts, credentials, and entitlements | Owns or supplies; confirms permitted use | Never resells credentials or assumes a key grants rights |
| Ticker selection, list parsing, batching, and scheduling | Owns | Not part of the MCP contract |
| Local evidence store and output retention | Owns and configures under agreed policy | Documents behavior; does not receive data by default |
| Catalyst Edge code | Receives under MIT license | Retains no exclusive rights over the customer environment or data |
| Investment and trading decisions | Solely owns | Provides no recommendation, execution, fiduciary service, or suitability determination |

## Entry conditions

Work starts only when all are true:

- The customer identifies the environment owner and integration owner.
- The customer supplies five valid public-company tickers; no portfolio holdings, positions, risk limits, or personal financial data are required.
- Every enabled source has a completed deployment rights row in `source-rights-matrix.md`.
- The customer and provider approve the data-flow, retention, credential, and support-access boundary.
- A release candidate has passed every required gate in `release-readiness-plan.md`.
- Counsel-approved terms, price, and signatures are complete.

## Acceptance criteria

Acceptance is evidence-based and limited to the installed version and agreed environment.

| ID | Criterion | Proof |
| --- | --- | --- |
| A1 | The delivered wheel and source distribution match the signed SHA-256 manifest and declared version. | Customer-side hash check and `importlib.metadata.version("catalyst-edge-mcp")` |
| A2 | A clean supported Python environment installs the release by following the customer runbook. | Timed screen share or terminal transcript; target is five minutes after prerequisites are present |
| A3 | The customer's MCP client discovers exactly `catalyst_edge_score` and `catalyst_edge_claim_sources`. | Client tool-list readback |
| A4 | Five customer-selected tickers each produce one schema-valid response from a separate `catalyst_edge_score` invocation. | Five retained response files and manifest |
| A5 | The customer can identify score method, model status, coverage, warnings, evidence, and next checks in one selected dossier. | Review checklist signed or acknowledged in writing |
| A6 | One claim ID is queried until `next_cursor` is null, and the union of returned source records equals `total_sources` without duplicate source-reference IDs. | Claim-page files plus automated manifest check |
| A7 | At least one dossier displays a typed missing family or retained rejection reason without converting it into directional evidence. | Demo manifest identifies ticker, family/reason, and response path |
| A8 | Customer can restore the prior pinned release and its prior configuration without deleting the evidence store. | Rollback transcript and post-rollback tool discovery |

An unavailable external source is not a product defect when the response follows the agreed typed-missingness behavior. A schema, provenance, security, or fail-closed-policy regression is a defect.

## Support and change boundary

- Support window: the 30-day term, business days, by scheduled call or agreed written channel.
- Initial response target: one business day; no 24/7 monitoring or uptime commitment.
- Included: installation, configuration, reproduction, one agreed integration, and one acceptance-defect patch.
- Excluded: source procurement, legal opinions, customer security administration, new adapters, hosted operation, custom scoring, trading logic, batch/watchlist orchestration, and ongoing analyst work.
- Customer changes to Python, MCP client, registry, network, source plan, credentials, or workflow after acceptance require revalidation and may move the work out of scope.

## Release update and rollback policy

- The accepted release stays pinned for the engagement.
- Security or acceptance-defect updates are proposed with release notes, hashes, migration notes, and rollback steps; the customer chooses when to install.
- Feature updates are not applied automatically.
- The prior wheel, configuration, and database backup remain available until the new version passes A1-A8.
- Rollback changes the package/configuration pointer; it does not delete the customer evidence store. Any incompatible migration requires an explicit backup and restore test before delivery.

## Completion and paid continuation

The engagement completes when A1-A8 pass or the customer accepts documented exceptions in writing. Failure to clear an entry condition pauses the schedule rather than silently reducing the acceptance boundary.

No recurring obligation starts automatically. A separate paid continuation requires a defined support-hour allowance, release-update policy, additional integration scope if any, term, price, and signatures. Continued use of the MIT-licensed code does not itself require a support subscription.
