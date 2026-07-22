# Catalyst Edge free/open-source coverage research

**Access date:** 2026-07-21
**Repository baseline:** `main` at `9fbc569b8421874a451907497af922217a38783a`
**Scope:** U.S. equities and ETFs; owner-operated collection; no repository or Axe runtime changes made during research.

## Executive recommendation

Proceed with a small, source-neutral quality PR before adding another feed. The current product already has the right durable backbone: official SEC filings and ownership records, reviewed issuer-primary feeds, GDELT discovery, and Bluesky partial attention. The most valuable next work is to make entity acceptance, rejection, coverage, and grouped-source support explicit.

The recommended free/owner-operated stack is:

1. SEC submissions, daily indexes, filing archives, ownership XML, fund series/class identifiers, N-CEN, and N-PORT as primary regulatory evidence.
2. Reviewed issuer and fund-sponsor release/feed/page metadata as primary issuer evidence.
3. GDELT raw GKG/Mentions/Web NGrams metadata as discovery only, after deterministic issuer-resolution gates.
4. The raw AT Protocol repository event stream for prospective social collection, with commit-signature, DID-identity, and message-chain verification; AppView search remains a partial diagnostic, and Jetstream is not the research archive.
5. Wikidata and OpenFIGI only as registry-discovery/cross-check inputs, never as unreviewed evidence or a point-in-time security master.
6. Technical/OHLC and true options flow remain unavailable unless the owner supplies appropriately licensed data.

This improves real watchlist output without weakening provenance or pretending free sources solve market-data rights.

## Current product boundary and observed gaps

The current repo composes SEC filings/ownership, reviewed issuer feeds, cache-only GDELT discovery, and Bluesky partial attention. Its `Source` contract already records publication, observation, and retrieval timestamps; canonical identifiers/URLs; hashes; parser versions; policy decisions; and correction lineage. Missing families are typed and move scoring toward neutral rather than bearish.

Four concrete defects remain:

- The reviewed registry contains only AAPL, NVDA, TSLA, RKLB, and BRK-A/BRK-B; only AAPL and NVDA have issuer feeds. It contains positive aliases but no negative aliases or required issuer-context terms.
- GDELT Web NGrams matching is deterministic alias containment, which allowed two unrelated or insufficiently specific TSLA matches in the 14-ticker test.
- A grouped insider claim may have more support internally than the public response shows because each evidence object currently exposes at most three sources. That made the seven-insider GOOGL cluster under-cited.
- The MCP has typed family statuses but no reason taxonomy for `source_unsupported`, `entity_rejected`, `discovery_only`, or `evaluated_not_material`, and no native RESEARCH NOW/MONITOR/IGNORE field. Downstream `IGNORE` therefore conflates an evaluated negative result with absence of supported evidence.

The evidence store is a strong operational event graph, but it is not a historical replay ledger: policy/config versions are not append-only, rejected entity matches are not retained, and there is no query for “exact normalized evidence visible as of T.”

## Source and component matrix

