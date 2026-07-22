# Catalyst Edge point-in-time backtest dataset research

**Access date:** 2026-07-21
**Repository baseline:** `main` at `9fbc569b8421874a451907497af922217a38783a`
**Decision target:** a defensible minimum 1,000-observation historical replay, not a semantic fixture set presented as performance evidence.

## Executive recommendation

Use a build-and-license hybrid:

- **Build and freeze the evidence side:** SEC filings/ownership, issuer-primary metadata, GDELT raw metadata, parser versions, entity decisions, deduplication, and scorer/config snapshots.
- **License the label and security-master side:** for a Stage A corpus beginning 2018-05-01, evaluate three separately licensed components: Databento Corporate Actions, Databento Security Master, and Tiingo EOD. Their combined price and rights are unknown until quoted in writing. This trio is only a conditional Stage A candidate because none of the reviewed materials establishes a CRSP-style terminal-return field.
- **Require a verified terminal-outcome source for Stage B:** CRSP is the preferred reviewed source. An enterprise alternative is acceptable only if it contractually covers inactive/delisted identity, final consideration or delisting returns, retention, calibration, and aggregate reporting.
- **Do not require options or retrospective social data for the first backtest.** Mark those families unavailable. Begin verified AT Protocol repository-event collection prospectively for future vintages.

