# Customer Configuration Record

**Status:** Superseded historical design-partner template; non-executable. The current
self-serve motion is defined in `GTM_PLAN.md`. Retain this only as a possible future paid
deployment reference; it does not authorize interviews, prospecting, custom installation,
or counsel quote requests.

## Release and ownership

| Field | Required value |
| --- | --- |
| Customer legal entity |  |
| Environment owner |  |
| Integration owner |  |
| MCP client, version, and operating system |  |
| Python and `uv` versions |  |
| Package version, wheel hash, and sdist hash |  |
| Transport and customer process supervisor | stdio or loopback HTTP |
| Evidence-store path |  |
| Backup, retention, and deletion owner |  |
| Log destination and payload/credential exclusion review |  |
| Credential injection and rotation owner |  |
| Prior rollback version and configuration hash |  |

## Source deployment record

Attach one completed `source-rights-matrix.md` deployment row per proposed source. Record the exact source ID, endpoint, account/plan, governing terms, output/retention scope, counsel decision, registry hash, and runtime policy decision.

| Source ID | Deployment row attached | Runtime state | Reason |
| --- | --- | --- | --- |
|  | no | disabled | missing customer-specific approval |

Credentials never change `disabled` to `enabled`. The packaged generic registry is an identity/host control, not paid-deployment clearance.

## Network and data boundary

| Field | Required value |
| --- | --- |
| Permitted outbound hosts |  |
| Request/rate ceilings |  |
| Retained fields and duration |  |
| Customer-visible/exported fields |  |
| Personal data and deletion obligations |  |
| Provider support access and revocation date |  |
| Source-outage and typed-missingness acknowledgement |  |

The core MCP does not accept arbitrary documents, portfolio holdings, positions, account credentials, material nonpublic information, or personal financial data.

## Approval and hash

- Customer environment owner: `[name/date]`
- Customer integration owner: `[name/date]`
- Provider technical reviewer: `[name/date]`
- Counsel rights/privacy/security decision: `[name/date/reference]`
- Canonical secret-free configuration hash: `[sha256]`

No technical reviewer or automated system may fill customer facts, approve commercial rights, approve legal terms, or sign this record for a human owner.
