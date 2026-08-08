# Model-training data source decision

**Reviewed:** 2026-08-06
**Refreshed:** 2026-08-08
**Status:** Synthetic engineering training is authorized and unblocked. Production
promotion remains awaiting written vendor rights, quotes, and the 25-security
sample. No account, trial, subscription, credential, or data download was created.

## Decision

Use **CRSP US Stock** as the preferred single-source candidate for the Stage B
price, point-in-time identity/lifecycle, and terminal-outcome contract. Its
published documentation explicitly covers permanent security identity, active
and inactive securities, and delisting returns. Selection remains conditional on
the commercial quote, written model-artifact/output rights, and the required
sample passing the repository contract.

Do not buy Tiingo by itself. Its $50/month internal-commercial plan is a viable
price-label component, but its current terms require written approval for derived
data retention and do not establish complete survivor-aware identity or terminal
outcomes.

Do not treat Databento Corporate Actions plus Security Master as a Stage B
terminal source. The published products provide point-in-time identifiers,
listing status, listed/delisted coverage, corrections, and corporate actions, but
do not document a complete delisting-return or final-consideration field. This
stack remains a conditional fallback only when paired with an approved terminal
source.

Reject Norgate Data for this product. Its current license is personal-use only,
prohibits commercial use, and requires deletion of Data and Derived Data after a
subscription lapses.

## Published evidence