[Databento documents](https://databento.com/docs/venues-and-datasets/corporate-actions) point-in-time corporate-action records from 2018-05-01, while its [Security Master](https://databento.com/security-master) is a separate product with separate quote/symbol-based pricing. [Tiingo advertises](https://www.tiingo.com/about/pricing) 30+ years of EOD history and a $50/month internal-commercial base tier, but its [symbology documentation](https://www.tiingo.com/documentation/appendix/symbology) says delisted coverage is limited to tickers not yet recycled. Its standard terms also require written approval for the intended retained backtest, benchmarking, and report use. The published prices therefore do not establish a licensed bundle or a complete terminal-return source.

[CRSP states](https://www.crsp.org/research/) that PERMNO remains fixed for the life of a security and tracks restructurings; its U.S. Stock database covers active and inactive securities. It remains the preferred benchmark or replacement if licensed access is available.

**Decision:** Draft the provider-neutral Stage A technical specification now. Implement the 50–100-observation Stage A only after the identity, lifecycle, price, retention, and derived-use rights are confirmed in writing. Do not start the 1,000-observation Stage B, purchase data, or call `deterministic_v1` backtested until a terminal-outcome source is also contracted and verified.

## Why the current corpus is not a backtest

The current 28 synthetic cases validate response contracts, missingness, and direction semantics. The 25 real SEC cases validate official links, accepted timestamps, bounded classification, deduplication, and dossier behavior. Neither corpus contains forward prices, returns, controls, costs, delisting outcomes, or an untouched period.

The current SQLite event graph preserves useful observation provenance, but it cannot reconstruct the exact dossier as of an arbitrary past timestamp because it lacks append-only registry/policy/config snapshots, complete raw-version manifests, rejected-match history, security lifecycle, market-session mapping, and outcome labels. The scorer remains `deterministic_v1`, `model_status=not_trained`.

## Candidate-source matrix

| Source | Access/history | Point-in-time strengths | Main risks and rights | Decision |
| --- | --- | --- | --- | --- |
| [SEC EDGAR APIs and bulk archives](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | No-key submissions/XBRL APIs; nightly bulk files; accession archives; real-time dissemination | Acceptance/accession time is an authoritative availability boundary; amendments are separately filed; archive paths support immutable source IDs | Company Facts aggregates can reflect later filings; freeze accession-level payloads/facts. Filing/exhibit content is not uniformly government-authored. | Required primary evidence |
| Issuer/sponsor official archives | Host-specific feeds, pages, sitemaps, JSON-LD, release indexes | Primary publication metadata when collected with first-seen time, hash, and validators | Historical pages can change/disappear; no universal completeness or redistribution rights | Reviewed primary evidence; no completeness claim |
| [GDELT raw data, GKG, and Mentions](https://www.gdeltproject.org/data.html) | Download/BigQuery; 15-minute data; GKG 2.0 from 2015; article/source/event metadata | Historical files give time-bounded discovery metadata and mention trajectories | Not an article-version archive; entity noise, coverage shifts, syndication, and publisher rights remain | Discovery-only historical feature |
| AT Protocol repository stream | [Firehose guide](https://docs.bsky.app/docs/advanced-guides/firehose) and [sync specification](https://atproto.com/specs/sync), repositories, DIDs, URIs/CIDs, commits and deletion events | Prospective collector can freeze cursor, uptime, deletion, entity decisions, and verification results | Relay receipt alone is not authentication; verify commit signatures, DID identity, and message-chain continuity. Retrospective completeness is not credible; Jetstream is unstable/self-unauthenticating and unsuitable for research archives. | Future prospective lane only |
| [CRSP US Stock](https://www.crsp.org/research/) | Subscription/WRDS or direct delivery; long daily/monthly history; active and inactive securities, corporate actions, PERMNO/PERMCO | Strongest reviewed candidate for survivor-bias control, permanent identity, delisting and corporate-action continuity | Quote required; internal research, storage, derived output, and any hosted use must be contracted. No raw redistribution. | Preferred research label/security master |
| [Databento Corporate Actions](https://databento.com/corporate-actions) | Point-in-time history from 2018-05-01; 60+ event types; listed/delisted securities; security/listing IDs; four updates daily | Records are ordered by event date and record timestamp; delisted securities continue to be tracked | Separate product with a published $299/month starting price. Documentation does not establish a delisting-return/final-consideration label. Contract must confirm retained snapshots, derived labels, model use, team access, and post-termination rights. | Conditional Stage A lifecycle component |
| [Databento Security Master](https://databento.com/security-master) | Separate product advertising 18 years of point-in-time history, 860,000+ securities, identifier/status fields | Time-varying security/listing identity can support universe membership and ticker continuity | Separate quote/symbol-based pricing; rights, inactive coverage, corrections, retention, and join behavior with Corporate Actions require confirmation | Conditional Stage A identity component |
| CRSP/Compustat Merged | Subscription; time-varying links and fundamentals | Useful if later features need point-in-time fundamentals and revisions | Larger license/cost; unnecessary for validating the current catalyst scorer | Optional, not Stage A |
| [Tiingo](https://www.tiingo.com/about/pricing) | 30+ years advertised; API; published $30/month individual and $50/month internal-commercial base tiers; redistribution separate | Potential adjusted EOD candidate after a rights and coverage review | Standard terms do not establish permission for the intended retained derivative dataset, benchmarking, or public analysis. Vendor must confirm inactive/delisted completeness, historical symbol mapping, frozen adjustments, retention, and model/report rights. Intended-use price is unknown. | Conditional Stage A price candidate only |
| [Intrinio](https://intrinio.com/pricing) | Advertises 50+ years EOD history; API/CSV/S3; security master; startup plan starts $333/month then steps to $999; enterprise $1,250+/month | Business-use tiers, historical prices, adjustments, and delisted-security handling are documented; enterprise delivery can support frozen snapshots | Exact feed bundle, inactive coverage, retention, model training/calibration, external derived output, and redistribution are contract-specific | Preferred non-CRSP commercial fallback |
| [Alpaca Market Data](https://docs.alpaca.markets/us/docs/about-market-data-api) | Equities history since 2016; free and $99/month individual tiers; bars, corporate actions; symbol mapping `asof` documented | Convenient Stage A API and raw/split/dividend/all adjustments; SIP history | Individual plan is not a hosted-product license; history is shorter; inactive/delisted completeness and frozen revisions are not established | Owner research prototype only, not Stage B backbone |
| [Massive stocks pricing](https://massive.com/pricing?product=stocks) | $0–$199/month individual plans; 2 to 20+ years; flat files, reference and corporate actions | Operationally easy bulk/flat-file history and adjusted/unadjusted aggregates | Published tiers are individual-use; business/redistribution rights require separate plan. Delisted/universe and revision guarantees need confirmation | Viable vendor evaluation, not selected |
| [Alpha Vantage](https://www.alphavantage.co/documentation/) | Adjusted daily API advertises 20+ years, splits and dividends | Simple per-symbol Stage A labels | [Default terms](https://www.alphavantage.co/terms_of_service/) are personal/non-commercial unless otherwise agreed; no demonstrated survivor-free master or frozen revisions | Do not select by default |
| Yahoo/yfinance, Stooq | Convenient free downloads | Fast exploratory checks | Upstream rights, retention, inactive coverage, revision and service guarantees are insufficient for the intended claim | Diagnostic only |
| [OpenFIGI v3](https://www.openfigi.com/api/documentation), [Wikidata](https://www.wikidata.org/wiki/Wikidata%3AData_access) | Current identifier mapping/search; Wikidata CC0 dumps | Useful cross-checks and registry proposals | Current mappings are not time-varying security-master truth; OpenFIGI API access does not itself establish downstream redistribution rights | Auxiliary discovery only |
| Licensed options data | OPRA vendor/direct history; exchange/vendor trade and quote files | Can support transaction/quote sequence and transparent derived flow features | OPRA agreements, non-display and redistribution rules; substantial volume/cost. [OPRA distinguishes subscribers and vendors](https://www.opraplan.com/). | Exclude from first backtest |

Published prices are snapshots as of the access date, not quotes. Vendor/counsel confirmation remains mandatory.

## Three viable stacks

### 1. Zero/low-cost owner-operated research

- SEC EDGAR bulk/archive evidence.
- GDELT raw metadata and existing Web NGrams discovery.
- Reviewed issuer archives.
- Alpaca free/individual or another owner-permitted EOD source for Stage A labels.
- Wikidata/OpenFIGI suggestions reviewed into a local identifier registry.
- No options and no retrospective social feature.

**What it can prove:** timestamp fidelity, replay determinism, labeling code, and a small event-study pipeline.
**What it cannot prove:** a survivor-bias-free 1,000-case universe, commercially reusable labels, or hosted-product rights.

### 2. Best-value paid internal research

- Free evidence stack above.
- Databento Corporate Actions from 2018-05-01 at the published $299/month starting price.
- Separately licensed Databento Security Master at an unknown quote/symbol-based price.
- Tiingo EOD at a published $50/month internal-commercial base, with the intended retained research/benchmark/report rights and price still unknown.
- CRSP or another verified terminal-outcome source is required for Stage B, not merely an optional validation sample.

**What it can prove:** a practical point-in-time Stage A if all three components pass written rights and coverage checks.
**Boundary:** there is no defensible published bundle total. The $299 and $50 figures omit Security Master pricing and any Tiingo addendum; this stack is not a Stage B terminal-return solution or a hosted-product license.

### 3. Commercially defensible hosted-product path

- SEC and reviewed issuer evidence collected and normalized by Catalyst Edge.
- GDELT metadata kept discovery-only.
- Intrinio enterprise (or equivalent exchange/vendor contract) for EOD/security master/corporate actions with explicit storage, derived analytics, internal model use, customer output, and termination rights.
- Separate OPRA/vendor contract only if options later become necessary.

**Boundary:** no published web page substitutes for the executed agreement. Raw licensed data remains outside responses and repository fixtures.

## Selected stack

The source decision is intentionally split by stage:

1. **SEC accession-level evidence** and issuer-primary metadata, frozen locally with retrieval manifests.
2. **GDELT raw GKG/Mentions/Web NGrams metadata** as discovery-only evidence, with versioned entity decisions and rejected matches.
3. **Conditional Stage A:** Databento Corporate Actions plus the separate Databento Security Master for lifecycle and point-in-time identity, subject to separate rights/price confirmation.
4. **Conditional Stage A:** Tiingo EOD for raw/adjusted daily labels, subject to a written addendum and coverage sample.
5. **Required Stage B:** CRSP, or a contractually equivalent enterprise source, for survivor-aware identity and terminal outcomes. Databento plus Tiingo alone is not selected for Stage B.
6. **SPY benchmark labels** from the same licensed price source. Add sector-relative labels only when the sector mapping itself is valid at `evaluation_at`.
7. **No options and no retrospective social features.** Begin a prospective verified AT Protocol corpus for a later dataset version.

If Databento and Tiingo do not pass rights and a 25-symbol coverage sample, use CRSP or an Intrinio/other enterprise contract that affirmatively covers the same security-master, inactive/delisted, retention, research, and derived-output requirements. A cheap current-ticker API is not equivalent.

## Point-in-time data contract

Use an append-only `dataset_version` and immutable `observation_id`. Minimum tables/objects:

### Security identity and lifecycle

- `security_id`, `security_id_type` (`permno` preferred), issuer CIK, ticker/name/exchange valid-from/to, share class, security type, and point-in-time classification source/version where licensed.
- IPO/listing, halt/suspension, ticker/name change, merger/acquisition, bankruptcy, delisting, terminal outcome, and corporate-action records with source and effective/announcement dates.

### Evidence version

- Event occurrence time; source publication/SEC acceptance time; `historically_available_at` backed by immutable proof; `reconstructed_at` for the actual historical collection run; retrieval time; correction/amendment/deletion time. Never backdate a 2026 reconstruction into `first_observed_at`.
- Historical issuer-primary evidence is admissible only when a contemporaneous archive proves availability before evaluation or the same content appears in an immutable SEC filing/exhibit. Otherwise it remains discovery-only.
- Source ID/tier, accession/record ID, canonical URL, hash, parser/rule version, policy decision, entity decision, rejection reason, and correction lineage.
- Content-addressed raw object reference where retention is allowed; otherwise metadata/fact manifest plus hash.
- Normalized `Evidence` exactly as replayed, including all supporting source IDs, missing families, family statuses, and warnings.

### Evaluation snapshot

- `evaluation_at`, market calendar/version, premarket/regular/after-hours relationship, eligibility cutoff, scorer version, code commit, config/registry/policy hashes.
- MCP score, direction, confidence, contribution breakdown, and the full ordered set of scoped reason records.
- If the downstream product classification is evaluated, store `classification`, `classification_owner`, `classification_policy_version`, its frozen class definitions, and the exact reason/score-to-class mapping. RESEARCH NOW/MONITOR/IGNORE is not inferred as an MCP-owned field.

### Outcome labels

- Raw and adjusted entry price; entry convention; 1/5/20-session underlying raw-price and total returns; SPY-relative returns; sector-relative returns only with a valid point-in-time sector mapping.
- Freeze `signal_sign` as `+1`, `0`, or `-1`. Underlying return is always `exit / entry - 1`; signal-signed gross return is `signal_sign * underlying_total_return`; neutral observations retain underlying labels but have zero hypothetical trade P&L.
- Reconcile splits explicitly in the raw-price path. The total-return label includes cash and stock distributions using the licensed vendor's frozen adjustment methodology, cross-checked against explicit corporate actions.
- For each horizon, maximum favorable/adverse excursion is the maximum/minimum signal-signed excursion from entry across split-adjusted daily high/low observations through that horizon. Cash distributions affect terminal total return, not the intraday high/low path.
- Net return is signal-signed gross return minus a frozen scenario cost model. End-of-day data does not measure spread, slippage, or borrow; those are versioned assumptions reported separately, with borrow applied only to negative-signal hypothetical trades.
- Halt/missing/delisting/merger/terminal outcome and all formula, rounding, adjustment, calendar, and cost-model versions.

Store raw manifests and normalized Parquet partitioned by dataset/source/date, query with DuckDB, and keep a small SQLite catalog for manifests/runs. Hash every manifest and freeze an environment lock, Git commit, scorer config, calendar, and SQL/query version. Never overwrite a prior dataset version.

## Replay and label conventions

- A fact is eligible only when `max(accepted_or_published_at, historically_available_at) <= evaluation_at`, with the historical-availability proof retained. `reconstructed_at` records when the backfill actually occurred and never substitutes for proof of past availability.
- Amendments/corrections are new versions; a later version cannot alter an earlier replay.
- With daily bars, enter at the first regular-session open at least 15 minutes after the eligibility time. Evidence after that cutoff enters at the next session open. The exact delay is frozen before outcomes are viewed.
- Label sessions with an exchange calendar, including holidays and half-days. Horizons count eligible sessions, not calendar days.
- Use unadjusted prices plus explicit corporate actions for audit, and vendor-adjusted total-return prices as a cross-check.
- Delisting returns or terminal consideration must be applied. Missing terminal outcomes are a data failure, not a dropped row.
- MFE/MAE use daily high/low for the first study; do not imply intraday execution precision.

## Corpus construction: 1,000+ observations

Pre-register the sampling query before joining returns.

- **Period:** 2018-05-01 through 2025-12-31, preserving 2024–2025 as the untouched test period. An earlier start requires a different verified lifecycle source.
- **Universe:** all eligible U.S. common equities in the licensed point-in-time security master that meet a predeclared minimum price/liquidity rule at the evaluation date; include inactive and later-delisted securities.
- **Events:** approximately 700 observations sampled from all eligible SEC/issuer catalyst events using a pre-registered probability rule. Event-family/year diagnostics may be stratified, but reported performance must use population weights; do not impose direction quotas or select on subsequent returns.
- **Controls:** approximately 300 ticker/session observations sampled from the same historical universe, matched on date, prior price/dollar volume, and prior 20-day volatility/momentum, with no eligible catalyst in the lookback. Add sector or size only when its source is point-in-time; otherwise omit it. SEC-filed SIC is an acceptable coarse contemporaneous classification.
- **Terminal audit set:** deliberately include inactive, acquired, bankrupt, delisted, and ticker-recycled cases in a separate audit set. Do not mix future-conditioned audit selection into the performance sample.
- **Regimes:** include the 2018 tightening/volatility period, 2020 shock/recovery, 2021 risk-on, 2022 inflation/rate selloff, 2023–2024 AI/megacap concentration, and 2025 post-election/rate regime without labeling regimes from future returns.
- **Splits:** train 2018–2021, validation 2022–2023, untouched test 2024–2025; also report rolling annual walk-forward folds.

The unchanged `deterministic_v1` and every candidate calibrated scorer must be frozen before one shared untouched-test unseal. Any learned calibration or weight change becomes a new scorer version trained only on train and selected only on validation. A model proposed after that unseal requires a new future holdout; it cannot reuse 2024–2025 as untouched evidence.

## Evaluation methods

- Baselines: neutral/no signal, SPY and sector momentum, prior 20-day ticker momentum, and simple SEC event-category rules.
- Classification: coverage and directional hit rate. Evaluate RESEARCH NOW/MONITOR/IGNORE precision/recall/confusion only when the downstream owner, policy version, class definitions, and reason/score mapping were frozen before the untouched-test unseal.
- Ranking/calibration: Spearman information coefficient, return by score/confidence band, reliability curves, Brier/log loss for predefined directional targets.
- Economics: raw/relative/net returns, turnover, MFE/MAE, drawdown, win/loss tails, and event-cluster exposure.
- Uncertainty: ticker-clustered and date-block bootstrap confidence intervals; report sample counts and effective independent clusters.
- Multiple testing: pre-register primary horizon/metric, use validation for thresholds, report all attempted variants, and apply a false-discovery or family-wise correction to secondary searches.

## Two-stage proof of concept

### Stage A — 50–100 observations

Deliver one immutable dataset version with at least 20 event types, 10 controls, multiple after-hours cases, and corrections/amendments. Maintain a separate terminal audit set with ticker changes, one acquisition, one bankruptcy/delisting, at least five inactive securities, and a ticker-recycling case. Manually audit every timestamp, identity path, replayed dossier, entry session, and label; do not report the deliberately selected audit set as performance evidence.

Pass only if:

- At every replay cutoff, 100% of evidence is invisible before its proven `historically_available_at` and visible on/after it; this tests historical public availability and replay eligibility, not the later backfill collector's possession time.
- 100% of sampled security/ticker intervals and entry sessions match the source records.
- 100% of correction/amendment cases replay the older version before the change.
- All terminal outcomes are represented; no row is silently dropped for missing price.
- Re-running from frozen manifests produces byte-identical normalized observations and labels.

### Stage B — 1,000+ observations

Freeze the pre-registered query, build all folds, publish a signed manifest and untouched-test report, and retain complete exclusion counts/reasons.

Minimum acceptance for the label “backtested”:

- At least 1,000 valid observations and at least 250 untouched-test observations.
- Zero known critical timestamp, identity, terminal-outcome, look-ahead, or survivor-selection errors. A sub-1% threshold applies only to predeclared noncritical metadata fields.
- At least 95% evidence/source coverage for the families claimed; missingness reasons reported by fold.
- Baselines, costs, clustered uncertainty, and all primary metrics reported whether positive or negative.
- Frozen dataset/scorer/config/code hashes and a one-command replay from permitted retained data.

“Backtested” does not mean “predictive.” Claim predictive usefulness only if the pre-registered untouched test shows monotonic score-band behavior and a positive benchmark-relative primary result after costs with its 95% confidence interval above zero, without a material sector/megacap concentration explanation. Otherwise report: **backtested; no demonstrated predictive edge**.

Weight/threshold calibration is justified only if validation shows stable monotonicity/calibration improvement across at least two walk-forward folds and the new version beats unchanged `deterministic_v1` on the predeclared validation objective. All retained candidates are frozen before the single shared untouched-test unseal; later candidates require a new future holdout.

## Cost and effort

| Item | Expected cost/effort |
| --- | --- |
| SEC/GDELT/issuer evidence | Data free; 2–4 engineer-weeks for historical manifests, entity gates, replay, and audits |
| Stage A price data | Published prototypes range from $0–$99/month, but the intended retained research/benchmark/report rights and price are unknown until confirmed |
| Databento corporate actions | Published starting price $299/month; exact rights/coverage subject to contract |
| Databento Security Master | Separate quote/symbol-based price; not included in the Corporate Actions starting price |
| Tiingo EOD internal-commercial | Published base $50/month or $499/year; intended-use addendum and total price unknown |
| CRSP | Vendor/institution quote; preferred reviewed Stage B terminal-outcome/security source |
| Intrinio fallback | Published startup $333/month for six months, $666/month for six months, then $999/month; enterprise starts $1,250/month, exact feeds/rights extra or custom |
| Stage B implementation/audit | 4–8 engineer-weeks after access, plus manual audit and legal/vendor review |
| Options | $0 in first backtest; later vendor plus OPRA/non-display/redistribution costs |

## Five highest-risk assumptions

1. Databento Corporate Actions, the separate Security Master, and Tiingo jointly cover enough inactive/delisted securities for Stage A; none is presumed to provide a Stage B terminal-return field.
2. Both agreements permit long-term retention, normalized labels, calibration/model research, and the intended report/derived outputs.
3. GDELT/issuer archives provide enough historical discovery coverage without regime-dependent selection distortion.
4. The event/control sampling rule can be executed solely from information available at each historical timestamp.
5. One thousand observations provide enough independent event clusters for narrow confidence intervals; ticker/date clustering may reduce effective sample size substantially.

## Exact next actions

1. Prepare a written data-rights questionnaire for Databento Corporate Actions, Databento Security Master, Tiingo, and a Stage B terminal source led by CRSP, covering fields, separate pricing, inactive/delisted history, final consideration/delisting returns, corrections, retention, derived labels, model calibration, internal reports, hosted outputs, and termination. Do not send it without owner approval.
2. Prepare a 25-symbol sample request spanning active, renamed, merged, acquired, bankrupt, delisted, ticker-recycled, ETF, ADR, split, and special-distribution cases. Do not send the questionnaire or sample request without owner approval.
3. Do not purchase until the owner approves one returned quote/rights package.
4. Draft the provider-neutral technical specification addendum now for immutable manifests, historical-availability proof, registry/policy/scorer hashes, replay cutoff logic, security lifecycle, labels, and audit fixtures. Defer vendor-specific mappings until rights/fields are confirmed.
5. Implement Stage A only after the chosen data can legally be retained and replayed.
6. Freeze the Stage B sampling plan before joining any forward returns.

## Go/no-go

**Go** on preparing the vendor-rights package and provider-neutral Stage A technical specification. **Conditional go** on Stage A after identity/lifecycle/price access is approved. **No-go** on Stage B, calibration, or any predictive claim until a survivor-aware terminal-outcome source is contracted and the Stage A timestamp audit passes.
