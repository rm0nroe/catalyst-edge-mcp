# Zero-subscription catalyst data research

**Project:** Catalyst Edge MCP

**Research date:** 2026-07-13

**Contract reviewed:** `product specification` and `technical specification`

**Scope:** legally durable, source-linked insider, company-event, options, and social inputs for a commercial-capable local MCP

## Executive verdict

**The differentiated product vision can be partially achieved without data subscriptions.** A strong, source-linked dossier can be built for insider activity and material company events, with useful but explicitly partial social-attention signals. Reliable transaction-level US listed-options flow cannot be supplied legally and durably for free.

The free product should therefore be positioned around what it can uniquely do well: join primary filings, ownership changes, planned-sale disclosures, issuer releases, material-event classifications, source provenance, event novelty, and measured public attention into one deterministic dossier. It must not claim that end-of-day option totals or public chain snapshots are sweeps, blocks, premium flow, or aggressor-side activity.

The defensible result is:

- **Insiders: strong free coverage.** Direct SEC submissions, Forms 3/4/5 ownership XML, and Form 144 support transactions, ownership deltas, 10b5-1 indicators, planned-sale notices, and deterministic insider clusters.
- **News/material events: strong primary-source coverage plus broad discovery.** SEC 8-K/6-K exhibits and issuer IR feeds provide authoritative events; GDELT Project helps discover and cross-link external coverage.
- **Options: an unavoidable gap.** OPRA licensing governs consolidated US options trades and quotes. Free chain snapshots and end-of-day aggregates cannot reconstruct trade premium, side, multi-exchange sweeps, or blocks.
- **Social: useful but incomplete.** Bluesky and selected Mastodon instances are legally accessible, but neither supplies a complete market-wide history. Reddit and Stocktwits cannot be assumed available for a commercial zero-subscription product.

If full-fidelity options flow is a mandatory product specification acceptance criterion, the zero-subscription build does **not** meet the product specification. If the product contract permits honest missingness and a later licensed adapter, it can still deliver a differentiated dossier rather than a generic finance-data wrapper.

## What “free” means here

“Free” means no recurring data subscription and no reliance on unapproved scraping, credential sharing, stolen keys, CAPTCHA solving, residential proxies, or redistribution-prohibited corpora. It does not mean zero operating cost. A local-only deployment still consumes bandwidth, disk, CPU, model storage, and maintenance time. A hosted deployment adds compute, egress, monitoring, secrets management, and abuse-control costs.

Licensing labels below distinguish:

- **Commercially usable:** primary terms support the proposed internal/derived use.
- **Conditional:** permitted only after issuer-by-issuer review, written approval, or a separate contract.
- **Not suitable:** terms prohibit the proposed commercial automation, exploitation, or redistribution.

This is an engineering licensing assessment, not legal advice. External redistribution of raw source data should receive counsel review.

## Product and technical specification implications

The technical specification currently defines canonical families for `filings_news`, `insider_trading`, `options_flow`, `technical`, and `social`, with deterministic family budgets and neutral missingness. The free architecture should preserve that scoring discipline while changing the source semantics:

1. Replace paid insider/news assumptions with direct SEC and issuer-originated evidence.
2. Keep GDELT and social platforms as discovery/attention inputs, not primary fact authorities.
3. Do not let an OCC report, Alpaca indicative feed, yfinance chain, or unusual-volume heuristic set `options_flow.available=true`.
4. Either add a separate `options_eod_activity` observation type or emit a typed `options_flow_unavailable` result. If the proxy remains inside the options family, cap its confidence and label every field as end-of-day aggregate data.
5. Preserve source URL, accession or platform record ID, observed time, published time, parser version, raw-content hash, and license policy with every observation.

---

## 1. Insider activity

### Ranked comparison