| Family | Candidate | Verified access and fields | History/revision behavior | Rights and operating burden | Recommended role |
| --- | --- | --- | --- | --- | --- |
| Corporate filings and ownership | [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), filing archives, Forms 3/4/5/144 | No-key JSON submissions and XBRL APIs; immutable accession paths; real-time dissemination; nightly bulk submissions/company facts | Submission JSON includes older-file pointers; amendments are separate filings. Freeze accession metadata and payload hash rather than relying on current aggregates alone. | Follow SEC automated-access policy and identifying user agent. Retain parsed facts, identifiers, hashes, and links; do not assume every issuer-authored exhibit is government-authored public-domain text. | Primary evidence and historical backbone |
| Funds and ETFs | [SEC N-CEN datasets](https://www.sec.gov/data-research/sec-markets-data/form-n-cen-data-sets), [SEC data library/N-PORT](https://www.sec.gov/data-research/sec-markets-data), [series/class IDs](https://www.sec.gov/submit-filings/filer-support-resources/how-do-i-guides/obtain-update-investment-company-series-class-ids) | N-CEN is annual as-filed fund metadata; N-PORT contains monthly portfolio holdings; official series/class IDs carry names, tickers, and status | Quarterly dataset publication and filing/amendment chronology must be preserved. N-PORT is not daily holdings truth. | Public filing data with the same content-retention caution as other EDGAR material. Medium parsing and identifier-linking burden. | Primary fund identity/filing lane; delayed holdings context |
| Issuer/sponsor primary | Official IR/newsroom RSS/Atom, sitemaps, JSON-LD, release indexes | Publication date, canonical URL, title/category, attachment links, HTTP validators, structured metadata | Page changes are not a revision log. Collector must store first-seen time, hash, validators, and correction lineage. | Host-by-host review; metadata/factual extraction only unless terms allow more. Medium ongoing registry burden. | Primary evidence for a reviewed cohort |
| Broad news discovery | [GDELT data/GKG/Mentions](https://www.gdeltproject.org/data.html), [current Web NGrams announcement](https://blog.gdeltproject.org/using-the-new-web-ngrams-dataset-to-find-relevant-coverage/) | Raw files/BigQuery; URL, source domain, dates, organizations/themes, event mentions; 15-minute GKG/Mentions updates; current minute-level Web NGrams quadgrams with table-of-contents URL/title metadata | Useful historical metadata but not a publisher article-version archive. The current Web NGrams service is explicitly an interim surface during GDELT's infrastructure migration, so its schema/access must be treated as provisional. A repeated URL/mention is not independent confirmation. | GDELT metadata is open; publisher content remains publisher-controlled. High data volume. | Discovery and duplicate/corroboration context only |
| Entity registry discovery | [Wikidata data access](https://www.wikidata.org/wiki/Wikidata%3AData_access), [OpenFIGI v3 API](https://www.openfigi.com/api/documentation) | Wikidata CC0 dumps/APIs; OpenFIGI maps identifiers to FIGI/ticker/name/exchange and permits free public API access with lower unauthenticated limits | Neither endpoint is a sufficient point-in-time security master. Current mappings may reflect later edits/renames. | Wikidata structured data is CC0. OpenFIGI data use still requires review of applicable terms; API documentation alone is not a redistribution grant. | Candidate alias/identifier suggestions requiring human review |
| Local entity matching | [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz), [spaCy](https://github.com/explosion/spaCy) | Maintained MIT projects; deterministic fuzzy matching and local NER/pipelines | Model/library versions must be frozen. Generic NER does not establish issuer identity. | Low runtime rights burden; model weights need separate review if used. | RapidFuzz for tested deterministic rules; spaCy research-only until benchmarked |
| Social forward collection | [AT Protocol firehose](https://docs.bsky.app/docs/advanced-guides/firehose) and [repository sync specification](https://atproto.com/specs/sync), repository records, deletion/account events | Raw repository event stream from relays/PDSes; stable repo DID, collection, record key/URI, CID, commit sequence, record timestamps. Research ingestion must verify commit signatures, DID identity, and message-chain continuity rather than treating relay receipt alone as authentication. | Complete only from the collector start plus any verified backfill. Must record outages, deletes, tombstones, account status, verification failures, and replay cursor. | Public records remain user-authored content; minimize retention and honor deletions/takedowns. Medium-high operations. | Prospective partial-attention corpus |
| Social convenience stream | [Bluesky Jetstream](https://docs.bsky.app/blog/jetstream) | JSON stream, collection/repo filters, lower bandwidth | Bluesky explicitly says Jetstream is not protocol-stable/self-authenticating and is unsuitable for archives or research studies. | Easy to operate but inappropriate as the authoritative research record. | Prototype/monitoring only, not the backtest archive |
| Technical/OHLC | [Alpha Vantage](https://www.alphavantage.co/documentation/), [Alpaca](https://docs.alpaca.markets/us/docs/about-market-data-api), [Tiingo](https://www.tiingo.com/about/pricing), Nasdaq Data Link, Stooq, Yahoo/yfinance | Capabilities range from adjusted daily data to SIP bars and corporate actions | Free sources generally do not guarantee inactive-security completeness, frozen revisions, or historical identifier continuity | Alpha Vantage default terms are personal/non-commercial; Tiingo distinguishes individual/internal-commercial/redistribution; Alpaca market-data agreements constrain commercial exploitation; Yahoo/yfinance is personal-use oriented; Stooq lacks a sufficiently explicit product license/API contract for this use. | Owner-supplied licensed adapter only; do not approve a free commercial default |
| Options | [OPRA access model](https://www.opraplan.com/), [Cboe options data services](https://www.cboe.com/data/market-data-services/us/options/), OCC/exchange aggregates | OPRA-class trade and quote records support transaction/quote sequence; public exchange pages provide only aggregates/reference subsets | Daily volume/open interest or delayed chains cannot reconstruct aggressor, sweep, block, or full historical quote context | OPRA vendor/subscriber/non-display/redistribution agreements and fees apply. Public pages remain subject to site terms. | True flow stays unavailable; aggregates must use non-flow names |

## Separate ETF/fund evidence lane

Corporate issuer semantics should not be copied onto SPY, QQQ, DIA, IWM, XLE, XLK, GLD, or GDX.

The fund lane should use:

- SEC registrant CIK plus series and class IDs as canonical identity, with ticker aliases versioned separately.
- N-CEN for annual fund structure/classification and N-PORT for reported monthly holdings, always labeled by report/end/filing dates.
- Sponsor-primary product notices, prospectus/supplement filings, fee/index changes, creation/redemption or closure notices where officially published.
- Index-provider notices only when access and output rights are approved.
- Constituent/sector/macro evidence as a derived exposure view, not as if the ETF itself made a corporate disclosure.

The first ETF/fund-lane implementation should classify unsupported fund families explicitly. It should not infer real-time holdings changes from N-PORT or treat constituent news volume as independent ETF catalyst evidence.

## Five highest-value quick wins

1. **GDELT entity-resolution registry v2.** Add required terms, negative aliases, exact ticker rules, issuer/brand/subsidiary context, and deterministic accept/reject reason codes. Retain rejected match metadata and hashes for a precision corpus.
2. **Complete grouped-claim support.** Keep the compact evidence body, assign an immutable claim ID, and add a paginated claim-source query that recovers every unique source ID/accession supporting that claim. This directly fixes the GOOGL cluster citation gap without overloading the current bounded response.
3. **Coverage and disposition reason codes.** Add scoped reason records for `observed_none`, `source_unavailable`, `source_unsupported`, `entity_rejected`, `discovery_only`, and `evaluated_not_material` to MCP diagnostics. Each record identifies its source/candidate/family/disposition scope; multiple reasons may coexist. A deterministic display precedence is separate from the retained reason set. The consuming agent can map that set to RESEARCH NOW/MONITOR/IGNORE; this PR does not pretend the MCP already owns that three-class product decision.
4. **Reviewed primary-source expansion.** Add a review tool that proposes official issuer/sponsor feed, sitemap, JSON-LD, and newsroom endpoints, but requires a checked registry entry before collection. Start with the 14-ticker test universe and the named ETF cohort.
5. **Prospective AT Protocol collector.** Store verified firehose cursor/commit metadata, minimal post identifiers, cashtag/entity decision, deletion state, bucket coverage, and outage intervals. Keep sentiment disabled until a labeled finance-language benchmark passes.

## Exact first PR

**PR title:** `Harden GDELT entity resolution and expose rejected-match audit data`

Scope:

- Bump the reviewed registry to version 2 with per-alias rules: alias kind, match mode, required context, negative context, valid-from/to dates, canonical CIK, rule version, and review provenance.
- Add a deterministic `EntityDecision` model with `accepted`, `reason_code`, matched aliases/context, source URL/domain, publication time, retrieval time, and raw hash.
- Apply the decision before a GDELT observation enters the canonical event graph.
- Persist rejected metadata in an append-only `entity_match_audit` table; publisher bodies remain unretained and query/output pages remain bounded.
- Add TSLA false-positive fixtures plus positive Tesla/Tesla Energy cases and ambiguous-word fixtures for the existing reviewed cohort.
- Expose aggregate rejection counts/reasons in diagnostics, not in scoring.

Out of scope: new feeds, ETF parsing, source-appendix response changes, scorer tuning, social collection, and paid market data.

## Acceptance gates

| Gate | Required result before enabling a new source/rule |
| --- | --- |
| Entity precision | At least 98% precision and 85% recall on a frozen corpus of at least 300 labeled candidates; zero cross-issuer collisions and zero known negative-alias or TSLA false-positive leaks |
| Event semantics | At least 95% precision for directional event types; unsupported wording remains neutral |
| Duplicate clustering | At least 98% correct pair decisions; no distinct-event merge among high-materiality cases |
| Primary-link validity | At least 99% of surfaced primary links resolve to the claimed official source/accession |
| Provenance completeness | 100% source ID, canonical record/URL, publication/acceptance, observed, retrieved, hash where payload was fetched, parser/rule version, and policy decision |
| Grouped claims | 100% of counted records recoverable through an immutable claim ID and paginated claim-source query; compact display truncation is explicit |
| Freshness | Source-specific SLA and collector outage intervals represented; no outage becomes `observed_none` |
| ETF coverage | Every supported fund resolves CIK + series/class ID; holdings include report/end/filing dates; unsupported fields are typed |
| Degradation | Fixed tests assert the exact ordered set of scoped reasons; unsupported, unavailable, no observations, rejected entity, discovery-only, and evaluated-not-material may coexist without information loss |

## Prioritized follow-ups

- **PR 1:** GDELT entity-resolution registry v2 and rejected-match audit corpus.
- **PR 2:** Immutable claim IDs, paginated grouped-source recovery, and disposition reason taxonomy.
- **PR 3:** ETF/fund identity and SEC N-CEN/N-PORT adapter, initially neutral and research-only.
- **PR 4:** Reviewed issuer/sponsor primary-source discovery workflow and registry expansion.
- **PR 5:** Verified AT Protocol prospective collector with commit/DID/message-chain validation and outage/deletion accounting.
- **Research-only:** spaCy/entity-linker comparison, OpenFIGI/Wikidata suggestion quality, sentiment models, index-provider rights, and any OHLC/options vendor.

## Not achievable for free

- Consolidated historical options trades plus quotes with contractual rights sufficient for aggressor, sweep, block, and product output.
- Complete retrospective finance-social counts. Ranked search and convenience streams are not full history; prospective collection can only be complete relative to recorded uptime and scope.
- A commercially cleared, survivor-bias-free U.S. security master plus adjusted/unadjusted price history, delisted outcomes, and frozen revisions from the candidates reviewed here.
- Universal issuer/sponsor archive completeness. Official sites vary, correct pages, and rarely promise historical retention.

## Go/no-go

**Go** on the entity-resolution/auditability PR and the later SEC fund lane. **No-go** on adding a broad news feed, sentiment weight, free OHLC default, or options-flow proxy before the corresponding rights and benchmark gates pass.
