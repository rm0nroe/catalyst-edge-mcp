# Catalyst Edge MCP — combined free-data recommendation

**Date:** 2026-07-13

**Status:** reconciled recommendation for product specification/technical specification revision and implementation

**Source reports:** [Codex research](./codex-catalyst-edge-free-data-research.md) · [Claude research](./claude-catalyst-edge-free-data-research.md)

## Executive decision

**Proceed with the project, but narrow the product promise.** Catalyst Edge remains worthwhile as a primary-source catalyst intelligence layer: a source-linked, deterministic dossier that explains what changed, how important it is, which evidence agrees or conflicts, how confident the system should be, and what an analyst should verify next.

It is not viable as a zero-subscription substitute for institutional options flow or comprehensive retail-social data. The free, commercially durable product can be strong in SEC insider activity and material events, useful in issuer/news discovery, and explicitly partial in public social attention. True options transaction flow remains a licensed future capability.

The combined verdict is therefore **partially achieved for free**:

- **Insider activity:** strong and production-worthy from direct SEC data.
- **Company events/news:** strong for primary disclosures; moderate for broad news discovery.
- **Options activity:** true flow unavailable without OPRA-derived licensed data.
- **Social attention:** useful but incomplete; sentiment should begin as experimental and low-weight.

This research covered the four requested data needs, not the technical specification’s fifth canonical `technical` family. The current technical adapter depends on FMP, while yfinance does not convey commercial data rights. A zero-subscription commercial release must either accept `technical` as neutrally missing or require a user-supplied/licensed OHLC provider; this report does not claim that gap is solved.

The moat is not access to free endpoints. It is the evidence graph, transaction semantics, primary-source ranking, deduplication, change detection, confidence discipline, and MCP ergonomics.

## Reconciliation of the two source reports

### Conclusions retained

- Replace FMP insider dependence with direct SEC submissions and ownership XML.
- Use maintained SEC tooling to validate parsers and accelerate offline backfill.
- Use direct `httpx` collection for production async behavior and bounded timeouts.
- Use SEC 8-K/6-K exhibits and issuer releases as authoritative event evidence.
- Use GDELT Project for discovery and coverage context, not as the source of truth.
- Treat Bluesky as a partial attention sample and disclose its limited finance coverage.
- Exclude unapproved Reddit and Stocktwits collection.
- Do not call yfinance chain snapshots “flow.”
- Do not attempt to reverse-engineer free sweeps, blocks, or aggressor-side premium.
- Preserve the existing deterministic scoring and neutral-missingness principles.

### Corrections applied

