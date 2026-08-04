# Public Self-Serve Source and Output Rights Matrix

**Status:** Current fail-closed engineering decision for the Local Beta, refreshed
2026-08-03 from official source terms. This is not legal advice and does not authorize a
paid securities-analysis product.

Public access, an API key, an open protocol, or a package license does not automatically
grant collection, storage, transformation, display, or redistribution rights. Unknown or
scope-mismatched sources remain disabled.

## Local Beta defaults

| Source | Implemented capability | Public default | Current decision and gate |
| --- | --- | --- | --- |
| SEC EDGAR/API | Filings, ownership, Form 144, and reviewed fund records; parsed facts, identifiers, hashes, times, accession IDs, and official links | **Available when a valid identity is configured** | Baseline. SEC provides comprehensive public EDGAR access and permits copying/distribution of site information subject to stated restrictions. Require a monitored `Company email@example.com` identity, official hosts, efficient requests, and no more than 10 aggregate requests/second; retain bounded derived facts/links rather than indiscriminate full-text redistribution. |
| Apple Newsroom feed | Reviewed issuer metadata path | **Disabled** | Apple's site terms restrict commercial reuse absent permission. Do not enable in the public package without written permission or a documented narrower rights decision for the exact feed/output. |
| NVIDIA issuer feed | Reviewed issuer metadata path | **Disabled** | Exact governing feed terms and commercial output rights remain unverified. Require source-specific terms and a recorded release decision. |
| Other issuer feeds | Registry supports reviewed hosts | **Disabled** | Registry review proves identity/host, not reuse rights. Require source terms, robots/rate review, retained/output fields, attribution, and a release decision. |
| GDELT Project/Web NGrams | Cached discovery metadata, derived entity decisions, hashes, and publisher links; no article bodies | **Disabled** | GDELT officially permits unlimited academic/commercial/government use and redistribution without fee, but every use or redistribution must cite and link to GDELT. The current dossier exposes publisher links without the required GDELT citation/link. Keep disabled until that output requirement is implemented and tested; preserve underlying publisher limits. |
| Bluesky AppView | Forward-only partial public-attention buckets, derived counts, pseudonymous hashes, and representative links; no post bodies | **Disabled** | Engineering decision completed 2026-08-03: six-hour out-of-band collection, cache-only MCP reads, 14 completed daily buckets, explicit purge command, disappearance/takedown uncertainty fails closed. Official docs support unauthenticated public AppView reads, but user content remains user-owned and third-party commercial/output rights are not explicit; keep the public default disabled pending owner release approval and 14-day live readback. |
| Mastodon | Adapter/registry concept only; not composed | **Disabled** | No reviewed instance set exists, and instance terms vary. |
| FMP/Finnhub | Conditional credentialed adapters | **Disabled** | A key is not entitlement. Require an executed plan/license covering automation, storage, derived output, display, and audit. |
| OPRA/options vendors, FlowAlgo, CheddarFlow | Conditional transaction-plus-quote adapter | **Disabled** | Licensed transaction/quote rights are required; no current provider clears the gate. |
| User-supplied OHLC | Optional technical family | **Disabled** | Require the user to identify a provider/plan that permits automation, storage, and derived analysis; not part of Local Beta defaults. |
| yfinance/Yahoo-backed data | Private diagnostic only | **Prohibited in public output** | No enablement path for Local Beta; replace with a rights-cleared source. |
| User documents, holdings, positions, or portfolio data | Not implemented by the core MCP | **Out of scope** | Do not accept through the core product. |

The MIT license covers Catalyst Edge code only. It does not license filings, issuer
content, social posts, market data, user data, or third-party APIs.

## Official references

- [SEC Developer Resources](https://www.sec.gov/about/developer-resources): official API/
  EDGAR access, classified-bot requirement, efficient downloading, and the 10-request-per-
  second aggregate ceiling.
- [SEC Privacy Information](https://www.sec.gov/about/privacy-information): SEC website
  dissemination and fair-access/security policy.
- [GDELT Terms of Use](https://www.gdeltproject.org/about.html#termsofuse): unlimited and
  unrestricted academic, commercial, and governmental use; redistribution requires a
  GDELT citation and link.
- [Apple Website Terms of Use](https://www.apple.com/legal/internet-services/terms/site.html):
  commercial copying/distribution restrictions.
- [Bluesky Developer Guidelines](https://docs.bsky.app/docs/support/developer-guidelines)
  and [Bluesky Terms](https://bsky.social/about/support/tos): developer obligations and
  user-content ownership.

## Release decision record

Complete one row for every source proposed for a public version. This is an internal
release record, not a customer interview or counsel quote request.

| Field | Required value |
| --- | --- |
| Package version and source ID |  |
| Exact endpoint and governing terms/effective date |  |
| Automation/rate rights | allowed / prohibited / unclear |
| Commercial use | allowed / prohibited / unclear |
| Retained fields and duration |  |
| Transformation/derived-analysis rights | allowed / prohibited / unclear |
| Public display/export/redistribution rights | allowed / prohibited / unclear |
| Attribution/notice required and implementation proof |  |
| Personal-data/deletion obligations |  |
| Geography/user restrictions |  |
| Runtime default and registry hash | enabled / disabled |
| Reviewer, date, and evidence link |  |

Any `unclear`, expired, missing, or scope-mismatched value means disabled. Credentials do
not change the decision.

## Paid-product boundary

Local Beta is free, impersonal, local research software. Before accepting payment or
enabling a Hosted Pro securities-analysis experience, obtain one scoped legal decision on
the exact output, claims, compensation model, jurisdictions, and distribution. This is a
paid-launch gate—not discovery, an interview cohort, or counsel quote-shopping.

The current GTM plan permits consideration of that scoped review only after 1,350 recent
activation-linked, verified, price-aware signups and separate Ryan authorization. Clearing
that threshold does not resolve any source row, authorize payment, or authorize the build.
The full Hosted Pro architecture is not reconsidered before the safeguarded 11,100-signup
gate and fresh re-costing. Unknown or scope-mismatched paid rights remain disabled regardless
of demand.
