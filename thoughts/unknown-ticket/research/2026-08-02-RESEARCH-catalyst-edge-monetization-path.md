---
date: 2026-08-02T19:11:20-04:00
researcher: ryanmonroe
git_commit: 36730391ad124cff82bcf6aaa346dc0e93248813
branch: codex/dynamic-market-universe-tdd
repository: catalyst-edge-mcp
topic: "Which 90-day monetization path should Catalyst Edge take: private paid installation, public open source, staged hybrid, or another model?"
tags: [research, catalyst-edge, monetization, mcp, open-source, product-led, self-serve]
status: complete
decision_status: approved-builder-first-product-led-no-interviews
last_updated: 2026-08-02
last_updated_by: ryanmonroe
---

# Research: Catalyst Edge monetization path

**Decision status:** approved builder-first product-led direction; no interviews or
counsel quote requests

**As of:** 2026-08-02

> **Current answer:** See [Follow-up reevaluation: broad self-serve path](#follow-up-reevaluation-broad-self-serve-path).
> The institutional analysis retained above that section is historical and must not be
> executed.

## Research question

For the next 90 days, which path offers the best evidence-backed balance of revenue
potential, learning speed, defensibility, and Ryan's long-term brand/options: (A) private
paid design-partner installation, (B) public open-source release monetized through
integration/support, (C) a staged hybrid, (D) a hosted remote product, or (E) a neutral
evidence-verification integration?

## Prior recommendation — superseded by the follow-up reevaluation below

Choose **C: a gated hybrid**. Use **A as the first commercial stage** and **E only as the
counsel-directed fallback**.

| Stage | Decision |
| --- | --- |
| **Now** | Test a legally and operationally tightened 30-day customer-installed **private pilot**. Do not publish, upload the full MCP to PyPI, submit to the MCP Registry, or build hosting. |
| **Gate** | Require counsel-cleared output, executable source controls, one accepted integration, and two artifact-specific buyer requests for the proposed public bundle. |
| **Then** | If the gate passes, separately authorize a bounded MIT-licensed **proof repository**. If it fails, remain private; the outcome is A, not a hybrid. |

The proof repository means schemas, synthetic fixtures, sample dossiers, and an offline
acceptance/provenance verifier. It excludes live collectors, source credentials, customer
configuration, the full MCP server, source policy, and directional scoring. The paid
private pilot supplies the complete customer-installed release, deployment policy,
integration, validation, updates, and support.

The current [`GTM_PLAN.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/GTM_PLAN.md#L45-L60)
should be **amended, not replaced**. Its customer-installed offer, workflow integration,
five-ticker acceptance, support boundary, and demand metrics remain directionally right.
Its 30-day sales sequence is not ready to execute because two load-bearing gates are
understated:

1. **Adviser-status counsel review must precede paid ticker-specific delivery.** SEC
   IA-1092 says regular reports or analyses about specific
   securities and a clearly definable charge—including one embedded in an overall
   service fee—can satisfy the business and compensation elements of the
   investment-adviser definition. Catalyst currently emits ticker-specific score, direction,
   confidence, and horizon. A disclaimer and customer installation do not create a safe
   harbor. Counsel must determine whether the paid offer can retain those fields or must
   become an objective evidence/provenance/missingness tool. The internal operating
   policy is more conservative than the cited authority: until counsel responds, use
   problem interviews and sanitized/historical demonstrations rather than live
   customer-selected tickers. [SEC IA-1092](https://www.sec.gov/files/rules/interp/1987/ia-1092.pdf),
   [SEC Hendricks letter](https://www.sec.gov/divisions/investment/noaction/2015/jonathon-hendricks-012615-202a.htm)
2. **Commercial source policy must fail closed in executable configuration.** The
   customer runbook disables issuer feeds, GDELT, and Bluesky, but runtime defaults and
   `.env.example` enable all three, while the static policy marks them
   production-allowed. A missing environment override can therefore cross the documented
   commercial boundary. See
   [`.env.example`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/.env.example#L18-L24),
   [`settings.py`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/catalyst_edge_mcp/settings.py#L119-L158),
   [`source_policy.py`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/catalyst_edge_mcp/source_policy.py#L24-L76),
   and the
   [customer runbook](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/docs/demo/customer-installation-runbook.md#L29-L59).

This preserves the portfolio strategy's public proof, commercial control, and protected
customer/environment advantage without treating publication as near-term demand evidence.

## Executive evidence

### Product readiness

- The product is a customer-run local MCP with two non-transactional tools that do not
  place trades or mutate upstream customer systems; the runtime can make documented
  network requests and write local evidence/cache/state. It accepts one ticker per score
  call and returns deterministic unbacktested scoring, typed missingness, and exact
  claim-source pagination. It does not implement holdings/portfolio personalization,
  execution, hosting, billing, tenancy, alerts, or batching. Documentation labels the
  output non-advisory, but its legal characterization is unresolved.
  [`GTM_PLAN.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/GTM_PLAN.md#L14-L32)
- PR #8 merged to private `main` at
  [`987710a`](https://github.com/rm0nroe/catalyst-edge-mcp/commit/987710a17f2ea911435069dfbe6d982c10f77600),
  with Python 3.10, Python 3.14, and installed-artifact checks passing. The repository
  remains private; there is no tag, GitHub release, PyPI project, or MCP Registry entry.
- RC 0.1.1 proves reproducible wheel/sdist builds, exact two-tool discovery, a
  2.679-second local SDK onboarding, five calls, complete claim pagination, typed missingness,
  and state-preserving rollback. It does not prove customer value, source rights,
  pricing, or delivery authority.
  [RC record](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/docs/validation/release-candidate-0.1.1-2026-08-02.md#L15-L34)

### Market evidence

- Quartr now sells an MCP included with Quartr Pro, covering first-party material from
  15,000+ companies across 65+ markets; every query uses first-party IR data, and the
  offering is sales-led. [Quartr MCP](https://quartr.com/mcp)
- Fiscal.ai exposes a finance MCP plus agent skills including news/event workflows and
  filing audit links. Its free API tier currently covers 45 companies and 250 calls/day,
  making it a low-friction substitute inside that bounded use case.
  [Fiscal MCP](https://docs.fiscal.ai/docs/guides/mcp-integration),
  [Fiscal skills](https://docs.fiscal.ai/docs/guides/mcp-skills),
  [Fiscal free limits](https://docs.fiscal.ai/docs/guides/free-trial)
- Daloopa's institutional MCP is read-only, OAuth-protected, covers 6,000+ tickers, and
  links datapoints to source filings, releases, presentations, or transcripts.
  [Daloopa MCP](https://www.daloopa.com/products/mcp)
- OpenBB separates an open-source data platform from a proprietary enterprise
  workspace. Its self-hosted Lite tier is currently listed at $2,400/year for a team
  ($1,200 promotion through August 31), while Pro uses custom pricing; paid tiers add
  deployment, RBAC, audit, support, and services. [OpenBB pricing](https://openbb.co/pricing/)
- AlphaSense uses annual, sales-led subscriptions and competes on broad premium content,
  enterprise security, exact-source citations, and professional services rather than a
  protocol wrapper. [AlphaSense pricing](https://www.alpha-sense.com/pricing/)
- The official MCP Registry is a preview metadata index, not a package host or payment
  channel. Private-only servers are ineligible; host applications are expected to use
  downstream aggregators; versions are immutable and entries currently cannot be
  unpublished; code scanning is delegated to package registries and aggregators. No
  registry-to-install or paid-conversion metrics were found in the reviewed official
  materials as of 2026-08-02. [Registry overview](https://modelcontextprotocol.io/registry/about),
  [aggregator guide](https://modelcontextprotocol.io/registry/registry-aggregators),
  [Registry FAQ](https://modelcontextprotocol.io/registry/faq)

### Legal and source constraints

- SEC.gov information may be copied or further distributed, subject to fair-access,
  identity, attribution, and trademark limits. Automated access is capped at 10
  aggregate requests per second. [SEC privacy policy](https://www.sec.gov/about/privacy-information),
  [SEC developer resources](https://www.sec.gov/about/developer-resources)
- The current GDELT source-rights row is a candidate for relaxation. GDELT Project says all
  released datasets are available for unlimited academic, commercial, or governmental
  use and may be redistributed if use includes a GDELT citation and link.
  [GDELT terms](https://www.gdeltproject.org/about.html#termsofuse)
- GDELT's permission does not grant rights to reproduce underlying publisher articles.
  The current implementation's metadata/title/link/hash and derived-decision boundary
  should remain. Before changing the production row, document which Web NGrams fields
  are stored, displayed, hashed, or discarded; add required attribution; and obtain
  counsel or source-owner confirmation for the exact fields and output.
- Apple restricts commercial copying/distribution and automated scraping without
  permission. Bluesky users retain their content, and the reviewed terms do not provide
  a blanket downstream commercial-content license. Those sources remain disabled for
  paid use absent written/counsel approval. [Apple terms](https://www.apple.com/legal/internet-services/terms/site.html),
  [Bluesky terms](https://bsky.social/about/support/tos)

#### GDELT field-level gate

The current Web NGrams implementation creates the following field-level rights gate. It
is a code trace, not a legal conclusion:

| Input or derived field | Current handling | Potential customer output | Commercial gate |
| --- | --- | --- | --- |
| NGram document ID | Used to join NGram matches to the TOC; stored in the entity-match audit | Not displayed as publisher content | Confirm GDELT attribution and derived-record use |
| NGram matched phrase/context | Used for entity matching; only hashes, rule IDs, matched aliases, and reason codes persist | Derived decision/audit only | Do not expose the publisher-body context; confirm derived audit use |
| TOC `title` | Normalized for matching and stored, capped at 240 characters | May appear as the event title | Confirm this exact metadata display and attribution; suppress if not cleared |
| TOC `url` | Validated, canonicalized, and stored as record/source URL | Publisher link and source reference | Link only; do not fetch or reproduce the article body |
| TOC `date` | Parsed and stored as publication time | Event/source timestamp | Confirm metadata use |
| Raw TOC line | Hashed for provenance; the content itself is not stored | SHA-256 only | Keep hash-only boundary |
| Other TOC fields and article body | Ignored/not fetched by this adapter | None | Keep discarded/excluded |

[`gdelt_web_ngrams.py`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/catalyst_edge_mcp/gdelt_web_ngrams.py#L278-L389)
is the implementation source for this table.

### Security and procurement gaps

- The release pack has artifact hashes and package-content checks, but no tracked SBOM,
  dependency-license report, `SECURITY.md`, vulnerability-disclosure process, or
  dependency-vulnerability evidence. The customer install command can resolve
  dependencies from an external index rather than from a signed offline wheelhouse.

### Inferences

- The market validates source-linked finance workflows, but MCP access, source links,
  and generic event summaries are already table stakes. Catalyst's near-term paid value
  is customer-specific control: approved sources, deterministic evidence policy,
  explicit missingness, installation, workflow integration, acceptance proof, rollback,
  and support.
- A full public open-source release would improve inspectability and possibly Ryan's
  developer brand, but it would enter a crowded category before the product has buyer
  evidence or a commercial control layer. The MIT license also means a private customer
  receiving the source distribution is paying for service and outcomes, not exclusive
  code access.
- Customer installation reduces hosting, tenancy, uptime, and custody burdens only if
  Ryan receives no customer credentials, portfolios, positions, evidence stores, logs,
  or standing remote access. It does not eliminate software-vendor diligence or
  adviser-status analysis.
- OpenBB is the strongest structural precedent for a hybrid, but not proof that Catalyst
  will convert public users. The proof repository must be tied to qualified institutional
  conversations and paid continuation, not stars, downloads, or Registry inclusion.
- Large open-core businesses prove coexistence, not Catalyst conversion:
  - Elastic reported FY2026 subscription-led revenue across self-managed and cloud
    products. [Elastic 2026 10-K](https://www.sec.gov/Archives/edgar/data/1707753/000170775326000018/estc-20260430.htm)
  - GitLab separates free individual-contributor features from paid manager/enterprise
    features. [GitLab 2026 10-K](https://www.sec.gov/Archives/edgar/data/1653482/000162828026018731/gtlb-20260131.htm)
  - PostHog says open source accelerated adoption, but self-hosted support consumed
    substantial engineering time. [PostHog](https://newsletter.posthog.com/p/the-hidden-benefits-of-being-an-open)
  - Supabase's 2026 builder survey found only a self-reported, non-causal association
    between developer community and customer sourcing from open-source users.
    [Supabase State of Startups 2026](https://supabase.com/state-of-startups)
- A hosted remote MCP could eventually support public discovery without open-sourcing
  the engine, but it requires auth, entitlement, tenancy, metering, billing,
  observability, incident ownership, and a larger legal/data-rights surface. It is not a
  90-day revenue optimization for this implementation.

### Unknowns that only market or professional evidence can resolve

- Whether the current paid ticker-specific output is investment-adviser activity, an
  excluded publication, or software/data infrastructure under federal and applicable
  state law.
- Whether score, direction, confidence, and horizon can remain in a paid offer.
- Which named buyer has a sufficiently painful evidence-verification step, an owned MCP
  environment, and budget for integration.
- Actual installation/support hours, legal cost, source cost, gross-margin floor, sales
  cycle, willingness to pay, repeat use, and paid continuation.
- Whether the proof repository materially improves institutional procurement or mainly
  attracts developers who will not buy services.
- Registry traffic, install conversion, qualified-lead conversion, and support burden.

## Decision comparison

No path can be shown to maximize expected revenue: there is no observed Catalyst close
rate, price, delivery cost, sales cycle, or paid retention. The comparison therefore
separates 90-day cash/learning from long-term option value and names the evidence that
would change the decision.

Commercial comparison:

| Path | 90-day cash/learning | Main downside | Decision |
| --- | --- | --- | --- |
| A. Private pilot | Fastest paid-workflow test after clearance | Legal/vendor review; founder-led delivery | **First commercial stage** |
| B. Full public OSS | Fast adoption test; weak revenue test | Irreversible publication and maintainer burden | **Reject for first 90 days** |
| C. Gated hybrid | A's private test, then measured public acquisition | More work; public users may not buy | **Recommended, conditional** |
| D. Hosted MCP | Platform work precedes buyer learning | Auth, tenancy, billing, uptime, custody | **Defer** |
| E. Neutral integration | Unknown until separate path is estimated | Unclear buyer value and legal treatment | **Counsel fallback; not assumed safe** |

Option and evidence comparison:

| Path | Long-term option | Evidence required to advance |
| --- | --- | --- |
| A | Integration/support business | Cleared output, cost floor, order, repeat use |
| B | Developer reach and possible paid funnel | Proof that full public inspection is required |
| C | Brand compounding plus paid control | One accepted integration and two artifact-specific requests |
| D | Recurring hosted access | Repeated hosting demand and willingness to pay |
| E | Lower-claim integration model | Counsel comparison, engineering estimate, buyer usefulness |

Decision gate:

1. If counsel clears A's current semantics, test A privately.
2. If counsel rejects A but identifies a viable neutral output, estimate and test E without
   broadening the implemented source/workflow boundary.
3. If neither is clearable, stop paid delivery.
4. If one private integration is accepted and at least two of four qualified demo buyers
   confirm that specific artifacts in the proposed proof repository satisfy a named
   procurement requirement, execute C's proof repository. Otherwise remain on A/E
   and keep distribution private.

### A. Private paid design-partner installation

Best near-term revenue mechanism, but not yet offer-ready. It maximizes learning from a
real workflow and lets every source, environment, and acceptance criterion be bounded.
Its weaknesses are founder-led acquisition, vendor diligence, legal exposure tied to
paid ticker analysis, and minimal public brand compounding.

**Retain:** customer-controlled environment, exact two-tool scope, five-ticker proof,
claim pagination, typed missingness, rollback, eight-hour support cap, and one acceptance
patch.

**Amend:** legal review before live customer-ticker demos; SEC+GDELT candidate baseline;
commercial fail-closed mode; security/procurement pack; evidence-based price test; no
promise that current directional fields survive counsel review.

### B. Full public open-source package now

Weakest revenue path. It creates inspectability and brand reach but makes publication
irreversible, introduces package security and community-support obligations, and exposes
an MIT implementation before demand or paid control layers exist. Free/low-cost finance
MCPs already cover much of the generic outcome. Registry presence is metadata, not
demand evidence.

Do not choose B in the first 90 days.

### C. Gated hybrid

Best balance. Stage A privately validates the expensive truth: whether a buyer will pay
for the controlled integration and use it repeatedly. A later proof repository compounds
brand and can reduce buyer fear without immediately releasing the complete package.

The proof repository should initially contain:

- an MIT license and explicit community-versus-paid support boundary;
- a sanitized or synthetic five-ticker evidence pack;
- JSON schemas and exact output semantics;
- an offline acceptance and provenance verifier;
- a technical architecture/security note and explicit limitations;
- a case study only with customer permission and bounded claims.

It must exclude live collectors, source policy, customer configuration, the full MCP
server, and directional scoring. A public connector, remote endpoint, full PyPI package,
or Registry listing remains a separate next-quarter decision.

### D. Hosted remote MCP

Potentially higher recurring value but a poor 90-day choice. It adds authentication,
tenant isolation, metering, billing, incident response, uptime, data handling, and
source-redistribution obligations before buyer demand is known. It also moves away from
the product's strongest current control—customer-local execution.

### E. Neutral evidence-verification integration

This option would preserve ticker-in evidence collection, exact source recovery, typed
missingness, and next checks while suppressing score, direction, confidence, and horizon
if counsel requires that boundary. It may reduce claim and buyer-risk exposure, but it is
not a legal safe harbor: it still produces ticker-specific analysis for compensation.
It requires a separate tool, response schema, and non-scoring service path; it cannot
reuse the current score contract unchanged. The effort is unestimated. See
**Appendix: E engineering delta**.

## Minimum viable commercial offer

**Name:** Catalyst Edge Evidence Integration — Design Partner

**Term and scope:**

- 30 days; one customer-controlled environment; one existing agent/research workflow.
- `stdio` by default; loopback HTTP only when the customer owns the supervisor and
  accepts the boundary.
- A exposes exactly `catalyst_edge_score` and `catalyst_edge_claim_sources` if counsel
  clears the current fields. E instead exposes the separately implemented
  `catalyst_edge_evidence` and `catalyst_edge_claim_sources`; it does not relabel the
  current score response.
- Five public-company tickers, one invocation per ticker; no holdings, positions,
  portfolios, personal financial data, or arbitrary documents.
- **Source policy:**
  - default candidates: SEC and GDELT metadata/derived decisions, with GDELT attribution
    and completed deployment rows;
  - disabled by default: every other source;
  - approval requirement: the executable deployment record cites contract terms or
    source-owner permission covering automated access, storage/cache, transformation,
    derived output, customer display or redistribution, vendor-assisted operation, and
    retention/deletion as applicable; counsel approves the exact use/output.
- Customer owns runtime, credentials, evidence store, access, retention, and investment
  decisions. Ryan receives no standing access or customer data by default.
- Deliver artifact/hashes, signed dependency manifest or wheelhouse, configuration,
  workflow integration, dossier/provenance/missingness acceptance, rollback, up to eight
  support hours, and one acceptance-defect patch.
- No holdings/portfolio personalization, managed monitoring, alerts, execution, hosting,
  suitability decision, guaranteed completeness, or performance claim. Any
  customer-facing statement that the output is “not advice” or “not a recommendation” remains
  counsel-controlled draft language until the legal classification is resolved.

**Entry gate:** counsel memo, corrected source record, executable fail-closed commercial
configuration, counsel-language gate, security pack, actual cost inputs, owner-set quote,
agreement, and signatures. The language gate covers MCP instructions, tool descriptions,
README, generated schemas/output, runbooks, and order forms.

## Pricing-test method

No verified public comparable supports a fixed Catalyst pilot price. Do not reuse the
former $5,000 pilot or $3,000/month assumptions, and do not infer a fee from build effort.

1. Fill the existing cost sheet from one named environment: discovery, install,
   validation, support, patch reserve, legal allocation, source cost, payment fees, and
   contingency.
2. Compute `cash_break_even_price` and `target_margin_price` exactly as defined in
   [`design-partner-pricing-decision.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/docs/commercial/design-partner-pricing-decision.md#L17-L38).
3. Run an owner-approved experiment across two consecutive cohorts of two qualified
   buyers. Hold the fixed scope and `target_margin_price` constant across all four; do
   not treat this small sample as a market estimate or vary price mid-cohort.
4. Record budget authority, procurement delay, no-decision, scope objection,
   incumbent-tool objection, and explicit price objection separately. “Too expensive” counts as
   price evidence only when the buyer otherwise accepts the scope, timing, authority,
   source, and security boundary.
5. After four completed quote outcomes, set the next experiment from actual delivery
   cost and objections. Scope down before discounting and never quote below cash
   break-even without an explicit owner decision documenting why.
6. If the first accepted installation reveals that the fixed price is below actual cash
   break-even, terminate the current cohort before issuing remaining quotes. Preserve
   completed outcomes as directional evidence, recalculate scope and price, and begin a
   new fixed-scope/fixed-price cohort; do not silently change terms inside one cohort.
7. Record the buyer's existing manual step, time/cost, environment, source entitlement,
   support expectation, exact objection, and signature outcome.
8. Count only a signed paid order as willingness-to-pay evidence. Count only paid
   continuation or expansion as recurring-demand evidence.

OpenBB's $2,400/year self-hosted team product is a comparison point, not a Catalyst price
ceiling or floor: Catalyst is currently a fixed integration service, while OpenBB is a
broader software platform with separate implementation services.

## Provisional ICP and cohort ledger

Recommendation confidence is **conditional and low until buyer interviews occur**.
Competitor supply validates a category, not Catalyst demand.

Provisional ICP:

- a small public-equity research team, research-technology consultancy, or technical
  founder with an existing or actively funded agentic research workflow;
- a research-technology owner who owns the current evidence-verification step and can
  name its time, error, or provenance cost;
- an identified MCP/runtime owner, budget path, source-entitlement owner, and desired
  decision inside 90 days;
- disqualified if the buyer wants proven alpha, recommendations, portfolio-specific
  output, execution, a managed watchlist, unapproved sources, or has no installation and
  budget owner.

Cohort definitions and schedule:

| Term | Operational definition |
| --- | --- |
| Problem interview | No Catalyst output or customer ticker is shown; the buyer describes the current workflow, pain, incumbent tools, authority, environment, entitlements, procurement, and timing. |
| Qualified conversation | The record identifies role, real workflow/pain, environment owner, budget path, source owner, 90-day urgency, and no disqualifier. |
| Complete demo | After counsel clearance, the approved A or E SKU runs the full five-ticker acceptance flow on counsel-approved sanitized, historical, or customer-selected inputs. |
| Material proof-bundle request | The buyer names a procurement requirement and confirms which specific proposed artifact—schemas, synthetic evidence pack, offline acceptance/provenance verifier, or architecture/security note—would satisfy it. Generic source/code inspectability or a request for excluded collectors, source policy, scorer, or full server does not pass. |
| Repeat use | The installed tool is invoked in the real workflow on at least two separate business days within a 14-day observation window. This is an operating hypothesis, not a benchmark. |
| Proof-repository attribution | The buyer identifies the proof repository as a discovery or trust input, recorded in the cohort ledger with its referring URL/source. |

Run one bounded founder-sales cohort: eight problem interviews in days 0–30; up to four
counsel-cleared complete demos from qualified participants; two fixed-scope quotes in
days 31–60; and the remaining two quotes in days 61–90. These counts are a
work-in-progress limit and stop rule, not statistically representative market thresholds.

Institutional timing is uncertain. FINRA guidance shows that regulated buyers may review
vendor financial condition, security, resilience, contracts, incident notice, data
disposition, and ongoing supervision; OpenBB says its enterprise deployments typically
take one to four weeks depending on integration and training. These support targeting a
small research-technology buyer first but do not prove Catalyst can close in 60 or 90
days. Treat dates below as controllable process goals with outcome ranges, not revenue
commitments. [FINRA Regulatory Notice 21-29](https://www.finra.org/rules-guidance/notices/21-29),
[OpenBB support/services](https://docs.openbb.co/workspace/getting-started/enterprise/support-services)

## 30/60/90-day sequence

Every customer-facing step, publication, purchase, or counsel engagement remains subject
to separate owner authorization.

### Days 0–30: clear the offer and test the problem

This capacity model is a planning assumption, not observed delivery data. It assumes one
owner; outside-counsel turnaround is elapsed time.

| Workstream | Action and gate | Owner hours | Output |
| --- | --- | ---: | --- |
| **P0 Discovery** | After batch authorization, run eight no-demo problem interviews; show no Catalyst output and request no customer ticker. | 16–24 | Cohort ledger and early demand result |
| **P0 Counsel** | Request two or three quotes. After four interviews, commission only if two are qualified and two name a costly evidence/provenance step. Scope A versus E, IA-1092, publisher exclusion, federal/state registration, and demo inputs. | 6–10 | Selected brief/memo or documented no-spend stop |
| **P0 Rights/design** | Complete the GDELT field/output and attribution record; trace A/E and commercial-mode requirements. Do not relax policy without counsel/source-owner confirmation. | 12–20 | Approved source-operation record and implementation boundary |
| **P0 Commercial mode** | Fail closed without an approved deployment record. Gate instructions, tool descriptions, schemas, docs, and generated output on counsel-approved language. | 16–28 | Tested A mode; configuration-only tests if counsel is unresolved |
| **P1 Security** | Build the baseline SBOM, license inventory, vulnerability policy/evidence, security contact, egress manifest, sandbox guide, and signed/offline dependency set. | 16–28 | Baseline procurement pack; defer buyer-specific artifacts if P0 consumes month |
| **P1 Offer/demo** | Fill the cost sheet and quote template; privately prepare sanitized demo and proof materials. Run up to four qualified demos only after counsel clears the format. | 12–20 | Cost floor, quote template, and up to four demo records |

The range is **78–130 owner hours**, so completing every item is not the day-30 promise.
The critical path is four interviews → demand threshold → memo → A/E decision → executable
commercial mode → demo. P0 consumes available capacity first. If interview scheduling or
counsel consumes the month, P1 security depth, demo execution, and proof-bundle work move
to days 31–60; no revenue or publication milestone is pulled forward to compensate.

**Day-30 expected range:** zero signed orders. Controllable evidence is eight completed
problem interviews, a scoped counsel quote and preferably a completed or active memo,
one technically specified A/E boundary, and draft fail-closed/security artifacts. A
longer counsel or buyer-security review is a timing observation, not a failed demand
test. No publication metric counts.

### Days 31–60: close and deliver one paid integration

1. If and only if counsel and the technical/rights gates clear a paid offer, send the first
   two identical-scope, evidence-based quotes to qualified participants.
2. Close no more than one first design partner until support load is known.
3. Install in one customer-controlled environment and retain A1–A8 acceptance evidence.
4. Measure install time, time to first call, provenance verification, dossier and
   missingness usefulness, repeat use, defects, support hours, and paid-continuation
   intent.
5. Record whether a specific artifact in the proposed proof repository satisfies a named
   procurement requirement. Keep the repository/package private through this window.

**Day-60 expected range:** zero or one paid integration. One accepted integration with
support within eight hours, no rights/security exception, and repeat workflow use is the
positive outcome. Zero while a documented legal, security, or procurement review is
active is unresolved; zero after both quote recipients reject or abandon the same value
proposition is negative evidence. A signed order without use is not enough.

### Days 61–90: validate repeatability and earn public distribution

1. Send the remaining two cohort quotes. Pursue a second independent paid partner only
   if the first delivery, if any, stayed in scope.
2. Ask for paid continuation or a defined expansion; do not create recurring obligations
   automatically.
3. Publish the bounded proof repository only if separately authorized, the legal/security
   gates are clear, at least one integration was accepted, and at least two of the four
   complete demos produced a material proof-bundle request for artifacts the proposed
   repository would actually contain. If those conditions fail, remain private; this is
   A, not a failed hybrid.
4. Re-evaluate full PyPI/MCP Registry distribution only after two independent paid
   integrations or strong contrary evidence that public code is the required acquisition
   wedge.
5. Choose one path for the next quarter: private integration business, public-core plus
   paid control layer, or stop.

**Day-90 expected range:** zero to two paid integrations. The strongest result is two, or
one plus paid continuation, with measured support economics. One accepted integration
still resolves delivery economics and the proof-repository gate. Zero is interpreted using
the staged demand criteria below, not labeled failure solely because enterprise review
exceeded 90 days.

## Kill and pivot criteria

- **Legal:** if counsel cannot clear a bounded paid offer, stop paid ticker analysis. Pivot
  only if counsel defines a neutral evidence/provenance product that fits the implemented
  boundary; do not rely on disclaimers.
- **Rights:** if SEC+GDELT cannot be cleared or the cleared output is not useful, stop the
  pilot rather than enable uncertain sources.
- **Problem demand:** after eight problem interviews, fewer than four qualified
  conversations or a majority unable to name a costly evidence/provenance step stops the
  cohort before demos and counsel-dependent product expansion.
- **Offer demand:** after up to four complete demos, zero quote request or champion-owned
  next step, combined with a majority saying existing tools already solve the workflow,
  kills the current offer. Active documented procurement is unresolved, not a win.
- **Use:** an accepted install that is not used repeatedly in the customer's real workflow
  does not justify continuation or a public release.
- **Economics:** delivery above eight support hours, an acceptance patch that becomes
  custom product work, or price below cash break-even triggers scope reduction or stop.
- **Differentiation:** if buyers value Quartr/Fiscal/OpenBB data breadth but not Catalyst's
  policy, missingness, provenance, or rollback, do not chase breadth with unlicensed
  adapters; reposition or stop.
- **Proof repository:** interpret the 30-day result only after six qualified buyers have
  received and acknowledged the exact repository link, including two outside the demo
  cohort. Six is a work limit, not a conversion benchmark. If that exposure produces
  zero attributable qualified conversations and no existing buyer reports reduced
  diligence, stop further OSS/Registry investment. If the denominator is not reached,
  classify the result as inconclusive; do not expand or terminate from it.
- **Registry:** downloads, stars, and listings without successful use and qualified buyer
  attribution do not justify continued public-maintainer burden.

## Smallest next actions

- **Reversible learning:** after owner authorization, run no-demo problem interviews and
  request two or three counsel quotes against one memo brief in parallel.
- **First paid action:** if the four-interview threshold passes, commission the selected
  tightly scoped memo.
- **First market commitment:** after legal, technical, rights, and security gates, send
  one owner-approved fixed-scope quote to a qualified buyer.
- **First distribution commitment:** sign one SEC+GDELT private pilot; do not publish
  first.

No counsel engagement, outreach, quote, publication, package upload, registry submission,
credential creation, source enablement, or runtime activation was performed during this
research.

## Appendix: E engineering delta

E cannot reuse the current public contract unchanged: `CatalystEdgeResponse` requires an
`edge` object containing score, direction, confidence, and horizon, and
`catalyst_edge_score` registers that schema.

E therefore requires:

- a separately named `catalyst_edge_evidence` tool;
- a `CatalystEvidenceResponse` limited to ticker, as-of/lookback, evidence, data quality,
  and next checks, plus the existing claim-source pagination tool;
- a service path that collects and merges evidence without invoking the directional
  scorer;
- tool-registration and compatibility updates;
- new schema, acceptance, and regression tests; and
- E-specific documentation and runbook language.

The effort is unestimated. Counsel should compare A and E explicitly, and buyer discovery
should test whether provenance/missingness alone replaces a real step.
[`models.py`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/catalyst_edge_mcp/models.py#L183-L266),
[`server.py`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/catalyst_edge_mcp/server.py#L115-L172)

## Code and document references

- [`GTM_PLAN.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/GTM_PLAN.md#L1-L12) — current product positioning and institutional boundary.
- [`docs/commercial/design-partner-package.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/docs/commercial/design-partner-package.md#L1-L34) — current fixed package and acceptance model.
- [`docs/commercial/source-rights-matrix.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/docs/commercial/source-rights-matrix.md#L1-L24) — current rights decisions; GDELT is a candidate for field-level relaxation after confirmation.
- [`docs/commercial/design-partner-pricing-decision.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/docs/commercial/design-partner-pricing-decision.md#L1-L45) — cost and paid-evidence method.
- [`docs/validation/release-candidate-0.1.1-2026-08-02.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/docs/validation/release-candidate-0.1.1-2026-08-02.md#L175-L188) — exact technical/commercial gate boundary.
- [`catalyst_edge_mcp/settings.py`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/catalyst_edge_mcp/settings.py#L119-L158) — current source defaults.
- [`catalyst_edge_mcp/source_policy.py`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/987710a17f2ea911435069dfbe6d982c10f77600/catalyst_edge_mcp/source_policy.py#L34-L76) — static production policy.

## Historical context

- [2026-08-01 monetization-readiness research](https://github.com/rm0nroe/catalyst-edge-mcp/blob/3ddec750ae025c8b990ecfbad0b0346c8c625595/thoughts/unknown-ticket/research/2026-08-01-RESEARCH-monetization-readiness.md) — bounded implementation/commercial gap; its managed-Watchlist hypothesis is superseded.
- `/Users/ryanmonroe/Desktop/dev/portfolio-monetization/2026-07-09-codex-portfolio-monetization.md` — historical public-proof/commercial-control/protected-advantage framework; July rankings and prices were not reused as current evidence. The portfolio directory is not a Git repository, so no valid GitHub permalink exists.

## Open questions

- What exact output semantics does counsel clear for a paid installation?
- Which named buyer owns the first relevant research workflow and environment?
- What are the actual cost-sheet inputs and resulting quote?
- Does SEC+GDELT evidence replace a meaningful manual step without broader licensed data?
- Does the proof repository change procurement, or merely attract non-buying developers?
- Which security artifacts does the first buyer require beyond the proposed baseline?

## Follow-up reevaluation: broad self-serve path

**Updated:** 2026-08-02 after owner feedback rejecting interviews, prospecting, and a
boutique-fund-first motion.

### Correction

The institutional recommendation above is superseded. It treated the current
`GTM_PLAN.md` audience and founder-led service motion as if they followed from the
product research. They do not.

- The PRD defines the users as agentic investment-research workflows,
  analysts/builders, and internal tools. It does not restrict the product to funds or
  institutional buyers. It explicitly targets the question, “what recent catalyst
  evidence exists, how strong is it, what changed, what supports it, and what should be
  checked next?”
  [`PRD.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/PRD.md#L101-L123)
- The implementation is already a local, user-run product: two read-only MCP tools,
  stdio and loopback HTTP, a zero-subscription baseline, deterministic scoring, exact
  provenance, contradictions, typed missingness, and explicit limitations. It does not
  require an institutional deployment model.
  [`TDD.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/TDD.md#L23-L35),
  [`TDD.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/TDD.md#L83-L95),
  [`TDD.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/TDD.md#L534-L563)
- The founder-led design partnership, executive buyer titles, 40–50 prospect list,
  custom demonstrations, and explicit retail exclusion were introduced by
  `GTM_PLAN.md`. They are GTM choices, not PRD/TDD product boundaries.
  [`GTM_PLAN.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/GTM_PLAN.md#L34-L75)
- The earlier retail-first work was not disproven. It was shelved because retail was
  then declared out of scope. Its useful audience conclusion remains: the product fits
  AI-native, self-directed equity researchers and agent builders, not mainstream users
  who need a conventional UI or traders expecting alerts, execution, or proven alpha.

### Revised recommendation

Use a two-step product-led model:

1. **Launch the complete `Catalyst Edge Local Beta` free and self-serve.** Publish the
   full current MIT product through GitHub and PyPI, attach a signed Claude Desktop
   `.mcpb`, and add the validated MCP Registry listing after the release is public and
   tested. Do not create a proof-only repository or require a call, interview, demo, or
   custom installation. Anthropic's desktop extension format exists specifically to
   turn local Python MCP servers into one-click installs; the MCP Registry supplies
   discovery metadata, not hosting or checkout.
   [Anthropic desktop extensions](https://www.anthropic.com/engineering/desktop-extensions),
   [MCP Registry](https://modelcontextprotocol.io/registry/about)
2. **Put one paid destination beside it: `Hosted Pro — $29/month, coming soon`.** The
   signup page should ask for the user's email, MCP client, and whether they would pay
   $29/month for zero-install hosted access and managed updates. Do not build hosting,
   accounts, billing, or tenancy until that page produces clear paid intent. If it does,
   obtain one scoped securities-counsel decision on the exact paid output and build one
   hosted SKU. If it does not, keep the local product free and do not invent a service
   business around it.

The price is a test, not a proven willingness-to-pay claim. It sits near Quiver's current
$30/month Hobbyist API/MCP tier, while broader retail platforms charge about $25–$79 per
month and include substantially more data, screens, alerts, and portfolio workflows.
That makes an immediate $49/month local subscription or $199 paid beta difficult to
justify before Catalyst demonstrates recurring use. Quiver currently exposes 10–18 MCP
tools and proprietary datasets at $30/$75 monthly; Catalyst exposes two tools and wins on
evidence synthesis, provenance, typed missingness, and local control rather than data
breadth.
[Quiver API/MCP pricing](https://api.quiverquant.com/pricing/),
[Quiver retail pricing](https://www.quiverquant.com/),
[Koyfin pricing](https://www.koyfin.com/pricing/)

### Audience and promise

Target one broad but coherent group:

> Technical, self-directed equity investors and agent builders who already use Claude,
> Codex, Cursor, or another MCP client and want faster, auditable ticker research.

Here, **builders includes retail traders and technically capable individual investors who
build their own agent workflows**. It does not mean only professional developers,
institutional research engineers, or software companies. The initial segment is defined
by behavior—already using AI tools and assembling a personal research stack—not by
employer, assets under management, or professional title.

Lead with:

> Ask your AI research agent what changed for a ticker, why it matters, what contradicts
> it, and show every source and missing-data warning.

Do not market “make money,” alpha, buy/sell signals, predictive performance, options
flow, or comprehensive market coverage. The user wants to make better investing
decisions; the product's defensible promise is reducing research time and making the
evidence auditable. The PRD explicitly excludes recommendations, performance claims,
investment advice, a UI, and commodity market-data endpoints.
[`PRD.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/PRD.md#L109-L123)

### Why free local first

- **Distribution matches the product.** The package and Registry metadata already
  validate locally, and fresh wheel/sdist installs expose exactly the two intended tools.
  A clean commit/tag, hosted CI proof, and public artifacts remain incomplete.
  [`release-candidate-0.1.1-2026-08-02.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/docs/validation/release-candidate-0.1.1-2026-08-02.md#L30-L35),
  [`release-candidate-0.1.1-2026-08-02.md`](https://github.com/rm0nroe/catalyst-edge-mcp/blob/36730391ad124cff82bcf6aaa346dc0e93248813/docs/validation/release-candidate-0.1.1-2026-08-02.md#L175-L188)
- **A paid local download has weak protection.** The current MIT license permits
  redistribution, so the durable paid value would have to be hosting, managed updates,
  proprietary data, or another maintained service—not access to the existing source
  alone.
- **Charging for the current directional output adds a real legal gate.** The tool emits
  ticker-specific score, direction, confidence, and horizon on demand. Direct payment
  makes the investment-adviser/publisher-exclusion analysis materially more important;
  a disclaimer does not determine the legal characterization. A free uncompensated
  release removes the direct-payment element but is not a categorical legal safe harbor.
  [SEC IA-1092](https://www.sec.gov/files/rules/interp/1987/ia-1092.pdf),
  [SEC Hendricks response](https://www.sec.gov/divisions/investment/noaction/2015/jonathon-hendricks-012615-202a.htm)
- **Free alternatives already exist.** Fiscal offers a meaningful free remote financial
  API/MCP allowance, so Catalyst needs usage and a crisp provenance-first distinction
  before a paid narrow product is credible.
  [Fiscal free trial](https://docs.fiscal.ai/docs/guides/free-trial)

### Smallest execution plan

#### Release gate

1. Make the public default source set conservative and rights-cleared. Require a valid
   SEC identity, disable conditional/uncleared sources by default, keep GDELT disabled
   until its required attribution/linking is implemented and tested, and make the
   documented rights matrix match the runtime.
2. Produce one clean reviewed `0.1.1` commit/tag, run the existing CI on GitHub, and
   verify the released wheel, sdist, rollback, and exact two-tool discovery.
3. Build and test one signed Claude `.mcpb` plus one copy-paste Codex/PyPI install path.
4. Publish the full release to GitHub and PyPI, then publish the Registry entry only after
   those permanent public artifacts work.

#### One launch surface

Create one page with:

- the single-sentence promise above;
- a 60–90 second real dossier/provenance example;
- `Install free` for Claude and Codex;
- `Hosted Pro — $29/month, coming soon` paid-intent signup;
- explicit unbacktested/non-advisory/source-coverage limitations; and
- links to documentation, source policy, security notes, and issue reporting.

Use public launch content and package discovery to reach the audience. Measure release
downloads, successful-install reports, issue/support burden, and Hosted Pro signups. No
interviews, call scheduling, prospect spreadsheets, custom demos, or outbound cohort is
part of the plan.

#### Decision

- **Paid intent appears:** commission one tightly scoped legal review of the exact Hosted
  Pro output, then build one remote MCP tier at the tested price. Do not add a dashboard,
  brokerage integration, alerts, or an institutional administration layer.
- **Paid intent does not appear:** keep Local Beta free, improve or stop based on actual
  use, and do not manufacture revenue through founder-led consulting.

### Explicitly removed from the plan

- eight no-demo problem interviews;
- counsel quote shopping before a free launch;
- small-fund/boutique-firm targeting;
- 40–50 named prospects and warm introductions;
- founder-led demonstrations and custom five-ticker acceptance;
- private design-partner installation and procurement artifacts;
- the proof-only public repository;
- the historical `$199 for 90 days`, `$49/month`, or `$399/year` paid local beta;
- hosted infrastructure before paid intent; and
- any promise of alpha, investment performance, trade signals, or execution.

### Remaining open questions

- Whether the owner wants to authorize public MIT distribution; this is a strategic and
  irreversible-enough distribution decision, not a research task.
- The exact minimum paid-intent threshold that would justify counsel and hosted build
  cost; it should be set from the estimated hosted build/operating cost rather than an
  invented conversion benchmark.
- Whether directional score/direction/horizon remain in a future paid tier or the paid
  tier exposes only evidence/provenance/quality measures; counsel must decide against the
  exact proposed paid experience.