| Topic | Final determination |
|---|---|
| Finnhub free company news | Technically available at 60 calls/minute, but the [free plan is licensed for personal use](https://api.finnhub.io/pricing). It is not a default commercial source without written Finnhub approval. |
| yfinance | Library code is Apache-2.0, but its [README says Yahoo data is intended for personal use](https://github.com/ranaroussi/yfinance). It may remain a development/private-user diagnostic adapter, not a commercially cleared production source. |
| OCC public reports | OCC documents batch endpoints, but its [website terms prohibit automated commercial exploitation](https://www.theocc.com/specialpages/legal/terms-and-conditions). Do not automate or productize them without written permission. |
| SEC “public domain” | Do not apply a blanket public-domain claim to issuer-authored filings. SEC-authored government material, issuer filings, exhibits, and embedded third-party material are not legally identical. Store parsed facts, identifiers, hashes, and source links; avoid indiscriminate full-text redistribution. |
| SEC freshness | The [submissions API updates in real time](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), typically within a second of dissemination—not merely in a nightly ownership batch. |
| GDELT rate limit | A live 2026-07-13 `429` response instructed callers to limit requests to one every five seconds. Treat that as the current operational ceiling and future 429 instructions as authoritative. |
| Bluesky authentication/rates | Public AppView reads are unauthenticated. The [AppView limit is described as generous but unspecified](https://docs.bsky.app/docs/advanced-guides/rate-limits); the 5,000-point figure applies to repository writes, not search reads. |
| Bluesky host reliability | `public.api.bsky.app` returned a CDN 403 from the current network while the documented `api.bsky.app` host returned valid JSON. Probe both official hosts; never solve reachability with proxies or scraping. |
| FinVADER license | FinVADER is Apache-2.0, not MIT, and its README advertises Python 3.8–3.11. It requires compatibility and quality testing before use in a Python 3.10+ package. |
| ProsusAI FinBERT license | The GitHub code repository is Apache-2.0, but the [published Hugging Face model metadata](https://huggingface.co/api/models/ProsusAI/finbert) has no explicit weight-license field. Keep disabled pending model-weight and training-corpus review. |
| Current launch-readiness test | The technical specification currently hard-codes SEC plus a fresh directional FMP, Finnhub, or true-flow provider. New free sources do not satisfy that gate until the technical specification and smoke tests are intentionally revised. |
| Technical family | Outside the requested four-source exercise and still unresolved for a commercial zero-subscription build. Do not use yfinance to imply that commercially licensed OHLC history exists. |

---

## Final source ranking

## 1. Insider activity

| Rank | Source/project | Data and access | Commercial/legal status | Limits/freshness/history | Python/async fit | Effort | Final use |
|---:|---|---|---|---|---|---|---|
| 1 | [SEC submissions API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), ownership XML, and [Form 144](https://www.sec.gov/files/form144.pdf) | `GET https://data.sec.gov/submissions/CIK##########.json`, then archive XML by accession. Forms 3/4/5 provide reporting owner, role, transaction code/date, shares, price, acquired/disposed, holdings, direct/indirect ownership, derivatives, footnotes, and 10b5-1 indicators. Form 144 provides proposed-sale details and plan dates. No key; identifying user agent required. | Best available primary source. Store facts and links; do not assume all embedded filing content is unrestricted government-authored material. | SEC ceiling 10 rps across machines; run at 2 rps/concurrency 2. Submissions are near-real-time; archives provide long history. | Excellent with existing `httpx.AsyncClient`; parse locally. | Medium | Required production source. |
| 2 | [`lxml`](https://pypi.org/project/lxml/) | Namespace-safe local ownership/Form 144 XML parsing. | BSD-style permissive license. | No external rate/freshness constraint. | Python 3.10+ compatible; parsing is synchronous CPU work after async fetch. | Low | Required parser unless a standard-library implementation proves sufficient. |
| 3 | [EdgarTools](https://github.com/dgunning/edgartools) | Typed Forms 3/4/5, Form 144, 8-K items, exhibits, and tables. Version 5.42.0 was current during review; MIT; active through 2026-07-09. | Code is commercially permissive; underlying SEC provenance still governs the evidence. | Inherits SEC limits. | Python 3.10+, but network/API use is synchronous. | Low offline; medium if isolated | Optional backfill, fixture generation, and parser cross-check—not request-path transport. |
| 4 | [`sec-edgar-downloader`](https://github.com/jadchaar/sec-edgar-downloader) | Controlled filing download and backfill. MIT, Python 3.10+, active through 2026-06-22. | Commercially permissive code; underlying SEC rules apply. | Built-in SEC limiter; SEC history. | Synchronous and downloader-only. | Low | Optional fixtures/backfill only. |

### Insider scoring semantics

- Preserve the technical specification definition that two distinct insiders in one direction form a cluster, but distinguish cluster strength:
  - two distinct insiders: `cluster`;
  - three or more distinct insiders: `strong_cluster`.
- Open-market purchase code `P` can be bullish with disclosed price/value.
- Sale code `S` uses lower confidence, especially when planned or accompanied by Form 144/10b5-1 context.
- Grants, exercises, gifts, tax withholding, conversions, and derivative movements are not equivalent to discretionary open-market trades.
- Form 144 is proposed intent, not completed execution.
- Every computed ownership delta must retain the underlying accession, reporting owner, footnotes, and post-transaction holdings.

## 2. Company news and material events

| Rank | Source/project | Data and access | Commercial/legal status | Limits/freshness/history | Python/async fit | Effort | Final use |
|---:|---|---|---|---|---|---|---|
| 1 | SEC 8-K/6-K filings and exhibits | Item numbers, accepted time, documents, EX-99 earnings/press releases, and primary archive links through submissions/archive APIs. | Primary public filing evidence; store parsed facts, hashes, and links. | Near-real-time SEC dissemination; long history; 10 rps ceiling. | Direct async `httpx` + local parsing. | Medium | Required authoritative event source. |
| 2 | Curated issuer IR/newsroom RSS/Atom | Official release title, publication time, canonical URL, category, and attachments. Discover standard feed declarations and maintain a reviewed issuer registry. | Conditional per issuer. Public access does not automatically license full-text redistribution. Store metadata and factual extraction unless terms authorize more. | No universal SLA/history. Poll every 5–15 minutes with `ETag`/`Last-Modified`; honor robots and issuer terms. | Async fetch + [`feedparser`](https://github.com/kurtmckee/feedparser) for local parsing. | Medium for a focused universe; high at broad scale | Required for an initial high-value issuer cohort; expand based on demand. |
| 3 | [GDELT Project DOC 2.0](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) | Article URL, title, seen date, domain, language/source metadata, and tone. Direct endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`. | GDELT Project is free/open, but publisher article text remains publisher-controlled. Store metadata, derived clusters, and source links only. | Rolling three-month DOC search; raw GDELT 2 from 2015; about 15-minute update cadence. Limit to one request per five seconds based on current live response. | Excellent via direct `httpx`; no wrapper needed. | Medium | Discovery, coverage breadth, and syndication clustering—not factual authority. |
| 4 | SEC RSS/Atom | Latest filings, ownership filters, litigation/releases, and regulatory notices. | SEC public-information rules. | Courtesy feeds; schedules and formats can change. | Async fetch + feedparser. | Low | Wake-up trigger reconciled against canonical SEC APIs. |
| Excluded by default | Finnhub free company news | Company-news metadata and URLs, 60 calls/minute, one-year free coverage. | Free plan is personal-use only. Written commercial approval required. | Vendor plan-dependent. | Existing adapter can support it if authorized. | Low technically | Feature-gated approved provider only. |

### Event deduplication and provenance

1. Normalize issuer to CIK and reviewed aliases.
2. Create exact fingerprints using CIK, accession/canonical URL, normalized title, and published minute.
3. Remove tracking parameters while preserving original and resolved URLs.
4. Cluster same-issuer stories within 48 hours using RapidFuzz token-set ratio `>=92`; add MinHash only if measured volume requires it.
5. Rank canonical evidence: SEC/regulator or issuer IR, then original publisher/wire, then syndication copy.
6. Preserve all alternate links in `related_sources`; score the event cluster once.
7. Treat corrections and materially changed numbers as linked versions, not duplicates.
8. Never derive event direction solely from headline sentiment. Only explicit allowlisted event mappings or disclosed numeric facts may set direction.

## 3. Options activity

| Rank | Source/project | Data and access | Commercial/legal status | Freshness | Final use |
|---:|---|---|---|---|---|
| 1 | [OPRA](https://www.opraplan.com/) through a licensed vendor/direct feed | Consolidated option trades and quotes required for premiums, trade/quote sequence, quote-side inference, sweeps, blocks, calls/puts, strikes, expirations, and volume/OI context. | Paid agreements required. The [fee schedule](https://cdn.opraplan.com/documents/OPRA_Fee_Schedule.pdf) includes non-display, subscriber, and redistribution fees; classification depends on the product architecture. | Real-time or delayed by entitlement. | Only path to true production flow; future licensed adapter. |
| 2 | OCC EOD volume/OI reports | Clearing aggregates, option symbol, call/put, account type/exchange, volume, and OI. | Do not automate commercially under current website terms without written permission. | EOD, not flow. | Optional `options_eod_activity` only after permission; never `options_flow`. |
| 3 | [yfinance](https://github.com/ranaroussi/yfinance) | Chain snapshot fields such as strike, expiration, last/bid/ask, volume, and OI. | Upstream data is described as personal-use; no commercial entitlement conveyed by the library. | Undocumented, no SLA. | Development/private diagnostic only; not production evidence. |
| Rejected | Cboe delayed web endpoints, undocumented APIs, Barchart scraping, open-source scanners | Delayed display pages or heuristics over chain snapshots. | Programmatic extraction or redistribution is not licensed for this product. | Variable. | None. |

### Required product behavior

- Zero-subscription production returns:

  ```json
  {
    "family": "options_flow",
    "available": false,
    "reason": "licensed_transaction_feed_required",
    "degraded_proxy_used": false
  }
  ```

- Do not let chain snapshots or daily aggregates satisfy `options_flow` availability or launch coverage.
- Keep a provider interface ready for future licensed trade-plus-quote ingestion.
- Sweep, block, and aggressor labels must remain transparently derived even after a licensed feed is added.

## 4. Social attention and sentiment

| Rank | Source/project | Data and access | Commercial/legal status | Limits/freshness/history | Python/async fit | Effort | Final use |
|---:|---|---|---|---|---|---|---|
| 1 | [Bluesky AppView](https://docs.bsky.app/docs/advanced-guides/api-directory) | Public posts, timestamps, AT URI/CID, facets/links, and ranked cashtag search. Use `https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts` with documented `https://api.bsky.app` fallback. No authentication. | Public API use is supported, but users retain content rights. Store minimal metadata, derived aggregates, and representative links; honor deletion/takedown. | AppView rate is generous but unspecified. Search is ranked and incomplete; no guaranteed historical totals. Collect forward. | Direct async `httpx` preferred; optional [`atproto`](https://github.com/MarshalX/atproto) is MIT/pre-1.0. | Medium | Primary free attention sample, always marked partial. |
| 2 | [Mastodon API](https://docs.joinmastodon.org/methods/search/) on reviewed instances | Public opted-in statuses, timestamps, URLs, hashtags, boosts/replies, and instance search results. | Instance-specific terms and API policy; no global license or global index. | Default 300 calls/5 minutes per account and IP, but instance operators vary it. History/search completeness varies. | Direct async `httpx`. | Medium-high | Optional corroborating attention sample. |
| Excluded by default | Reddit Data API | Approved posts/comments, metadata, and URLs. | Commercial access requires approval/contract under current terms. No scraping or archived third-party substitute. | Contract-specific. | PRAW is maintained but does not grant data rights. | High | Authorized adapter only. |
| Excluded by default | Stocktwits | Finance-native messages, symbol streams, and sentiment metadata. | New API registration is paused; automated extraction outside approved APIs is prohibited. | Contract-specific. | No approved baseline. | High | Revisit only after written access. |

### Sentiment decision

Ship **attention first**, sentiment second:

- Attention is deterministic: exact cashtag/alias matches, unique authors, deduplicated posts, time-bucket counts, and change versus collected baselines.
- Generic [VADER](https://github.com/cjhutto/vaderSentiment) is MIT and deterministic, but finance-language accuracy must be measured before it influences scoring.
- [FinVADER](https://github.com/PetrKorab/FinVADER) is Apache-2.0 and deterministic, but advertises Python only through 3.11 and had no code push after 2023 during review. Treat as an evaluation candidate, not an automatic dependency.
- ProsusAI FinBERT remains disabled until the published model weights and training-corpus rights receive explicit approval.
- Any enabled sentiment result is low-weight, source-scoped, and rounded before fixed thresholds. Social attention must never be described as market-wide sentiment.

---

## Recommended zero-subscription architecture

```text
SEC submissions/archive ─┐
Issuer IR feeds ─────────┼─> async background collectors ─> source observations
GDELT Project ───────────┘                                  │
                                                            ├─> canonical event graph
Bluesky AppView ─────────┐                                  ├─> deterministic change rules
Mastodon allowlist ──────┴─> time-bucketed attention ───────┤
                                                            ├─> provenance and confidence
Options-flow adapter ──────> unavailable until licensed ────┘
                                                                    │
                                                                    └─> MCP catalyst dossier
```

### Runtime components

1. **Background collectors:** keep multi-source crawling out of the eight-second MCP request budget. Request-time refresh is limited to one high-value call when cache age and remaining deadline permit.
2. **SQLite/WAL evidence store:** `source_observation`, `canonical_event`, `event_source`, `insider_transaction`, `insider_cluster`, `social_bucket`, `collector_state`, and `source_policy`.
3. **Provenance envelope:** source ID/tier, source and canonical URLs, accession/record ID, published/observed/retrieved times, raw SHA-256, parser version, model/lexicon revision, license policy, and related sources.
4. **Per-source policy:** SEC 2 rps/concurrency 2; GDELT one request per five seconds; Bluesky/Mastodon use returned headers and backoff; issuer feeds use conditional GET.
5. **Bounded failures:** six-second source timeout, eight-second outer adapter timeout, no unbounded retry, cached partial result with freshness, and distinct `no_observations`, `stale`, `rate_limited`, `permission_required`, and `licensed_feed_required` statuses.
6. **No scraping infrastructure:** no browser crawler, residential proxy, CAPTCHA solver, cookie farm, or credential rotation.

### Dependency recommendation

| Dependency | Decision |
|---|---|
| Existing `httpx`, Pydantic, MCP SDK | Keep. |
| `lxml>=6.1,<7` | Add for ownership/Form 144 XML unless standard-library parsing passes all fixtures. |
| `feedparser>=6.0.12,<7` | Add for RSS/Atom parsing. |
| `rapidfuzz>=3.14,<4` | Add for deterministic duplicate clustering. |
| `edgartools>=5.42,<6` | Optional extra for backfill and validation only. |
| `atproto` | Optional; direct XRPC through `httpx` is preferred initially. |
| VADER/FinVADER | Evaluation extras only until compatibility and labeled accuracy gates pass. |
| Transformers/FinBERT | Do not add in the zero-subscription MVP. |

---

## Required technical specification revisions before implementation

The current technical specification assumes FMP/Finnhub keys and a provider-name-based launch gate. The new architecture requires an explicit design revision before code changes.

1. **Approved source matrix**
   - Production baseline: SEC, reviewed issuer feeds, GDELT Project, Bluesky AppView, reviewed Mastodon instances.
   - Conditional: authorized Finnhub, Reddit, Stocktwits, OCC, and future OPRA vendor.
   - Development/private only: yfinance unless commercial rights are separately obtained.
   - Technical: user-supplied/licensed OHLC provider or typed neutral missingness; no zero-subscription source is approved by this research.
2. **Source-quality constants**
   - SEC filing/ownership: `1.00`.
   - Issuer IR release: `0.95`.
   - GDELT-discovered publisher metadata: initial `0.60–0.70`, further constrained by domain tier.
   - Bluesky attention: initial `0.50–0.60`, explicitly partial.
   - Mastodon attention: initial `0.40–0.50`, instance-scoped.
   - Options flow: unavailable without licensed feed; no proxy quality constant.
3. **Launch readiness**
   - Replace provider-name gating with evidence semantics.
   - Require SEC provenance plus at least one fresh directional observation from direct insider activity, an allowlisted material event, or an explicitly authorized provider.
   - Require correct typed missingness for every unavailable canonical family.
4. **Options semantics**
   - `options_flow.available=true` only for a licensed transaction-plus-quote source.
   - Remove production coverage credit from yfinance.
5. **Social semantics**
   - Attention and sentiment are separate observations.
   - No trend before minimum warm-up/sample thresholds.
   - Collector downtime is included in coverage so outages cannot become bearish signals.
6. **Tests and documentation**
   - Add source-policy fixtures, license/permission states, rate-limit behavior, parser drift, source-host fallback, and model-disabled behavior.
   - Update environment matrix, launch smoke, examples, traceability matrix, and warnings.

---

## Phased implementation plan

### Phase 0 — revise the technical specification and contracts

**Effort:** 1–2 days · **Risk:** low

- Approve the source matrix and product wording above.
- Add typed source-status and provenance fields.
- Correct options availability and launch-readiness semantics.
- Add tests showing unavailable options/social remain neutral.

### Phase 1 — direct SEC insiders and events

**Effort:** 4–7 days · **Risk:** low-medium · **Priority:** highest

- Implement direct submissions/archive collection and fair-access controls.
- Parse Forms 3/4/5, Form 144, 8-K/6-K item/exhibit metadata.
- Implement transaction-code semantics, planned-sale context, ownership change, and cluster strength.
- Cross-check fixed filings with EdgarTools and rendered SEC filings.

### Phase 2 — issuer feeds and event graph

**Effort:** 4–7 days · **Risk:** medium

- Add an initial reviewed issuer-feed registry.
- Implement conditional RSS/Atom retrieval and health monitoring.
- Add canonical event/source tables and exact/fuzzy deduplication.
- Validate corrections, syndication, and primary-source ranking.

### Phase 3 — GDELT discovery

**Effort:** 2–4 days · **Risk:** medium

- Add serialized one-per-five-seconds DOC queries and caching.
- Apply issuer aliases and domain-quality tiers.
- Store metadata/links only and attach coverage to existing primary events.

### Phase 4 — social attention

**Effort:** 5–8 days plus warm-up · **Risk:** medium

- Add official Bluesky AppView host probing and direct search collection.
- Add a very small reviewed Mastodon allowlist only if Bluesky coverage is insufficient.
- Collect buckets for at least 14 days before emitting trend bands.
- Evaluate VADER and FinVADER on labeled finance/social fixtures; keep sentiment disabled if accuracy or compatibility fails.

### Phase 5 — dossier validation and hardening

**Effort:** 5–8 days · **Risk:** medium

- Evaluate 20–30 historical catalyst cases.
- Measure primary-link validity, event precision/recall, duplicate merge/split errors, source freshness, and analyst time saved.
- Update deterministic thresholds based on documented evaluation, not anecdote.

### Future licensed gate — options flow

- Obtain OPRA/vendor classification and quotes.
- Add a provider only after rights cover non-display analysis, storage, and any customer-facing derived output.
- Ingest both trades and quotes; preserve sequence and distinguish observed facts from sweep/aggressor inference.

---

## Proof-of-concept validation

Use **AAPL**, **NVDA**, **TSLA**, **BRK.B/BRK-B**, and **RKLB** plus one issuer with a recent 8-K selected at runtime.

| Test | Pass criteria |
|---|---|
| SEC identity/archive | Ticker-to-CIK and accession resolution is exact; archive XML resolves; no XSL display-path bug; requests remain <=2 rps. |
| Ownership parsing | Reporting owner, role, code/date, shares, price, A/D, holdings, ownership form, derivatives, footnotes, and 10b5-1 flags match fixed filings. |
| Planned sales | Form 144 remains “proposed”; later execution is not inferred without separate evidence. |
| Insider clusters | Two-insider clusters and three-plus strong clusters are deterministic; grants/exercises/gifts/tax events do not inflate them. |
| Material events | 8-K/6-K item numbers, exhibits, accepted times, and primary URLs match SEC; unsupported direction remains neutral. |
| Issuer feeds | Conditional GET prevents duplicates; moved/broken feeds become stale, not “no news”; only terms-approved content is retained. |
| GDELT | One-per-five-seconds limiter holds; source URLs resolve; publisher bodies are not stored; primary/secondary duplicates collapse without merging distinct events. |
| Bluesky | At least one documented official host works without a proxy; cashtag matches are reproducible; ambiguous aliases are rejected; coverage is marked partial. |
| Mastodon, if enabled | Counts remain instance-scoped; instance failure cannot silently reduce trend. |
| Sentiment, if enabled | Fixed preprocessing produces byte-identical rounded outputs; labeled finance fixture meets a documented acceptance threshold. |
| Options integrity | Without a licensed adapter, `options_flow.available` remains false; no sweep/block/aggressor/premium evidence is emitted from chain/OCC fixtures. |
| Timeout/provenance | 429, 500, malformed data, slow sockets, and stale cache return within eight seconds with complete status and provenance. |

### Product validation gate

Continue investing only if the 20–30 case evaluation shows:

- at least 95% of surfaced evidence links resolve to the claimed source;
- material-event and transaction classification errors are rare and visible through fixtures;
- duplicate clustering does not materially overstate independent confirmation;
- the dossier saves analysts meaningful manual research time;
- users value “what changed / why / confidence / what to check next” beyond a raw SEC search.

If those outcomes do not hold, adding more feeds will not rescue the product.

## Final recommendation

Proceed with Phase 0 and Phase 1. The project is defensible when it becomes the best evidence-first catalyst dossier over legally durable primary sources. It is not defensible if it markets free chain snapshots as flow, personal-use APIs as commercial data, or incomplete public-post searches as market-wide sentiment.

The zero-subscription release should lead with SEC insider and material-event intelligence, source hierarchy, deduplication, change detection, and confidence. Issuer feeds and GDELT broaden the evidence graph; social attention is optional corroboration; options flow is an explicitly licensed future module.

**Final verdict: worth building, partially achievable for free, and stronger when the unavailable data is modeled honestly instead of imitated.**
