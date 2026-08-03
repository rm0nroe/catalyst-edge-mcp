# Catalyst Edge MCP Design Partner Order Form

**Status:** Superseded historical design-partner draft; non-executable. The current
self-serve motion is defined in `internal-plan`. Do not use this document for outreach,
customer discovery, signature, delivery, or counsel quote requests.

## Parties and term

- Provider: `[legal name and address]`
- Customer: `[legal name and address]`
- Effective date: `[date]`
- Engagement term: 30 calendar days from `[start date]`
- Customer environment: `[MCP client, operating system, Python, network boundary, owner]`
- Integration workflow: `[one existing agent/internal research workflow]`

## Scope

Provider will deliver the fixed package in `design-partner-package.md` for one customer-controlled environment. The accepted release exposes two read-only tools: one-ticker `catalyst_edge_score` and bounded `catalyst_edge_claim_sources` provenance pagination.

Customer, not Provider, owns ticker selection, document/list parsing, batching, scheduling, runtime administration, credential administration, retention decisions, user access, and every investment or trading decision.

Excluded services include investment advice, recommendations, fiduciary or suitability determinations, brokerage/execution, portfolio monitoring, alerts, arbitrary document ingestion, managed hosting, cloud tenancy, custom models, proven alpha, and promised returns.

## Deliverables and acceptance

- Deliverables: items 1-9 in `design-partner-package.md`.
- Acceptance criteria: A1-A8 in that document.
- Acceptance review date: `[date]`.
- Customer has `[number]` business days after receipt of complete acceptance evidence to identify a specific unmet criterion in writing.
- External-source unavailability is accepted when the response follows the signed source decision and typed-missingness contract.
- Any exception requires a written record naming the criterion, evidence, owner, remedy or acceptance, and date.

## Fees

- Fixed design-partner fee: `$[insert only after discovery validates scope and pricing]`.
- Payment schedule: `[counsel/accounting-approved schedule]`.
- Taxes and expenses: `[terms]`.
- No recurring fee, renewal, or paid continuation begins automatically.

The fee covers installation, integration, configuration, validation, and agreed support. It does not purchase exclusive ownership of the MIT-licensed code or any third-party data.

## Source and data schedule

Attach the completed per-deployment rows from `source-rights-matrix.md`. Sources not listed as approved remain disabled even if credentials are present.

- Enabled source IDs and governing terms: `[attachment]`
- Customer-supplied accounts/entitlements: `[attachment]`
- Retained fields and duration: `[attachment]`
- Evidence-store location, backup owner, and deletion owner: `[attachment]`
- Permitted output users/export: `[attachment]`
- Credential injection and rotation owner: `[attachment]`
- Outbound hosts and rate limits: `[attachment]`

Customer will not submit personal financial information, portfolio holdings, positions, account credentials, material nonpublic information, or arbitrary documents through the core MCP.

## Security and confidentiality

- Credentials remain in the customer-controlled process environment and are not returned in tool output.
- Provider access, if any, is time-bounded, least-privileged, logged by Customer, and revoked at engagement end.
- Each party protects the other's confidential information under `[counsel-approved confidentiality terms]`.
- Incident notice, security standard, subprocessors, cross-border transfer, and data-processing terms: `[counsel to determine from actual deployment]`.

## Support, updates, and rollback

- Included support: up to eight hours during the term on business days.
- Initial response target: one business day; no uptime or 24/7 service level.
- Included patch: one reproducible acceptance-defect patch.
- Releases remain pinned; no automatic feature update.
- Customer may restore the prior pinned release using the agreed rollback procedure without deleting the evidence store.
- Work beyond the included boundary requires a signed change order or separate agreement.

## Product and financial limitations

Output is deterministic, unbacktested research evidence with explicit confidence and missingness. It is not a recommendation, prediction, warranty of accuracy/completeness, or promise of performance. Customer independently verifies sources and remains solely responsible for investment, trading, compliance, and risk decisions.

`[Counsel must determine regulatory status, required disclosures, warranty disclaimer, limitation of liability, indemnity, governing law, dispute process, insurance, and any professional-services terms. A disclaimer alone is not the regulatory analysis.]`

## Intellectual property

- Catalyst Edge code is provided under its MIT license.
- Customer retains ownership of its environment, configuration, credentials, workflow, and data.
- Third-party data/content remains subject to its own rights and is not licensed by the MIT license.
- Customer-specific integration work and feedback treatment: `[counsel-approved terms]`.

## Completion and continuation

The engagement completes upon A1-A8 acceptance or written acceptance of named exceptions. Continued code use under MIT is independent of support. Any later support, update, new integration, hosted operation, or source expansion requires a new written scope, term, price, rights review, and signatures.

## Required approvals before use

- [ ] Provider commercial owner approves scope and price.
- [ ] Customer environment and integration owners approve the operating boundary.
- [ ] Every enabled source row is complete and counsel-approved.
- [ ] Privacy/security schedule matches the actual data flow.
- [ ] Securities/regulatory counsel approves the offer and disclosures.
- [ ] General commercial counsel approves the complete agreement.
- [ ] Release candidate passes R0-R7.
- [ ] Final document contains no brackets, draft labels, or unresolved attachments.