| Rank | Source/project | Exact data supplied and access | License / commercial use | Limits, history, freshness | Reliability / maintenance | Effort | product specification fit | Missing fields / risks / hidden cost |
|---:|---|---|---|---|---|---|---|---|
| 1 | [SEC EDGAR submissions and filing archives](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [ownership technical specifications](https://www.sec.gov/submit-filings/technical-specifications) | `GET https://data.sec.gov/submissions/CIK##########.json`, then filing XML at `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{xml_basename}`. Forms 3/4/5 provide reporting owner, issuer, relationship, transaction code/date, shares, price, acquired/disposed flag, direct/indirect ownership, post-transaction holdings, footnotes, derivatives, and the Form 4/5 Rule 10b5-1 checkbox. [Form 144](https://www.sec.gov/files/form144.pdf) supplies proposed-sale amount/value/date, broker, seller relationship, acquisition history, prior three-month sales, and plan-adoption date when applicable. No key; identifying `User-Agent` required. | US government and EDGAR public filing content is available to access and reuse; attribute the SEC and do not imply endorsement or misuse SEC marks. See the [SEC webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions) and [privacy/public-information notice](https://www.sec.gov/about/privacy-information). Suitable for commercial derived analysis and source linking. | SEC fair-access ceiling is [10 requests/second across the requester’s machines](https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits). Run at 2 rps/concurrency 2 locally. Submissions typically update in under one second; recent JSON includes at least one year or 1,000 filings and points to older shards. Bulk submissions refresh nightly. EDGAR archives supply long history. | Primary source and highest legal durability; no uptime SLA. Current specs include Ownership XML 5.5 effective 2026-03-18 and Form 144 2.0. | Medium | Full insider evidence, ownership change, planned sales, insider clusters, provenance. | Footnotes are sometimes necessary to interpret economics. Form 144 is intent, not proof of execution. Grants, tax withholding, exercises, gifts, and conversions are not directional purchases/sales. A 10b5-1 checkbox indicates intended reliance, not that a plan is valid. SEC may throttle or change courtesy endpoints. |
| 2 | [EdgarTools](https://github.com/dgunning/edgartools), [data-object docs](https://edgartools.readthedocs.io/en/latest/data-objects/) | High-level Python objects for Forms 3/4/5, Form 144, 8-K items, exhibits, ownership transactions, holdings, and related tables. Install `edgartools`; use for backfills, fixtures, and parser validation rather than request-path networking. | MIT; commercial use permitted. | Uses SEC data and therefore inherits SEC rate/freshness rules. Version 5.42.0 was current during review; Python 3.10+; repository pushed 2026-07-09. | Actively maintained and unusually complete for SEC domain parsing. Its public API can evolve and network operations are synchronous. | Low for offline/backfill; medium for production isolation | Accelerates insider and event parsing without inventing a second schema. | Not a new data source or a substitute for SEC provenance. Synchronous access is a poor fit for the bounded async MCP request path. Pin versions and keep raw XML fixtures so parser regressions are visible. |
| 3 | [`sec-edgar-downloader`](https://github.com/jadchaar/sec-edgar-downloader), [PyPI](https://pypi.org/project/sec-edgar-downloader/) | Downloads selected filing forms from EDGAR with company name/email identity and a built-in rate limiter. Good for fixture generation and controlled historical backfill. | MIT; commercial use permitted. | Inherits SEC history/freshness; built-in 10 rps ceiling. Version 5.1.0, Python 3.10+, repository pushed 2026-06-22. | Maintained, simple, and narrow. | Low | Backfill/fixture support for Forms 3/4/5, 144, and 8-K. | Downloader only; it does not supply domain parsing, clustering, or production async collection. Do not duplicate it in the request path if direct `httpx` already handles fetching. |

### Recommended insider implementation

Use direct async SEC collection and parse ownership XML locally:

- Fetch with the existing `httpx.AsyncClient`, an identifying `User-Agent`, per-host concurrency 2, a 2 rps token bucket, conditional requests, and a 6-second source timeout.
- Resolve the filing document from the archive `index.json` or the basename of `primaryDocument`. A submission value such as `xslF345X06/form4.xml` is an EDGAR display path; the archive file can be `form4.xml` at the accession root.
- Parse XML with [`lxml`](https://pypi.org/project/lxml/) 6.1.x (BSD-style license, Python 3.8+) into a stable internal schema. Keep EdgarTools as an optional backfill/validation extra, not a network dependency inside the MCP deadline.
- Build deterministic clusters only after classifying transaction codes. A useful cluster requires at least three distinct insiders with open-market purchase code `P` in a rolling seven-day window. Report sales code `S` separately, with 10b5-1 and Form 144 context. Never treat `A`, `M`, `F`, `G`, or derivative conversions as equivalent to discretionary open-market activity.
- Compute ownership change from post-transaction holdings and transaction shares, retaining footnotes and direct/indirect ownership. Use disclosed price for transaction value; do not synthesize a price where the filing omits it.

---

## 2. Company news and material events

### Ranked comparison

| Rank | Source/project | Exact data supplied and access | License / commercial use | Limits, history, freshness | Reliability / maintenance | Effort | product specification fit | Missing fields / risks / hidden cost |
|---:|---|---|---|---|---|---|---|---|
| 1 | [SEC 8-K/6-K filings, exhibits, and submissions API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Form 8-K](https://www.sec.gov/files/form8-k.pdf) | Filing metadata, accepted time, item numbers, filing documents, and exhibits such as EX-99.1 earnings releases. Use submissions JSON plus archive `index.json`; optionally use the official [company/filing Atom query](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=8-K&dateb=&owner=exclude&count=40&output=atom). No key; identifying user agent. | Same SEC public-information terms as above; suitable for commercial derived analysis and links. | 10 rps official ceiling; run below it. Near-real-time submissions, long archive history. Most reportable 8-K events are due within four business days, so the source is authoritative but not necessarily first disclosure. | Primary, structured, stable, no SLA. SEC also publishes [EDGAR and structured-data RSS feeds](https://www.sec.gov/data-research/structured-data/structured-disclosure-rss-feeds), with structured feeds updated about every ten minutes during published weekday hours and monthly archives from 2005. | Medium | Material events, earnings releases, regulatory filings, primary-source links, catalyst classification. | An 8-K may follow an issuer release or omit economic direction. Item number identifies event class, not automatically bullish/bearish effect. Exhibit HTML varies. Foreign private issuers use 6-K. |
| 2 | Official issuer investor-relations RSS/Atom and press-release pages, such as [NVIDIA’s official newsroom RSS](https://nvidianews.nvidia.com/rss.xml) and [Apple Newsroom RSS](https://www.apple.com/newsroom/rss-feed.rss) | Official release title, publication time, canonical URL, category, and sometimes body or attachments. Discover standards-based `<link rel="alternate" type="application/rss+xml|atom+xml">`, then maintain a reviewed issuer-feed registry. Fetch with conditional GET. | Conditional by issuer. Public access is not a blanket license to store or redistribute full text. Store metadata, hashes, source links, and an internally generated short factual extraction; retain bodies only where terms allow. | No universal limit, history, or SLA. Poll no faster than 5–15 minutes, honor `ETag`, `Last-Modified`, `Retry-After`, robots controls, and issuer terms. Many feeds expose only recent items. | Highest-value primary disclosure after EDGAR, but URLs and vendors change. Requires health checks and manual registry maintenance. | Medium initially; high at broad issuer coverage | Company press releases, earnings releases, presentations, event timing, primary-source provenance. | Site-by-site legal/robots review, feed breakage, missing timezone, duplicated wire releases, and manual issuer onboarding. No browser scraping fallback. Hidden cost is ongoing feed maintenance. |
| 3 | [GDELT Project](https://www.gdeltproject.org/data.html) [DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) and downloadable data | Broad multilingual news metadata, article URLs, publication times, source domain, themes/tone, and discovery queries. DOC endpoint: `GET https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=ArtList&maxrecords=250&format=json&startdatetime=YYYYMMDDHHMMSS&enddatetime=YYYYMMDDHHMMSS&sort=HybridRel`. Raw GDELT 2 data and BigQuery support deeper backfill. No key for Project endpoints. | GDELT describes the Project database as free/open. That does **not** license publisher article text. Store GDELT metadata, derived clusters, and outbound source URLs; do not redistribute scraped article bodies. Do not confuse free GDELT Project with [GDELT Cloud](https://gdeltcloud.com/acceptable-use), whose commercial/redistribution terms and pricing are separate. | DOC 2.0 is a rolling three-month search surface, maximum 250 results per query. GDELT 2 raw feeds update about every 15 minutes and date to February 2015. A live 429 response on 2026-07-13 instructed callers to limit requests to **one every five seconds**; treat that as the current operational ceiling, serialize calls, cache, and honor future 429 text/headers because there is no contractual quota or SLA. BigQuery can incur query charges. | Long-running project and broad coverage, but no completeness or uptime SLA. URL availability and publisher metadata vary. | Medium | Credible-news discovery, coverage-change signals, corroborating links, cross-source novelty. | Not authoritative for company facts; tone is not a trade-direction label. Syndication creates duplicates. Article rights remain with publishers. Queries can have false entity matches, language issues, and link rot. |
| 4 | SEC [RSS feeds](https://www.sec.gov/about/rss-feeds) and regulatory announcement feeds | SEC latest filings, company filings, ownership-form filters, litigation/releases, and rulemaking notices in RSS/Atom. Fetch bytes asynchronously and parse locally. | SEC public-information terms; source links and derived metadata suitable. Other agency feeds require their own terms review. | Feed-specific schedules; EDGAR feeds are courtesy services and formats may change. SEC page was updated 2026-06-24. | Official and low-cost; less complete than submissions/archive APIs for backfill. | Low | Regulatory announcements and a low-latency wake-up mechanism. | Not a canonical database; use as an ingestion trigger and reconcile against EDGAR. |

### Open-source components for collection and deduplication

| Component | License / status | Exact role | Async and Python fit | Risk |
|---|---|---|---|---|
| [`feedparser`](https://github.com/kurtmckee/feedparser) 6.0.12 | BSD-2-Clause; repository pushed 2026-07-06 | Parse RSS/Atom bytes after `httpx` fetches them. | Python 3.10 compatible. Parsing is synchronous CPU work but small and safe after async I/O. | It sanitizes feeds but does not grant content rights or discover every vendor-specific IR endpoint. |
| [`RapidFuzz`](https://github.com/rapidfuzz/RapidFuzz) 3.14.5 | MIT; repository pushed 2026-06-22 | Deterministic normalized-title and token-set similarity for low-volume duplicate clustering. | Python 3.10+; fast local CPU. | Threshold tuning is required for issuer names, earnings numbers, and updated stories. |
| [`datasketch`](https://github.com/ekzhu/datasketch) 2.0.0 | MIT; repository pushed 2026-07-05 | Optional five-word-shingle MinHash/LSH when the event store outgrows pairwise title comparison. | Python 3.9+; local batch/background use. | Added complexity is not justified in the MVP; use only after measured scale requires it. |
| [EdgarTools 8-K support](https://edgartools.readthedocs.io/en/stable/eightk-filings/) | MIT; active as above | Parse 8-K item structures, press-release exhibits, and earnings tables for offline/backfill validation. | Python 3.10+, synchronous; isolate from the request path. | Parser API/version drift; always retain accession, exhibit URL, and raw hash. |

### Deterministic primary-source deduplication

1. Normalize issuer identity to CIK and ticker aliases; reject ambiguous bare tokens such as `AI`, `ON`, or `IT` unless a cashtag, CIK, legal name, or contextual alias confirms the company.
2. Create an exact fingerprint from `CIK + accession-or-canonical-URL + normalized-title + source-published-minute`.
3. Canonicalize URLs by lowercasing the host and removing fragments and known tracking parameters. Follow redirects only with a bounded timeout and preserve both original and resolved URLs.
4. Within a 48-hour issuer window, cluster titles at RapidFuzz token-set ratio `>= 92`. For measured high volume, add five-word-shingle MinHash with Jaccard `>= 0.82`.
5. Choose the canonical evidence link by source tier: SEC/regulator or issuer IR, then original wire/publisher, then syndication copy. Keep all alternates in `related_sources`; never discard provenance.
6. Count and sentiment-score a story cluster once. A correction or materially changed numeric result becomes a new version linked to the original, not a duplicate.

---

## 3. Real options activity

### Finding

**Reliable free transaction-level US listed-options flow is not available for the proposed commercial MCP.** OPRA is the consolidated source for equity/index options last sales and quotations. The [OPRA FAQ](https://www.opraplan.com/faqs) defines current data as the preceding 15 minutes; data becomes delayed after 15 minutes and historical on the next trading day. Nonprofessional status is for personal, not business, use. A product/entity performing investment analysis is professional/non-display use.

The current [OPRA fee schedule](https://cdn.opraplan.com/documents/OPRA_Fee_Schedule.pdf) lists, among other charges, $2,000/month for Category 1 enterprise non-display use, $1,500/month for redistribution, $650/month for query-service-only redistribution, $600/month for indirect subscriber access, and $1,000/month for direct access before connectivity. Exact agreements and vendor fees depend on architecture. Delaying data does not make commercial redistribution free, and OPRA’s [datafeed policy](https://cdn.opraplan.com/documents/OPRA_Datafeed_Policy.pdf) adds reporting and entitlement obligations.

### Ranked comparison

| Rank | Source/project | Exact data supplied and access | License / commercial use | Limits, history, freshness | Reliability / maintenance | Effort | product specification fit | Missing fields / risks / hidden cost |
|---:|---|---|---|---|---|---|---|---|
| 1 | [OPRA](https://www.opraplan.com/) directly or through an authorized vendor | Consolidated options trades and quotes needed to calculate trade premium, quote-side inference, large prints, multi-exchange sweeps, blocks, call/put flow, strike, expiration, and trade-vs-open-interest context. Access is contractual feed/vendor connectivity, not an anonymous REST endpoint. | Commercial use requires the relevant OPRA/vendor agreements, display/non-display classification, usage reporting, and fees. **Not zero-subscription.** Redistribution and customer-facing query services carry separate rights. | Real-time or 15-minute delayed depending entitlement; historical classification next trading day. Capacity, history, and rate limits are vendor/feed specific. | The authoritative consolidated source; operationally reliable only with paid feed engineering and compliance. | High | The only candidate that can fully satisfy real options-flow requirements. | Recurring OPRA and vendor fees, possible exchange/connection fees, entitlement reporting, audits, storage, replay, normalization, and compliance operations. Side/aggressor and sweep labels are still derived analytics, not native truth. |
| 2 | [OCC volume query and documented batch endpoint](https://www.theocc.com/market-data/market-data-reports/other-market-data-info/batch-processing/volume-query-batch-processing), [daily open interest](https://www.theocc.com/market-data/market-data-reports/other-market-data-info/batch-processing/daily-open-interest) | End-of-day cleared option volume by symbol/underlying, call/put, account type, exchange, and activity date; daily open interest. Example volume endpoint: `https://marketdata.theocc.com/volume-query?...&format=csv`; OI endpoint: `https://marketdata.theocc.com/daily-open-interest?reportDate=MM/DD/YYYY&action=download&format=csv`. Public report page shows 24 months for volume query. | **Not suitable for an unapproved commercial implementation.** Although OCC documents script endpoints, its [website terms](https://www.theocc.com/specialpages/legal/terms-and-conditions) prohibit automated access and commercial exploitation of Services/Data. Written permission or a data agreement is required before automation or product use. OCC [data sales](https://www.theocc.com/market-data/market-data-reports/other-market-data-info/data-sales) are paid and restrict distribution. | EOD only; volume query exposes up to 24 months. No intraday timing. Availability is website/report dependent and has no product SLA. | OCC is authoritative for clearing aggregates, but the public-report delivery is not a licensed commercial API. | Medium technically; high legally | A conditional `options_eod_activity` proxy only after permission. | No trade timestamp, execution price, premium, bid/ask, aggressor, sequence, sweep/block, or opening/closing truth. Account type is not trade side. It cannot satisfy `options_flow`. |
| 3 | [Alpaca Basic historical option data](https://docs.alpaca.markets/us/docs/historical-option-data) | Authenticated indicative option quotes and delayed trade/quote access, with contract fields. Basic plan documentation states indicative options feed, 200 historical calls/minute, 200 WebSocket quote subscriptions, and options history from February 2024; recent data is delayed/restricted. | Account keys required. [Alpaca’s customer agreement](https://files.alpaca.markets/disclosures/library/AcctAppMarginAndCustAgmt.pdf) restricts reproduction, distribution, sale, and commercial exploitation without written consent. Suitable only for an approved user-supplied-key experiment, not the default commercial product. | Basic-plan limits above; delayed/indicative rather than full OPRA. Vendor terms and plan can change. | Maintained broker API, but data entitlement is not equivalent to a commercial product license. | Medium | Partial contract/quote context for private evaluation only. | Indicative feed is not consolidated OPRA and cannot reliably identify all large trades/sweeps. Account maintenance, contractual permission, and user eligibility are hidden costs. |
| 4 | [yfinance option-chain snapshots](https://github.com/ranaroussi/yfinance) | Current chain fields commonly include strike, expiration, bid/ask/last, displayed volume, and open interest. Unofficial access through Yahoo-backed endpoints. | The library is Apache-2.0, but that does not license Yahoo data. Its own README says the Yahoo API is intended for personal use and directs users to Yahoo’s terms. Treat as best-effort personal/research access only. | Snapshot/update behavior and throttling are undocumented; no completeness/SLA. yfinance 1.5.1 was released 2026-06-28, showing active code maintenance. | Active wrapper, but fragile and unofficial upstream behavior. | Low | At most a degraded chain snapshot. | **Not flow.** No transaction tape, aggressor, sequence, true premium, sweep, or block. Must never be labeled `options_flow`. |
| 5 | [Cboe delayed quotes](https://www.cboe.com/delayed_quotes/api/) or open-source scanners/clients | Web-delayed quote display, or algorithms that label unusual chain volume. Open-source clients such as [Massive’s MIT client](https://github.com/massive-com/client-python) only access their provider’s licensed plans. | Cboe explicitly prohibits programmatic extraction/downloading from its delayed quote API page. Client-library licenses do not license underlying data. Reject undocumented endpoints and unlicensed scanners. | No approved free product API. Provider-specific if licensed. | Code may be maintained; the missing legal data entitlement remains. | Not applicable | None for the zero-subscription product. | Open source cannot recreate missing transaction/quote inputs. Labels produced from chain snapshots are heuristics, not real flow. |

The open-source search produced clients and analyzers, not a free legal tape. The [Unusual Whales official MCP](https://github.com/unusual-whales/unusual-whales-official-mcp) exposes flow only after authenticating to that provider; the maintained [Intrinio Python SDK](https://github.com/intrinio/python-sdk) exposes unusual-activity endpoints backed by a subscription; and the [FlowAlgo Options Trader](https://github.com/SC4RECOIN/FlowAlgo-Options-Trader) consumes FlowAlgo exports rather than detecting flow from public data. Their code can illustrate schemas or algorithms, but neither their code license nor a sweep-labeling algorithm supplies OPRA data rights.

### Recommended options behavior

- In the zero-subscription architecture, return `available=false`, `reason="licensed_transaction_feed_required"`, and links to the OPRA basis for that limitation.
- Do not include OCC automation in the product until OCC gives written permission. If permission is obtained, expose it as `options_eod_activity` with `observation_type="eod_clearing_aggregate"`, never as sweep/block flow.
- Keep the adapter boundary ready for a future licensed OPRA vendor. A licensed implementation must ingest both trades and quotes, preserve sequence/timestamps, join NBBO context, define a transparent sweep window, and distinguish observed fields from derived aggressor/strategy labels.
- Remove or rename any technical specification/API language implying that yfinance fallback “covers” options flow. Neutral missingness is more accurate than false precision.

---

## 4. Social attention and sentiment

### Ranked comparison

| Rank | Source/project | Exact data supplied and access | License / commercial use | Limits, history, freshness | Reliability / maintenance | Effort | product specification fit | Missing fields / risks / hidden cost |
|---:|---|---|---|---|---|---|---|---|
| 1 | [Bluesky public AppView APIs](https://docs.bsky.app/docs/advanced-guides/api-directory) | Public posts, authors, indexed timestamps, AT URIs/CIDs, facets/links, and ranked search. Prefer `GET https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=%24AAPL&limit=100&cursor=...`; the same unauthenticated XRPC is documented at `https://api.bsky.app`. Preserve AT URI/CID and construct a source link to `https://bsky.app/profile/{handle-or-did}/post/{rkey}`. | Bluesky protocol and official implementation are open; public AppView endpoints are intended for public requests. Under [Bluesky’s terms](https://bsky.social/about/support/tos), users retain their content rights. Store minimal metadata, derived counts, and representative links; do not imply ownership of post text or bulk re-host user content. Respect deletion/takedown signals. | Public AppView has generous but unspecified endpoint limits; hosted account/PDS guidance gives 3,000 requests per five minutes per IP for relevant hosted services. Inspect rate headers and back off. Search is indexed/ranked and does not promise complete totals or stable historical depth. Collect forward for reliable time series. | Active ecosystem. [`atproto`](https://github.com/MarshalX/atproto) 0.0.69 is MIT, Python 3.9+, has async support, and was pushed 2026-07-10; its pre-1.0 API may break. Direct `httpx` against the XRPC lexicon is simpler for the MVP. During the 2026-07-13 live check, `public.api.bsky.app` returned a CDN 403 from the current network while the official `api.bsky.app` endpoint returned valid JSON; the POC must test deployment-network reachability and use only the documented alternate host, never proxies. | Medium | Ticker/cashtag mention samples, change over collected time, representative source links, sentiment input. | Partial population and incomplete search counts. Alias ambiguity, bots, reposts, deletion, language, ranking bias, and CDN/network-specific blocking. Full-network collection requires significant storage/ops; the [Jetstream repository](https://github.com/bluesky-social/jetstream) warned during review that its new full-network service was not yet production deployed and on-disk formats could change. |
| 2 | [Mastodon public APIs](https://docs.joinmastodon.org/methods/search/) on a reviewed instance allowlist | Public statuses, timestamps, URLs, accounts, hashtags, boosts/replies, and search results via `GET https://{instance}/api/v2/search?q=%24AAPL&type=statuses`. Depending on instance configuration, app token/auth and Elasticsearch are required. | Mastodon software is open, but each instance has its own terms, robots policy, retention, and API configuration. Use only reviewed instances; store aggregate counts and source URLs, minimize post/user retention, and honor deletes. | Default [rate limit](https://docs.joinmastodon.org/api/rate-limits/) is 300 requests per five minutes per account and per IP, but operators can change it. There is no global search: status full-text results require server support and cover only public opted-in content. Historical depth is instance-specific. | Mature protocol/software; data availability is decentralized and variable. [`Mastodon.py`](https://github.com/halcy/Mastodon.py) 2.2.1 is MIT and current for Mastodon 4.5.8, but synchronous; repository pushed 2026-05-28. Direct async `httpx` is preferable. | Medium to high | Additional public attention samples and source links. | No market-wide denominator or completeness. Instance outages, policy variation, opt-in search, duplicate federated copies, and manual allowlist/app-token maintenance. |
| 3 | [Reddit Data API](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Reddit-Developer-Interfaces) with prior approval | Approved OAuth apps can access permitted posts/comments, timestamps, scores, URLs, and subreddit context. [`PRAW`](https://github.com/praw-dev/praw) 8.0.2 is BSD-2, Python 3.10+, and actively maintained as of 2026-07-13. | **Conditional, not a zero-subscription assumption.** The [Data API Terms effective 2026-07-01](https://redditinc.com/policies/data-api-terms) and [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy) require approval; commercial use needs permission/contract, and unapproved AI/ML training or commercial use is prohibited. PRAW’s license does not grant Reddit data rights. | Rate limits and access are app/contract specific; inspect response headers rather than assuming an old public quota. API history and search completeness are limited by approved endpoints. | Platform/API is material but policy and approval risk are high. Wrapper maintenance does not remove business approval. | High including approval | Potentially high-value ticker discussions and source links after written authorization. | Approval may be denied or paid; terms can change; deletions/privacy/moderation and account maintenance create obligations. No scraping fallback, OAuth evasion, or archived third-party dataset. |
| 4 | [Stocktwits](https://api.stocktwits.com/developers) approved API/Firestream | Symbol streams, message metadata, source links, and, for authorized products, sentiment details/charts. [Firestream](https://firestream-portal.stocktwits.com/documentation) uses authorized account credentials. | **Unavailable by default.** New API registrations are paused. [Terms updated 2026-04-09](https://stocktwits.com/about/legal/terms/) prohibit automated extraction except through an approved API or written authorization. | Contract/account-specific; no dependable anonymous quota or history. | Valuable finance-native population, but access is closed/conditional. | High including commercial negotiation | Strong fit only if Stocktwits grants access. | Cannot be part of the promised free baseline. Browser scraping violates the stated legal-durability requirement. |

### Financial-sentiment model

| Model/project | License / maintenance | Exact use | Compatibility / operating cost | Risks and controls |
|---|---|---|---|---|
| [ProsusAI FinBERT model](https://huggingface.co/ProsusAI/finbert), [repository](https://github.com/ProsusAI/finBERT) | Model/repository declares Apache-2.0. The original repository’s last push was in 2022, while the model remains widely downloaded. Run through current [`transformers`](https://pypi.org/project/transformers/) 5.13.x (Python 3.10+, released 2026-07-11 during review). | Classify permitted short texts as positive/negative/neutral. Pin the model revision and tokenizer; run in evaluation mode and batch off the MCP request path. | Python 3.10 compatible. Local inference avoids a paid API but downloads hundreds of MB of weights and consumes CPU/RAM; latency is hardware-dependent. `torch` materially increases the install footprint. | Apache licensing on code/weights does not erase provenance concerns in upstream training corpora (Financial PhraseBank and Reuters TRC2). Obtain model-governance/legal approval before a commercial release; use inference only, never fine-tune on restricted social content. Finance-news training may perform poorly on slang, sarcasm, emojis, and memes. Keep sentiment low-weight and validate against a fixed labeled fixture. |

### Recommended social computation

- Separate **attention** from **sentiment**. Attention is the count of accepted exact cashtags and unambiguous aliases, unique authors, and source-normalized posts per fixed time bucket. Sentiment is an optional aggregate over those accepted posts.
- Collect continuously in the background. Search APIs are not reliable retrospective counting systems, so the first 7–30 days are a warm-up period rather than instant “historical trend.”
- Compare a current seven-day bucket with the previous seven days and a rolling 28-day baseline. Require minimum volume before emitting a trend; otherwise return `insufficient_sample`.
- Deduplicate reposts/boosts and near-identical text. Count one author once per normalized message cluster per bucket. Record platform coverage and collector downtime so an outage cannot look like collapsing attention.
- Keep user data minimal: platform record ID, content hash, timestamps, language, cashtag match, derived score, and representative public URL. Avoid default display of usernames or full post bodies; apply deletion TTLs.
- Pin model revision, preprocessing, label mapping, and rounding. Run deterministic evaluation and round model probabilities before fixed scoring thresholds so minor cross-hardware floating-point differences do not change dossier bands.

---

## Recommended zero-subscription architecture

### Collection and evidence flow

```text
SEC submissions/archive ─┐
Issuer IR RSS/Atom ──────┼─> async collectors ─> raw hash + provenance ─> canonical event store
GDELT Project ───────────┘                                             │
                                                                      ├─> deterministic dedupe/event rules
Bluesky public API ──────┐                                             ├─> source-linked evidence
Mastodon allowlist ──────┴─> background social buckets ────────────────┤
                                                                      └─> Catalyst Edge scoring/dossier
Licensed options feed ─────> unavailable in zero-sub build; typed neutral missingness
```

### Runtime design

1. **Background-first ingestion.** Add a small collector process using the existing shared `httpx.AsyncClient`. MCP tools read a local snapshot and may perform one bounded high-value refresh, rather than crawling multiple sources serially during an 8-second request budget.
2. **SQLite/WAL local evidence store.** Recommended tables: `source_observation`, `canonical_event`, `event_source`, `insider_transaction`, `insider_cluster`, `social_bucket`, `collector_state`, and `source_policy`. Store raw bytes only where source terms allow; otherwise store a SHA-256 hash and parsed facts.
3. **Provenance envelope.** Every observation carries `source_id`, `source_tier`, `source_url`, `canonical_url`, `accession_or_record_id`, `published_at`, `observed_at`, `retrieved_at`, `raw_sha256`, `parser_name/version`, `model_revision`, `license_policy`, and `related_sources`.
4. **Bounded network policy.** Six-second connect/read budget per source, two concurrent requests per host by default, no unbounded retries, conditional GET, explicit `Retry-After` handling, and jittered background retries. GDELT gets a stricter one-request-per-five-seconds limiter. The outer adapter timeout remains eight seconds. A request-path timeout returns cached evidence plus freshness metadata.
5. **Source tiers.** Tier 1: SEC/regulator and issuer IR. Tier 2: original publisher/wire discovered through GDELT. Tier 3: social posts. Source tier affects confidence, not factual direction. Syndication count never multiplies evidence strength.
6. **Deterministic scoring.** Scoring reads normalized facts and fixed rules only. Model outputs are rounded inputs with a fixed low weight. Missing data is neutral; source failure and no event are distinct states.
7. **No hidden scraping stack.** No headless browser, proxy pool, CAPTCHA service, cookie farm, or account rotation. Sources that require those are unavailable.

### Exact integration manifest

| Layer | Integrate | Purpose |
|---|---|---|
| HTTP | Existing `httpx>=0.28` | Async SEC, GDELT, Bluesky, Mastodon, and RSS retrieval with shared timeout/retry policy. |
| SEC XML | `lxml>=6.1,<7` | Ownership and Form 144 XML parsing with namespace-safe XPath. |
| SEC optional extra | `edgartools>=5.42,<6` | Offline/backfill parsing and fixture cross-checks; not request-path transport. |
| Feeds | `feedparser>=6.0.12,<7` | Parse issuer and SEC RSS/Atom bytes fetched by `httpx`. |
| Dedupe | `rapidfuzz>=3.14,<4` | Deterministic normalized-title clustering. |
| Scale-up dedupe | Optional `datasketch>=2,<3` | MinHash/LSH only after event-volume measurements justify it. |
| Bluesky | Direct public XRPC through `httpx`; optional `atproto>=0.0.69,<0.1` | Avoid SDK churn for the one public search endpoint; use SDK only if firehose/repository operations are later approved. |
| Mastodon | Direct reviewed-instance APIs through `httpx` | Preserve async behavior and avoid a sync wrapper in the request path. |
| Sentiment | Optional `transformers>=5.13,<6`, compatible pinned `torch`, `ProsusAI/finbert` at an immutable revision | Background batched inference after legal/model-governance approval. Keep a deterministic non-model attention score if omitted. |

No new package changes should be made until the first SEC implementation phase chooses whether direct `lxml` alone is sufficient. Fewer dependencies are preferable to wrapping the same public endpoint several ways.

### Expected zero-subscription operating costs

| Cost | Local MCP | Hosted service |
|---|---|---|
| Data subscriptions | $0 for selected SEC, GDELT Project, Bluesky, and reviewed Mastodon/IR access; options flow unavailable | Same, subject to source terms and commercial review |
| Compute/storage | Existing workstation; SQLite, logs, cached metadata, and optional model disk/CPU | Small VM/container, persistent disk, backups, monitoring, and egress; not $0 in production |
| Human maintenance | Issuer-feed registry, source-policy review, parser fixtures, platform-policy monitoring | Same plus on-call/abuse handling and data-subject/deletion operations |
| Proxies/CAPTCHAs | $0 and prohibited by design | $0 and prohibited by design |
| Accounts/secrets | None for SEC/GDELT/Bluesky public; instance token may be needed for Mastodon | Secret rotation and instance approvals; Reddit/Stocktwits excluded until authorized |
| Model | Optional local CPU/RAM and several-hundred-MB weight download | Dedicated inference resources if throughput grows; no paid inference API required |

---

## Gap analysis

| Requirement | Zero-subscription status | What can be delivered | What remains impossible or materially weaker |
|---|---|---|---|
| Forms 3/4/5 transactions and ownership | Strong | Complete public filings, transaction/holding rows, derivatives, relationships, footnotes, source links, ownership changes | Filing corrections and complex footnotes still require careful parsing; no guarantee a disclosure reflects economic discretion |
| Planned sales | Strong but correctly qualified | Form 144 proposed sales and 10b5-1 indicators/plan dates | Form 144 is notice/intent, not an executed sale; some sales fall below filing threshold |
| Insider clusters | Strong derived signal | Transparent clusters by distinct insiders, code, time window, and issuer | Cluster semantics must exclude grants/exercises/gifts and distinguish planned sales |
| Material events and earnings | Strong | 8-K/6-K items, exhibits, issuer IR releases, accepted/published time, primary links | Issuer feeds require per-site maintenance; disclosures can lag the underlying event |
| Broad credible news | Moderate | GDELT discovery, source-domain diversity, primary-source canonicalization, deduplicated coverage | No licensed full article corpus; three-month DOC search horizon; completeness and article availability are not guaranteed |
| True options flow | **Unavailable** | A typed, neutral gap and a future licensed-adapter boundary | No reliable trade premium, aggressor, large-print sequence, sweep/block detection, or consolidated trade/quote coverage without OPRA/vendor rights |
| EOD options activity | Conditional, not default | OCC volume/OI could support daily call/put and unusual-aggregate analysis after written permission | Public website terms currently block automated commercial use; even approved data is not flow |
| Social attention | Moderate from collection start | Bluesky plus reviewed Mastodon mention buckets, unique-author counts, source links, transparent coverage | No complete market-wide denominator, guaranteed history, or stable cross-platform sample |
| Reddit/Stocktwits finance-native sentiment | Unavailable by default | Optional adapter after written commercial approval | Approval, contract, possible fees, account maintenance, and policy change; scraping is prohibited |
| Sentiment accuracy | Moderate/experimental | Pinned FinBERT inference over legally collected text with low deterministic weight | Training-data provenance review, domain shift to slang/sarcasm, language coverage, model footprint, and calibration work |

The principal strategic gap is options, not insiders or filings. A paid generic finance API is not necessary to create the dossier, but a licensed options feed is necessary to claim real flow.

---

## Phased implementation plan

### Phase 0 — correct the contract and evidence schema

**Effort:** 1–2 days · **Risk:** low

- Add typed `source_status` values: `available`, `no_observations`, `stale`, `rate_limited`, `permission_required`, and `licensed_feed_required`.
- Add the provenance envelope and source-policy registry.
- Rename the yfinance result to `options_chain_snapshot` and prevent it from satisfying `options_flow` coverage.
- Decide whether `options_eod_activity` is a new noncanonical family or a separately labeled observation under an options budget. Do not enable OCC collection without written permission.
- Add fixtures that prove missing options/social sources remain neutral in deterministic scoring.

### Phase 1 — direct SEC insider and material-event ingestion

**Effort:** 4–7 days · **Risk:** low to medium · **Priority:** highest value per engineering hour

- Implement submissions/archive fetching with fair-access throttling, cache validators, and raw hashes.
- Parse Forms 3/4/5 and 144 into normalized transactions/holdings/planned sales.
- Parse 8-K/6-K item numbers and exhibit metadata; identify EX-99.1 earnings/press releases without headline-only direction inference.
- Implement transaction-code semantics, ownership deltas, plan flags, and distinct-insider clusters.
- Cross-check fixed filings against EdgarTools and SEC-rendered pages.

### Phase 2 — issuer feeds, GDELT discovery, and canonical event graph

**Effort:** 5–8 days · **Risk:** medium

- Create a reviewed issuer-feed registry for an initial liquid-ticker cohort.
- Add conditional RSS/Atom fetch and health monitoring.
- Add bounded GDELT DOC queries for company legal name, ticker/cashtag, and exclusion aliases.
- Implement exact and fuzzy deduplication, primary-source tiering, corrections/versioning, and `related_sources`.
- Measure false merge/split rates before adding MinHash.

### Phase 3 — social attention collection

**Effort:** 5–10 days plus warm-up · **Risk:** medium

- Add Bluesky public search collection and a small reviewed Mastodon instance allowlist.
- Build minute/hour/day buckets, unique-author counts, dedupe, collector-uptime accounting, and ambiguity controls.
- Warm the system for at least 14 days before emitting change-over-time bands.
- Add optional pinned FinBERT inference only after the model/license review and labeled-fixture acceptance test.
- Keep Reddit and Stocktwits feature-gated behind explicit authorization records.

### Phase 4 — options decision gate

**Effort:** business/legal discovery first · **Risk:** high

- Request written OCC clarification only if end-of-day aggregate activity has enough product value to justify it.
- Obtain OPRA/vendor quotes for a future licensed transaction/quote feed and classify the MCP architecture for non-display/query/redistribution use.
- Implement true flow only after rights are documented. Until then, keep `options_flow` unavailable and exclude it from denominator-based coverage claims.

### Phase 5 — dossier calibration and operational hardening

**Effort:** 5–8 days · **Risk:** medium

- Run deterministic scoring fixtures, clock/timezone tests, stale-cache tests, source-policy expiry checks, and duplicate-event audits.
- Benchmark collection under the eight-second MCP deadline using cached/background-first behavior.
- Add source health and provenance completeness to the dossier, so users can distinguish no catalyst from missing evidence.

---

## Proof-of-concept validation plan

Use real public tickers with different failure modes: **AAPL** (dense Forms 4/144 and news), **NVDA** (earnings/news volume), **TSLA** (high social ambiguity/volume), **BRK.B / BRK-B** (symbol normalization), and **RKLB** or another smaller issuer (low-volume coverage). Run against the latest completed market day; never assume same-day EOD data is final.

| Test | Source(s) | Procedure | Pass criteria |
|---|---|---|---|
| SEC identity and archive resolution | SEC submissions/archive | Resolve each ticker to CIK; fetch recent filing metadata; for ten Forms 4 and two Form 144 filings, use archive index/basename to fetch XML. | 100% accession/source links resolve; accepted times and hashes stored; rate stays <=2 rps; no XSL display-path error. |
| Ownership parsing | SEC XML + EdgarTools cross-check | Compare reporting owner, relationship, transaction code/date, shares, price, A/D, post-holdings, direct/indirect ownership, derivatives, footnotes, and 10b5-1 flags for fixed AAPL/NVDA filings. | Exact match on disclosed scalar fields; missing values remain null; parser difference produces a failing fixture, not silent coercion. |
| Planned-sale semantics | SEC Form 144 | Parse seller, relationship, proposed shares/value/date, broker, past sales, and plan-adoption date; trace any later Form 4 separately. | Dossier labels Form 144 “proposed”; it never reports execution without a separate filing; sub-threshold caveat is present. |
| Insider clustering | Derived SEC | Run fixed 7/30-day windows and hand-audit all transaction codes for five issuers. | Only qualifying open-market purchases/sales enter their respective clusters; grants/exercises/gifts/tax withholding do not inflate the cluster. |
| Material-event extraction | SEC 8-K/6-K | Parse recent NVDA/AAPL 8-K items and EX-99 exhibits; compare to SEC index and rendered filing. | Correct item numbers, filing/issuer/exhibit links, accepted time, and primary source; direction is absent unless supported by an explicit deterministic rule. |
| Issuer-feed registry | Reviewed IR feeds | Configure at least three issuers with published RSS/Atom; exercise ETag/Last-Modified and simulate a moved/broken feed. | No duplicate on 304; broken feed is `stale`, not “no news”; canonical issuer URL retained; only terms-approved content stored. |
| GDELT discovery and dedupe | GDELT DOC 2.0 + SEC/IR | Query NVDA around an earnings event and TSLA around a high-coverage event. Cluster same-event syndicated links and select the SEC/IR primary where present. | At least 95% of hand-labeled duplicates merge without merging two distinct material events; every cluster retains all source URLs; article bodies are not stored. |
| Bluesky attention | Public AppView | Probe both documented unauthenticated AppView hosts from the deployment network, then query exact `$TSLA`, `$NVDA`, and ambiguous aliases; collect hourly for seven days and replay fixed JSON fixtures. | At least one official host works without a proxy; cashtag matches are reproducible; ambiguous bare tokens rejected; cursor/rate handling bounded; deleted/repost data handled; source links resolve; coverage marked partial. If both official hosts fail, the source is `unavailable`, not scraped through a browser. |
| Mastodon attention | Two or three reviewed instances | Search public opted-in statuses using each instance’s supported auth and record instance coverage/downtime. | Per-instance counts and source links are correct; no result is presented as global Mastodon volume; instance failure cannot lower the trend silently. |
| Sentiment determinism | Pinned FinBERT revision | Label at least 30 permitted examples: earnings beat/miss, neutral filings, negation, sarcasm, slang, emoji, and mixed statements. Run twice on the target CPU. | Byte-identical label/bucket outputs after fixed preprocessing/rounding; acceptable confusion matrix is documented; otherwise sentiment remains disabled while attention ships. |
| Options integrity negative test | Adapter contract | Run without a licensed OPRA adapter; provide yfinance-like chain and OCC-shaped fixtures. | `options_flow.available` remains false; no sweep, block, aggressor, or premium field is emitted; dossier score is neutral with `licensed_feed_required`. |
| Timeout and provenance | All selected collectors | Inject 429, 500, malformed XML/feed, slow socket, stale cache, and redirect loops. | MCP call returns within eight seconds; partial cached evidence is labeled with freshness; every fact has a source/provenance record; no retry storm. |

Do not call OCC batch endpoints in the automated POC until written permission resolves the conflict between documented batch examples and the website terms. Do not activate Reddit or Stocktwits tests without approved credentials and commercial authorization.

---

## Final recommendation

Build the free version now around direct SEC ownership/material-event parsing, a curated issuer-feed registry, GDELT discovery with primary-source deduplication, and bounded Bluesky/Mastodon attention collection. Those sources support a defensible differentiated dossier because the product value comes from evidence joining, transaction semantics, novelty, provenance, and deterministic confidence—not from wrapping a single quote/news API.

Do **not** promise true options flow in the free tier. Treat it as a licensed capability gate. Also do not promise market-wide social sentiment: report the actual platform sample, collection window, and downtime. This honest boundary produces a stronger product than relabeling free chain snapshots or fragile scraped posts as institutional-quality data.

**Verdict: partially achieved for free.** Three of the four requested needs can produce meaningful, legally durable inputs at zero subscription cost, with social breadth explicitly limited. The fourth—real options transaction flow—requires licensed OPRA-derived data and recurring commercial cost. The product specification vision remains viable if differentiated synthesis and provenance are the delivery boundary and unavailable sources remain neutral; it is not fully satisfied if all four families must have institutional-grade live coverage on a zero-dollar data budget.
