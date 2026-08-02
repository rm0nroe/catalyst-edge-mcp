# Deployment Source and Output Rights Matrix

**Status:** Fail-closed commercial deployment record, refreshed 2026-08-02. This is an engineering control, not legal advice. Counsel must review the actual customer, jurisdiction, source terms, data flow, retention, and output before paid delivery.

Public access, an API key, a client-library license, and an open protocol do not by themselves grant commercial collection, storage, transformation, or redistribution rights.

## Current baseline

| Source | Runtime capability | Retained/customer-visible material | Paid-deployment decision | Gate before enablement |
| --- | --- | --- | --- | --- |
| SEC EDGAR/API | Direct filings, ownership, Form 144, and reviewed fund records | Parsed facts, identifiers, hashes, timestamps, accession IDs, and SEC links; no indiscriminate full-text redistribution | **Candidate baseline, counsel sign-off required.** SEC says site information is public and may be copied/distributed, while automated access must follow fair-access and bot-identification rules. Filer-supplied content still requires bounded use and accurate attribution. | Customer-owned monitored identity; <=10 aggregate requests/second and this product's lower internal limit; official hosts only; privacy/security policy; retention/output review |
| Apple Newsroom feed | Reviewed issuer metadata path | Titles, timestamps, identifiers, hashes, links, and short provider-generated factual extraction | **Disabled for paid deployment.** Apple's website terms restrict site information to personal, non-commercial informational use absent express permission; a public RSS endpoint is not enough. | Written commercial permission or counsel-approved narrower use for the exact feed/output |
| NVIDIA issuer feed | Reviewed issuer metadata path | Same bounded metadata/link envelope | **Disabled for paid deployment.** The applicable terms and commercial output rights for the specific feed were not established by the refreshed review. | Identify governing feed terms and obtain written permission or counsel approval |
| Other issuer feed | Registry supports reviewed hosts | Same bounded metadata/link envelope | **Disabled by default.** Registry review proves identity/host, not commercial rights. | Source-specific terms, robots/rate review, retention/output decision, and written/counsel approval |
| GDELT Project/Web NGrams | Discovery metadata cached outside request path | Publisher metadata, derived entity decisions, hashes, and links; not article bodies | **Disabled for paid deployment pending clarification.** No official Project term located in the refreshed review clearly grants the required commercial collection/output rights; GDELT Cloud terms are a separate service and do not clear this implementation. | Written Project permission or counsel-approved official license/terms for exact endpoints and outputs; underlying publisher limits preserved |
| Bluesky AppView | Partial public-attention windows | Minimal post metadata, derived counts/windows, hashes, and representative links; no post-body redistribution | **Disabled for paid deployment pending counsel.** Developer guidelines permit ecosystem access subject to platform rules, but user content remains user-owned and the reviewed terms do not establish a blanket downstream commercial content license. | Developer-guideline compliance, privacy/retention assessment, deletion handling, output limitation, and written/counsel approval |
| Mastodon | Adapter/registry concept only; not composed | Would be instance-scoped metadata and derived buckets | **Disabled.** No reviewed instance is selected and each instance can have distinct terms. | Instance-specific terms, representativeness, rate, privacy, retention, and written/counsel approval |
| FMP/Finnhub | Conditional adapters/credentials | Vendor-defined normalized evidence | **Disabled.** Credential presence is not entitlement. | Executed plan/license covering automation, commercial use, storage, derived outputs, customer display, and audit |
| OPRA/options vendor, FlowAlgo, CheddarFlow | Conditional transaction-plus-quote adapter | Auditable transaction/quote-derived evidence | **Disabled.** Licensed feed required; no current provider clears the gate. | Executed agreement covering non-display use, derived data, storage, redistribution/customer access, symbols, and exchange fees |
| Customer OHLC | Optional technical family | Derived indicators and transition evidence | **Disabled until customer supplies rights.** | Customer identifies provider/plan and warrants automation, storage, derived analysis, and use in this deployment; provider terms attached |
| yfinance/Yahoo-backed data | Private diagnostic only | No production evidence or readiness credit | **Prohibited in paid output.** | No enablement path in this offer; replace with licensed source |
| Customer documents, positions, or portfolio data | Not implemented by core MCP | None | **Out of scope.** | Separate product/security/legal design; do not accept through this engagement |

The MIT license covers Catalyst Edge code only. It does not license SEC filing content, issuer content, social posts, market data, customer data, or third-party APIs.

## Official references used for the refreshed boundary

- [SEC Developer Resources](https://www.sec.gov/about/developer-resources): automated access and 10-request-per-second aggregate fair-access ceiling.
- [SEC Privacy Information](https://www.sec.gov/about/privacy-information): SEC.gov information is public and may be copied or further distributed, subject to stated restrictions.
- [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): API access remains subject to the SEC privacy/security policy.
- [Apple Website Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html): commercial copying/distribution restrictions block assumption-based feed use.
- [Bluesky Developer Guidelines](https://docs.bsky.app/docs/support/developer-guidelines) and [Bluesky Terms](https://bsky.social/about/support/tos): developer obligations, user-content ownership, and absence of a blanket downstream content license.
- [GDELT Cloud Terms](https://gdeltcloud.com/terms): relevant only to the separate GDELT Cloud service; not evidence that GDELT Project endpoints used here are commercially cleared.

## Per-deployment sign-off

Copy one row per proposed source into the customer release record.

| Field | Required value |
| --- | --- |
| Customer/legal entity and environment |  |
| Source ID, endpoint, account, and plan |  |
| Governing terms/license and effective date |  |
| Automation and rate rights | allowed / prohibited / unclear |
| Commercial internal use | allowed / prohibited / unclear |
| Retained fields and retention duration |  |
| Transformation/derived-analysis rights | allowed / prohibited / unclear |
| Customer display/export/redistribution rights | allowed / prohibited / unclear |
| Personal data/deletion obligations |  |
| Credential owner and rotation owner |  |
| Output attribution/notice |  |
| Geography/user restrictions |  |
| Provider written confirmation | attached / not required / missing |
| Counsel decision, reviewer, and date | approved / restricted / rejected |
| Runtime policy decision and registry hash |  |

Any `unclear`, `missing`, expired, or scope-mismatched value means disabled. The deployed configuration and runtime composition must be checked against the signed rows before every release.

## Securities-law delivery gate

Compensation for reports or analyses concerning securities can fall within the Investment Advisers Act definition; whether an exclusion applies is fact-specific. The package therefore prohibits recommendations, personalized portfolio advice, performance promises, execution, and suitability decisions, but those product constraints do not replace counsel review. See the SEC's [Investment Management Staff Issues of Interest](https://www.sec.gov/rules-regulations/no-action-interpretive-exemptive-letters/division-investment-management-staff-no-action-interpretive-letters/investment-management-staff-issues-interest).
