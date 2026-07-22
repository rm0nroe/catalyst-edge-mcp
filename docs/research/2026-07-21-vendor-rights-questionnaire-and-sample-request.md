# Vendor rights questionnaire and sample request

**Prepared:** 2026-07-21
**Status:** Draft only. Do not send, accept terms, approve a quote, create a paid
account, or purchase data without explicit owner approval.
**Candidate components:** Databento Corporate Actions, Databento Security Master,
Tiingo EOD, and CRSP or a contractually equivalent terminal-outcome source.

## Intended use

Catalyst Edge is evaluating a provider-neutral, owner-operated research dataset
for point-in-time replay and backtesting. Stage A contains 50–100 manually audited
cases beginning no earlier than 2018-05-01. A later Stage B may contain 1,000+
cases. The system needs historically correct identity, lifecycle, raw/adjusted
prices, corporate actions, corrections, inactive/delisted outcomes, and retained
availability timestamps. No brokerage execution or raw-data redistribution is
planned.

Please answer each question in writing and identify the exact product, edition,
account type, agreement, schedule, and fee that controls the answer. A link to
general documentation is helpful but does not replace a product-specific answer.

## Part 1 — Product scope, coverage, and total price

1. Which separately licensed products are required for:
   - point-in-time security/listing identity and historical symbols;
   - corporate actions and lifecycle events;
   - unadjusted and adjusted daily OHLCV;
   - inactive/delisted securities; and
   - final consideration, delisting returns, or another complete terminal outcome?
2. State the earliest complete date, venues/security types, active/inactive
   coverage, identifier types, delivery methods, update cadence, corrections
   history, minimum term, setup fees, recurring fees, usage-based fees, and any
   required third-party exchange fees for each product.
3. Confirm whether U.S. common equities, ADRs, ETFs, unit investment trusts,
   commodity trusts, multiple share classes, renamed securities, mergers,
   bankruptcies, delistings, and recycled tickers are represented without silent
   survivor filtering.
4. Provide the total Stage A price and the total Stage B price for one owner plus
   the minimum internal team access needed to build and review the dataset. Do not
   activate an account or start a paid trial in response to this request.

## Part 2 — Point-in-time fields, corrections, and terminal semantics

For every applicable product, provide a data dictionary and one representative
record showing:

1. stable security, listing, issuer, and share-class identifiers;
2. symbol/name/exchange/security-type validity intervals and status history;
3. announcement, record, effective, provider-observation, publication, and
   correction timestamps, including their time zones and precision;
4. original/corrected/cancelled record IDs and whether prior versions remain
   queryable after a correction;
5. split, dividend, spin-off, merger, acquisition, bankruptcy, halt, symbol
   change, delisting, and final-consideration fields;
6. raw and adjusted prices, exact adjustment factors, dividend treatment, and
   whether historical adjusted values can be revised later; and
7. the exact terminal-return or final-consideration semantics, including cash,
   stock, mixed consideration, worthless outcomes, missing outcomes, and the
   handling of the final tradable session.

Please identify any field that reflects current knowledge rather than what was
known at the record timestamp. State whether a query can reproduce the exact
record version visible at an arbitrary historical cutoff.

## Part 3 — Retention, research, model, and derived-output rights

Please quote the governing contract language or provide an addendum confirming
whether the customer may:

1. retain raw deliveries, normalized records, content hashes, fact manifests,
   derived labels, and audit logs during the subscription and after termination;
2. rebuild and replay historical datasets internally after termination;
3. permit employees and contractors on the named internal team to access the
   data and derived dataset;
4. use the data for backtesting, scorer calibration, statistical analysis, and
   model training/evaluation, including negative-result reporting;
5. publish aggregate benchmark results, confidence intervals, coverage/error
   rates, methodology, and non-reconstructable examples;
6. expose source-linked derived scores, classifications, citations, and factual
   provenance through a hosted product without exposing raw vendor records; and
7. retain small sanitized or synthetic fixtures for automated regression tests.

List any non-display, derived-data, redistribution, attribution, audit,
deletion-on-termination, or per-user fees. If a right is unavailable, state the
closest permitted alternative and its price. Silence is treated as no permission.

## Part 4 — Coverage sample and acceptance evidence

Please return machine-readable samples from the exact quoted products for the
25-case matrix below. Include every identity, lifecycle, action, price, correction,
and terminal field applicable to each case; include empty fields explicitly.
For historical/current symbol pairs, return both identities and their non-overlap
or continuity relationship. Redacted values are acceptable only when the field
semantics, timestamp behavior, and identifier joins remain testable.

| # | Requested symbol/security case | Primary audit purpose |
| ---: | --- | --- |
| 1 | AAPL | Active common equity; 2020 split; adjusted/raw reconciliation |
| 2 | NVDA | Active common equity; 2021/2024 splits; correction stability |
| 3 | TSLA | Active common equity; splits and high-volume corporate actions |
| 4 | RKLB | Active post-combination equity; listing/issuer continuity |
| 5 | BRK-A / BRK-B | Multiple share classes and symbol normalization |
| 6 | FB / META | Rename plus historical META ticker collision/reassignment audit |
| 7 | CDAY / DAY | Corporate and ticker rename continuity |
| 8 | ATVI | Acquired security and final consideration |
| 9 | TWTR | Acquired/private outcome and final tradable session |
| 10 | VMW | Acquired security and mixed lifecycle history |
| 11 | IRBT / IRBTQ | Bankruptcy, symbol/status change, and terminal outcome |
| 12 | BBBY / BBBYQ | Bankruptcy, delisting, and worthless/terminal semantics |
| 13 | SIVB / SIVBQ | Bank failure, halt/delisting, and terminal semantics |
| 14 | S (Sprint and SentinelOne) | Explicit recycled-ticker identity separation |
| 15 | SPY | ETF/unit-investment-trust identity and action treatment |
| 16 | QQQ | ETF series/class identity and price/action history |
| 17 | GLD | Commodity-trust identity and non-corporate semantics |
| 18 | GDX | ETF series/class identity and sponsor/security joins |
| 19 | BABA | ADR identity, venue, ratio/action, and inactive-risk handling |
| 20 | TSM | ADR identity and issuer/listing separation |
| 21 | COST | Special cash distribution and adjusted/raw reconciliation |
| 22 | GE | Reverse split plus spin-off/action chronology |
| 23 | DWAC / DJT | Merger/ticker transition and issuer continuity |
| 24 | DISCA / WBD | Merger/reorganization and terminal consideration |
| 25 | XLK | ETF series/class identity and sector-fund treatment |

For each case, also provide:

- a point-in-time identity snapshot before and after each material transition;
- the provider record/version IDs and timestamps needed to order corrections;
- unadjusted and adjusted daily values around the event;
- the exact corporate-action factors used by the adjusted series; and
- a documented reason for any absent, unsupported, or non-applicable field.

## Internal acceptance and authorization gate

The sample passes only if the repo can map it losslessly into the canonical TDD
contract, reproduce identity intervals and adjustment arithmetic, represent every
terminal case without silent row removal, and retain the required rights in
writing. Vendor-specific adapter work does not begin before those checks.

Owner approval is separately required to:

1. send this questionnaire or identify the customer/account;
2. accept a trial, NDA, click-through, addendum, quote, or order form;
3. incur any fee or enable a spend-capable account; and
4. select a Stage A or Stage B vendor package.
