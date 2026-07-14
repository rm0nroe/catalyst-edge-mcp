# Catalyst Edge MCP — Free/OSS Data Sourcing Research
**Date:** July 13, 2026 | **Against:** product specification + technical specification (deterministic_v1 scorer, 5 canonical families)

## 0. Framing against the actual technical specification

The technical specification already locks in a specific dependency shape:

| Family | Current technical specification source | Paid? | Failure mode if unfunded |
|---|---|---|---|
| `filings_news` | SEC (free) + FMP news (`FMP_API_KEY`) | Partially | Missing FMP key → news half of family lost |
| `insider_trading` | FMP insider-trading/search | **Fully paid** | Missing FMP key → **entire family missing** |
| `options_flow` | FlowAlgo/CheddarFlow, yfinance degraded fallback | Real flow: paid. Fallback: free | Already honestly degraded (confidence capped 0.45) |
| `technical` | FMP technical-indicators | Fully paid | Missing FMP key → family missing (out of scope here) |
| `social` | Finnhub social-sentiment | Paid endpoint | Missing key → family missing |

Your 4 questions map directly onto closing the paid dependencies in rows 1, 2, and 5, and confirming row 3 (options) is legitimately unsolvable for free. That's exactly what I found. All candidates below are evaluated against the technical specification's actual adapter contract: `AdapterResult` shape, documented source-quality constants, dedup key `(family, signal, timestamp, canonical_source_url)`, 6s request / 8s outer timeout, fail-closed on schema drift, no invented URLs.

---

## 1. Insider activity (SEC Forms 3/4/5)

| Rank | Source | Exact data | Access | License / commercial use | Rate limits / freshness | Reliability / maintenance | Effort | Satisfies | Risks / gaps |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **edgartools** (`dgunning/edgartools`) — github.com/dgunning/edgartools | Parses Form 3/4/5 ownership XML into typed transactions: insider name/role, transaction code, shares, price, derivative vs non-derivative, footnotes (incl. Rule 10b5-1 plan flags where the filer discloses them) | Python lib, wraps `data.sec.gov/submissions/CIK{cik}.json` + EDGAR archive XML | **MIT**, free commercial use, no API key required (just an identity string) | Inherits SEC's 10 req/s fair-access cap; lib defaults to 9 req/s. Freshness = EDGAR's own (Form 4 legally due within 2 business days; ownership forms disseminated nightly ~10pm ET) | 2.1k GitHub stars, 3,764 commits, 148 releases, latest v5.31.1 (May 2026), 1000+ tests, single very active maintainer, ships an MCP server itself | **Low** | Transaction detail, ownership changes, source-linked provenance (constructs real EDGAR archive URLs) | Single-maintainer bus-factor; you still must implement the technical specification's own cluster/planned-sale *classification* logic (≥2 distinct insiders same direction = cluster; 10b5-1-flagged sales get lower confidence) — the library gives raw fields, not that judgment |
| 2 | Raw `data.sec.gov` submissions + ownership XML (DIY, no library) | Same underlying data as #1 | Direct httpx GET, exact endpoints already named in your technical specification §6 | US govt work, public domain (17 U.S.C. §105), zero restriction | Same 10 req/s SEC-wide cap | N/A — you own it | **Medium** (hand-write the `ownershipDocument` XML schema parser) | Same as #1 | More code to maintain than #1 for no data-quality gain; only worth it if you want zero third-party dependencies in the insider adapter |
| 3 | `sec-edgar-toolkit` (stefanoamorelli) — dual Python/TS SDK with explicit `Form4Parser`/`Form5Parser` | Same form coverage, narrower scope (parsing only, no XBRL/financials) | Python lib | Open source (verify exact license tag before adopting) | Same SEC ceiling | Smaller community than edgartools; treat as a secondary/fallback parser, not primary | Low-Medium | Same as #1 | Less battle-tested than edgartools; redundant if #1 is adopted |
| — | OpenInsider (openinsider.com) | Pre-aggregated insider-cluster screens | **HTML scrape only, no public API** | Unclear ToS on automated/redistributed access | N/A | N/A | — | — | **Excluded** — violates your own "no fragile browser scraping / ToS evasion" rule. Fine as a human sanity-check, never as an adapter. |

**Verdict — Need 1: fully achievable for free, and it's a strict upgrade, not just a substitute.** SEC primary filings already carry source-quality 1.00 in your own table vs. FMP's 0.85. Swapping the insider adapter from FMP to edgartools + direct SEC XML removes the "no FMP key → insider family dark" failure mode entirely and gets you *higher*-quality evidence at zero cost. This is the single highest-value, lowest-risk item in this whole research.