| Candidate | Published evidence | Current disposition |
| --- | --- | --- |
| CRSP US Stock | [Subscription request](https://www.crsp.org/subscription-information/); [data guide](https://www.crsp.org/crsp_pdf/crsp-us-stock-indexes-databases-data-descriptions-guide-crspaccess/) documents delisting-return semantics | Preferred; quote and written rights required |
| Databento | [Corporate Actions](https://databento.com/docs/venues-and-datasets/corporate-actions) covers point-in-time records from 2018-05-01 and listed/delisted securities; [Security Master](https://databento.com/security-master) is separately priced | Conditional identity/lifecycle component; terminal proof absent |
| Tiingo | [Pricing](https://www.tiingo.com/about/pricing) lists $50/month internal commercial; [Terms 1.6](https://app.tiingo.com/tos/) requires written derived-data approval and raw-data deletion at termination | Conditional price component; do not subscribe yet |
| Norgate | [FAQ](https://norgatedata.com/faq.php) limits licensing to personal use; [EULA](https://norgatedata.com/subscribe/eula.php) deletes Data and Derived Data at lapse | Rejected |

## Free and low-cost refresh

The 2026-08-08 review did not identify a free source that satisfies the complete
commercial training contract. SEC EDGAR remains usable for timestamped catalyst
and lifecycle evidence, but Forms 25, 15, and 8-K do not supply a complete
survivor-aware security master, adjusted daily prices, or terminal returns. A
Form 25 records removal from a national exchange; the security may continue OTC.

Academic WRDS access is not a commercial workaround: the [WRDS Terms of
Use](https://wrds-www.wharton.upenn.edu/users/tou/) restrict academic access to
academic and non-commercial research. Cloud or marketplace credits would offset
cost only when the grant also supplies explicit company-level data and derived
model-artifact rights.

Tiingo remains the only reviewed candidate with a published sub-$100/month
internal-commercial base price. It is not a complete single-source solution:
Tiingo's [symbology documentation](https://www.tiingo.com/documentation/appendix/symbology)
limits delisted coverage to tickers that have not been recycled, and no complete
terminal-return contract has been established. Massive/Polygon has technically
useful point-in-time reference data, but its $0-$199 plans are individual-use;
the current [Stocks Business plan](https://massive.com/business) is $1,999/month.

The free-only decision therefore remains fail-closed for real-market training and
promotion: continue provider-neutral plumbing and SEC evidence work, but do not
train or promote `trained_softmax` from an unapproved free or retail-use dataset.

## Synthetic engineering decision — 2026-08-08

Proceed now with synthetic training as an engineering-unblock path. Synthetic
rows may exercise the complete provider-neutral replay, feature extraction,
training, evaluation, artifact, loading, and shadow-inference flow without
waiting for a vendor response or creating a paid account.

Synthetic results measure performance against the synthetic generator only.
They do not establish real-market accuracy because both the evidence-to-outcome
relationship and the future-return labels are invented. A synthetic model must
therefore remain development-only, carry an explicit synthetic provenance marker,
report no market-performance claim, and fail closed with `stage_b_passed=false`.
The public scorer remains `deterministic_v1` with `model_status=not_trained`.

This decision separates the work into two independent gates:

1. **Engineering gate — unblocked now.** Finish a production-shaped synthetic
   corpus; run it through the same importer, coverage audit, canonical replay
   build, training, evaluation, artifact hashing/loading, and shadow-inference
   interfaces intended for licensed data; retain the resulting artifact only as
   a reproducible development fixture.
2. **Market-validation gate — still blocked.** Use a rights-cleared point-in-time
   corpus with real forward returns, lifecycle events, terminal outcomes, and an
   untouched test period before reporting market accuracy or promoting
   `trained_softmax`.

### Engineering path forward

1. Add a deterministic synthetic-corpus generator that covers 2018–2025,
   bearish/neutral/bullish labels, corrections, corporate actions, ticker reuse,
   delisting/bankruptcy outcomes, exclusions, and deliberately missing records.
2. Feed synthetic records through the existing provider adapter/importer contract;
   do not add a separate training-only schema or bypass.
3. Run the coverage audit and canonical replay build, preserving provenance,
   content hashes, chronological group isolation, purge/embargo, and the untouched
   test boundary.
4. Train and evaluate `trained_softmax`, compare it with majority-class,
   training-prior, and `deterministic_v1` baselines, and label every metric
   `synthetic_only`.
5. Load the content-hashed artifact through the normal fail-closed loader and run
   shadow inference without changing the public scorer or release response.
6. Turn the end-to-end run into a reproducible local command and regression test
   so a future licensed dataset can replace the synthetic adapter without changing
   downstream model code.
7. Stop at the real-data boundary: do not open a market-accuracy claim, set
   `stage_b_passed=true`, bundle the artifact publicly, or promote the scorer until
   the market-validation gate passes.

The reproducible engineering command is
`uv run catalyst-edge-synthetic-model --root <output-directory>`. It writes only
content-addressed `synthetic_only` corpus, audit, artifact, evaluation, runtime-manifest,
and shadow-inference records beneath the supplied directory.

## Inquiries sent

On 2026-08-06, Gmail confirmed delivery from `rmonroe128@gmail.com` to:

- `crsp-subscriptions@morningstar.com` — CRSP US Stock quote, rights, and
  25-security validation request;
- `support@databento.com` — combined Corporate Actions, Security Master, EOD,
  terminal-field, rights, quote, and sample request; and
- `sales@tiingo.com` — $50 commercial-plan confirmation, Terms 1.6 derived-model
  approval, coverage limits, price, and sample request.

Each inquiry states that no raw redistribution or brokerage execution is planned
and asks for product-specific written permission covering training, retained
non-reconstructable model parameters, commercial software distribution of those
parameters, aggregate reporting, post-termination artifact retention, deletion
obligations, and total fees.

Tiingo returned an automated receipt with a stated 1–2 business-day sales window.
Databento's Eric confirmed that its price data is unadjusted, pointed to the
Corporate Actions and Security Master landing-page prices, and asked whether a
derived output will be sold or distributed. On 2026-08-07, Ryan replied that
non-reconstructable model parameters will be commercially distributed while no
raw or reconstructable Databento prices or records will be exposed, and repeated
the adjustment-factor, terminal-outcome, rights, total-price, and sample requests.

CRSP/Morningstar's Matthew Harrison supplied product links and required the
licensing and pricing discussion to continue from a business-domain address. On
2026-08-07, Ryan followed up from `ryan@ryanmonroe.ai`, copied the subscriptions
address, and repeated the exact product, artifact/output-rights, total-price, and
25-security sample requirements. No quote, rights answer, or sample has been
received. Tiingo still has only the automated receipt. A Gmail search found no
older Tiingo account messages, the Tiingo site was not logged in, and no local
Tiingo credential exists; the previously suspected reusable account is therefore
not verified.

### Contact matrix as of 2026-08-08

| Organization | Contacted? | Current mailbox evidence |
| --- | --- | --- |
| CRSP/Morningstar | Yes | Matthew Harrison replied and requested intended use, external-result display, investment-process use, seats, AI/ML tools, CUSIP license, corporate location/incorporation date, and AUM before pricing; no quote, rights answer, or sample yet |
| Databento | Yes | Eric answered partially; Ryan clarified that only non-reconstructable model parameters would be distributed and repeated the unresolved rights, terminal, adjustment, total-price, and sample questions |
| Tiingo | Yes | Automated receipt only; no substantive sales, rights, coverage, quote, or sample response recorded |
| WRDS | No separate inquiry | Academic access was researched and rejected as a commercial shortcut under its published terms |
| SEC | Not a vendor inquiry | Public EDGAR APIs and filings were researched as evidence inputs, not contacted for a commercial dataset |
| Massive/Polygon | No | Published individual and business plans were researched; no sales inquiry was sent |

## Acceptance gate

The source decision completes only when one returned package:

1. covers point-in-time active/inactive identity, corrections, raw/adjusted daily
   prices, corporate actions, and complete terminal outcomes;
2. permits internal training and retention/distribution of the bundled,
   non-reconstructable model artifact after raw licensed data is removed;
3. states all recurring, setup, user, derived-data, and output fees; and
4. passes the existing 25-security validation matrix without silent row loss.

Until then, `deterministic_v1` remains the production scorer. Real-market model
training, artifact promotion, market-accuracy claims, and any Tiingo purchase
remain blocked; synthetic engineering training is explicitly allowed under the
decision above. Public v0.1.5 was released separately without a trained-model
claim or artifact.