---

## 2. Company news and material events

| Rank | Source | Exact data | Access | License / commercial use | Rate limits / freshness | Reliability / maintenance | Effort | Satisfies | Risks / gaps |
|---|---|---|---|---|---|---|---|---|---|
| 1 | SEC 8-K via SEC/edgartools (already in your architecture) | Item-classified material events (1.01, 2.02, 5.02, etc.), full text | Same SEC endpoints | Public domain | 10 req/s SEC cap; same-day-ish | Same as insider row | Low (already designed) | Material events, primary source, 1.00 quality | No change needed — this row confirms your existing design is already correct |
| 2 | **GDELT DOC 2.0 API** — api.gdeltproject.org/api/v2/doc/doc | Article URL, title, seen-date, domain, source country, language, crude tone score. **Does not host or redistribute article text** — only metadata + link back to the primary outlet | Plain unauthenticated `GET` with querystring params (call directly with `httpx`; skip wrapper libraries — the API surface is trivial and a direct call avoids wrapper-maintenance risk) | GDELT is a Google/Georgetown-backed open academic project; because it never republishes full article text, you're not carrying anyone else's copyright — you're only storing a URL, which is exactly what your `canonical_source_url` dedup key wants | No published hard quota (be a reasonable citizen); rolling **3-month** search window only, updates every 15 min | Live since 2016, heavily used in academic literature (multiple 2025-2026 papers cite it), FCO-built public web UI still active | **Low** | Deduplication of syndicated coverage (same headline across N domains = one story, not N confirmations), provenance linking, discovery of coverage outside SEC filings | Breadth-over-precision: indexes some low-quality domains — mitigate with a domain allowlist/quality tier; no deep history (3-month cap is fine for a 14-90 day lookback tool) |
| 3 | **Finnhub `/company-news`** — genuinely free tier, distinct from the paid `/stock/social-sentiment` endpoint your technical specification already keys to `FINNHUB_API_KEY` | Headline, summary, URL, source, datetime | REST, `X-Finnhub-Token` header, same key you already provision for social | Free tier: 60 calls/min, no separate cost | 60 req/min free; near-real-time | Well-documented, enterprise-run (ex-Google/Bloomberg team), widely used | **Low** (you already have the adapter and the key — this is one more endpoint call) | Second confirming news source, reduces reliance on FMP news specifically | Still an aggregator, not primary; treat at ~0.80 quality like your existing Finnhub row |
| — | Company IR-page / press-release RSS (per-ticker) | Primary press releases | No universal free API — would require a hand-maintained ticker→RSS-URL map | N/A | N/A | Fragile at scale | **High** for broad coverage | Marginal | Not recommended for v1 — same "don't scope-creep like MediaCrawler" logic your product specification already applies elsewhere. Revisit only if a specific high-value ticker needs it. |

**Verdict — Need 2: largely achievable for free.** SEC 8-K (already free) + GDELT (new, zero-cost, legally clean because it never stores full text) gives you a second independent, dedup-capable `filings_news` source that satisfies the technical specification §14 launch-readiness bar ("at least one fresh directional family from FMP, Finnhub, or a true-flow provider") without spending on FMP news specifically. Finnhub's already-free news endpoint is a good third leg using a key you already have.

---

## 3. Real options activity — the one hard "no"

**Direct answer to your explicit question: OPRA licensing makes reliable, free, *commercial* transaction-level options flow legally impossible, full stop.** This isn't a data-availability gap — it's a licensing wall:

- OPRA (the SIP for all listed US options) requires a **Vendor Agreement** to redistribute its data at all, with a flat **$1,500/month redistribution fee**, plus per-subscriber fees on top.
- "Non-Display Use" — consuming OPRA data on the backend to compute a score *without ever showing raw quotes to a user* — **still requires a license**. Your MCP tool, which ingests trade/quote data to produce a score, would count as non-display use even if it never renders a raw options tape.
- The "Non-Professional Subscriber" personal-use exemption (no fee, but strict: individual capacity only, "not in connection with any trade or business activity," can't be furnished to any other person) does not cover a product built for Crown Capital LLC.
- This is why every paid retail options-flow product (Unusual Whales, FlowAlgo, CheddarFlow, Market Data, OptionCharts) is either an OPRA Vendor itself or resells one — there is no free tier of *any* of them that includes true flow, because the underlying license cost is a fixed floor none of them can discount away.

| Rank | Source | What it actually gives you | Free? | Verdict |
|---|---|---|---|---|
| 1 | yfinance chain snapshot (**already in your technical specification**, `degraded=true`, confidence capped 0.45) | Current call/put open interest and volume per contract, no trade-level ticks, no sweep/block, no aggressor side | Yes | Correctly the best free option; nothing below beats it |
| 2 | Polygon.io/Massive free tier | 5 calls/min, EOD or 15-min-delayed chain only, no trade prints on free tier | Yes but worse | **Not an upgrade** — more restrictive than yfinance's effective throughput, adds a second degraded provider for zero new capability. Skip it. |
| 3 | CBOE/OCC end-of-day total volume+OI files | Daily aggregate put/call totals per underlying, no strike/expiration granularity | Yes | Could feed a crude put/call-ratio *technical* signal, not `options_flow`-grade; medium effort for low payoff, not recommended for v1 |
| 4 | Barchart "unusual options" free screener | Vol/OI-ratio screen, delayed, website-only | Yes, but **no documented API** | Excluded — scrape-only, same ToS problem as OpenInsider |
| 5 | Open-source "build your own UOA scanner" blog projects | Same vol/OI-ratio math your yfinance fallback already encodes, sourced from the same free chain snapshots | Yes | No incremental capability — concept already validated by your existing design, no new library needed |

**Verdict — Need 3: not achievable for free at the bar you defined** (sweeps, blocks, premium, aggressor side, volume vs. OI at the trade level). This is exactly why your technical specification already treats yfinance as degraded rather than as flow — that design is correct and there is no free way to close the gap. The only way to get real flow is to pay FlowAlgo, CheddarFlow, a Polygon paid tier, Databento, or another OPRA-licensed reseller — your technical specification already accounts for this correctly via `CATALYST_EDGE_OPTIONS_PROVIDER`.

---

## 4. Social attention and sentiment

| Rank | Source | Exact data | Access | License / commercial use | Rate limits / freshness | Reliability / maintenance | Effort | Satisfies | Risks / gaps |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Bluesky / AT Protocol** — `app.bsky.feed.searchPosts` (cashtag/keyword search; simpler than consuming the raw firehose) | Post text, author, timestamp, engagement counts, `$TICKER` cashtag search | Free App Password or OAuth account, no developer review queue; official `atproto` Python SDK (MarshalX/atproto), MIT | Free for any use per current Bluesky docs; no redistribution ban found for aggregate-signal use of public posts | ~5,000 points/hour per account (reads are generous); real-time via firehose, near-real-time via search index | Bluesky-run infra, actively developed (relay migrations logged through 2026), SDK widely used | **Low-Medium** | Ticker mention volume, change over time, source-linkable posts | **Coverage risk**: financial-discussion density on Bluesky is materially smaller than Reddit/X/Stocktwits, especially for small/mid-caps — best as one signal among several, not the sole social source |
| 2 | Mastodon public API | Public timeline/search on instances that allow unauthenticated read (ActivityPub is an open protocol) | Free, no auth for public data on cooperative instances | Open protocol, no central ToS | Per-instance, generally generous | Federated — reliability varies by instance | Low | Same as above | Very low finance-discussion density — not worth adapter investment for v1, note as available and deprioritize |
| 3 | GDELT GKG `timelinevol`/`timelinetone` (reused from Need 2) | Volume + tone timeline of *press* attention to a keyword — a proxy for media buzz, not retail chatter | Same free GDELT access as above | Same as above | Same as above | Same as above | Low (already integrated for news) | Confirming "media attention" signal, cheap bonus | Not a substitute for actual social-platform mentions — different population |
| — | **Reddit official API** | Posts/comments from r/wallstreetbets, r/stocks, etc. | OAuth | **Free tier explicitly bars commercial use** ("monetizing applications built on free tier access violates terms of service"); commercial tier is ~$12,000/yr+, and Reddit separately bars using its content to train models without consent | 100 req/min free tier | N/A | — | — | **Excluded.** Crown Capital LLC / Catalyst Edge MCP is a commercial product — the free tier cannot legally be used, and unofficial scraping (PRAW against a non-compliant app, or reviving Pushshift-style archives) is exactly the ToS-evasion your requirements rule out. This is the single biggest social-coverage loss versus what a paid Finnhub/Quiver-style aggregator likely blends in under its own commercial license. |
| — | Stocktwits API | Trending symbols, message stream, sentiment tags | REST | **Developer registration is currently closed** — official page states they are "reviewing all of our APIs, documentation and terms" and not accepting new signups | N/A while closed | Unknown — in flux | — | — | **High risk, not recommended for v1.** Don't build a primary dependency on an API that isn't presently onboarding new developers; revisit periodically. |

**Sentiment scoring (mention counting isn't sentiment):**

| Rank | Model | License | Fit |
|---|---|---|---|
| 1 | **VADER / FinVADER** (lexicon-based, no model weights, pure Python) | MIT | Best fit for this codebase specifically — fully deterministic and auditable, which matches `scoring_method=deterministic_v1` far better than a neural model does. Zero inference cost, trivial to unit-test byte-for-byte. |
| 2 | `yiyanghkust/finbert-tone` or `ProsusAI/finbert` (HuggingFace transformer) | **Ambiguous** — neither model card exposes an unambiguous OSS license tag as of this research; verify explicitly (or pick a clearly Apache-2.0/MIT-tagged fine-tune) before shipping in a commercial product | Higher accuracy ceiling than VADER on nuanced text, but treat the licensing question as **open, not resolved** — don't assume "on HuggingFace" means "cleared for commercial embedding" |

**Verdict — Need 4: partially achievable for free.** Bluesky + GDELT give a legally clean mention/attention signal, and VADER/FinVADER gives a fully free, deterministic sentiment layer consistent with your scoring philosophy. But the two largest purpose-built retail-sentiment sources — Reddit and Stocktwits — are closed off (one by commercial ToS, one by a closed developer program), so total social coverage/recall will be visibly thinner than what a paid Finnhub-style aggregator provides. This is a real, disclosable coverage gap, not just an inconvenience — say so in `data_quality.warnings` when the social family is Bluesky-only.

---

## Deliverable 2 — Recommended zero-subscription architecture

Changes relative to technical specification §2/§6, keeping the existing adapter protocol and family budgets untouched:

```text
catalyst_edge_mcp/adapters/
  sec.py                 # unchanged — already free/primary
  sec_insider.py         # NEW — wraps edgartools (MIT) for Form 3/4/5;
                          #        retires the FMP insider-trading/search dependency
  gdelt.py                # NEW — direct httpx client for GDELT DOC 2.0;
                          #        second/confirming filings_news provider
  fmp.py                  # unchanged, but now optional for filings_news/insider —
                          #        keep only for `technical` (out of this research's scope)
  finnhub.py              # EXTENDED — add the already-free /company-news call
                          #        alongside the existing paid social-sentiment call
  bluesky.py              # NEW — app.bsky.feed.searchPosts + local FinVADER scoring;
                          #        primary `social` source, ahead of/instead of paid Finnhub social
  options.py              # unchanged — FlowAlgo/CheddarFlow optional paid,
                          #        yfinance degraded free fallback (no free upgrade exists)
```

Net effect: `filings_news`, `insider_trading`, and `social` become servable at **$0 marginal data cost**, using only compute/hosting you already pay for. `FMP_API_KEY` becomes relevant only for the `technical` family (indicators), which is outside your 4 stated needs. `options_flow` is unchanged because no free path exists.

---

## Deliverable 3 — Exact libraries, repos, endpoints, models to integrate

| Component | Package / endpoint | Install |
|---|---|---|
| Insider (Forms 3/4/5) | `edgartools` — github.com/dgunning/edgartools | `pip install edgartools` |
| Filings/news discovery | GDELT DOC 2.0 — `https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=artlist&format=json` | plain `httpx`, no install |
| News (free tier) | Finnhub — `GET https://finnhub.io/api/v1/company-news?symbol=&from=&to=&token=` | `pip install finnhub-python` (or reuse existing httpx client) |
| Social mentions | Bluesky AT Protocol — `GET https://bsky.social/xrpc/app.bsky.feed.searchPosts?q=%24TICKER` | `pip install atproto` |
| Sentiment scoring | VADER / FinVADER | `pip install vaderSentiment` (finance-lexicon extensions available on PyPI; verify current maintenance before pinning) |
| Options (unchanged) | `yfinance` degraded fallback | already in your stack |

---

## Deliverable 4 — Gap analysis (what remains impossible or materially weaker without paid data)

| Gap | Why | Materiality |
|---|---|---|
| True options flow (sweeps, blocks, premium, aggressor side) | OPRA vendor licensing ($1,500/mo redistribution fee + per-subscriber fees + non-display-use licensing) — a legal ceiling, not an engineering one | **Hard, permanent gap.** Only closes by paying FlowAlgo/CheddarFlow/Polygon-paid/Databento. |
| Reddit-grade social coverage | Free tier ToS explicitly bars commercial use; paid tier ~$12,000/yr | **Real coverage loss** — biggest single retail-sentiment source is unavailable to this product for free |
| Stocktwits | Developer program currently closed to new signups | **Temporary, not legal** — revisit periodically; don't build around it now |
| Breadth/latency of aggregated news vs. a paid provider | GDELT batches every 15 min and has a 3-month lookback ceiling; Finnhub free news is solid but narrower than FMP's licensed aggregation | **Modest** — SEC+GDELT+Finnhub-free covers the "at least one fresh directional family" bar, but small-cap/international breadth will lag a paid aggregator |
| FinBERT-class model commercial licensing | No explicit OSS license tag confirmed on the model cards checked | **Open question** — resolve before shipping, or default to VADER/FinVADER which has unambiguous MIT licensing |

---

## Deliverable 5 — Phased implementation plan (highest-value, lowest-risk first)

1. **`sec_insider.py` via edgartools.** Pure upside: primary-source quality upgrade (1.00 vs. FMP's 0.85), zero legal risk, zero cost, removes a single-point-of-failure (FMP key) from a canonical high-weight family (12-point budget).
2. **`gdelt.py` + extend `finnhub.py` with the free `/company-news` call.** Dual-sources the `filings_news` family, wires into your existing `(family, signal, timestamp, canonical_source_url)` dedup key, satisfies technical specification §14 launch-readiness without paying for FMP news.
3. **`bluesky.py` + VADER/FinVADER.** New `social` adapter; ship with an explicit `data_quality` warning noting Bluesky-only coverage is narrower than Reddit/Stocktwits-inclusive commercial aggregators.
4. **Optional, lower priority:** CBOE EOD put/call ratio as a bonus `technical` input; Mastodon as a bonus `social` confirming signal. Do these only if phases 1-3 are stable and there's spare capacity.
5. **Never:** chase free options flow (it doesn't exist); build a Reddit or unregistered-Stocktwits integration for a commercial product.

---

## Deliverable 6 — Proof-of-concept test plan

**Tickers:** NVDA (mega-cap, high volume across all families — stresses throughput/pagination), one mid-cap with a recent real 8-K (pick dynamically at test time), one thin small-cap (stresses graceful no-data/partial-coverage paths), one recently-uplisted ticker (stresses CIK-mapping edge cases in `company_tickers_exchange.json`).

For each ticker, assert:
- `edgartools` returns ≥1 Form 4 in the trailing 90 days for NVDA-class tickers, and a clean empty result (not an exception) for the thin small-cap.
- GDELT returns ≥1 article with a resolvable, real URL (no invented links) for NVDA-class tickers.
- Duplicate GDELT hits for the same underlying story across multiple domains collapse under your existing dedup key.
- Bluesky search returns a nonzero post count for a high-attention ticker and zero (gracefully, not an error) for an obscure one.
- VADER/FinVADER sentiment scores are **byte-for-byte deterministic** across repeated runs on identical input — this is a hard requirement given `scoring_method=deterministic_v1`.
- Simulated provider throttling/unreachability on each new adapter respects the 6s request / 8s outer timeout and degrades to the correct `missing_families` / warning entries instead of raising.
- The yfinance options path is never mislabeled as flow in any generated summary text (grep for the word "flow" adjacent to yfinance-sourced evidence).

---

## Deliverable 7 — Verdict

**Partially achieved — and on the three families where it's achievable, it's an upgrade, not a compromise.**

Three of your four canonical families (`insider_trading`, `filings_news`, `social`) can be met at **zero marginal data cost** while staying fully inside the technical specification's existing adapter/provenance/timeout contract — and in the insider case specifically, the free source (SEC primary filings via edgartools) is *higher quality* than the paid source it replaces (1.00 vs. 0.85 on your own source-quality scale).

The fourth (`options_flow` at true-transaction-level) is **not achievable for free**, and that's a legal ceiling — OPRA's redistribution and non-display-use licensing — not a research or engineering gap. Your technical specification already encodes the honest answer to this (degraded yfinance fallback, capped confidence, explicit "flow unavailable" warning); nothing free closes that gap, and nothing should pretend to.

Net effect on the product specification's actual differentiation thesis: **it still holds, and arguably gets stronger.** The product specification's bet is "evidence synthesis and confidence," not "we quietly resell someone else's paid flow data." A dossier built on primary-source SEC insider evidence, deduplicated multi-source news with real provenance, and a legally clean (if narrower) social-attention signal — explicitly caveated wherever options flow is degraded — is a more defensible, more source-linked product than one that thinly wraps a paid aggregator. That's the exact trap the product specification already told you to avoid.
