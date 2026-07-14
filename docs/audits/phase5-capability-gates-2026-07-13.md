# Phase 5 capability gate audit — 2026-07-13

## Decision

No sentiment model, lexicon, or vendor aggregate is production-enabled. No
options-flow provider is composed. The audited candidates fail closed until
every required gate is recorded as passed in
`catalyst_edge_mcp/capability_gates.py`.

This is an engineering and source-policy review, not legal advice. A deployment
owner must bind any future approval to the exact artifact revision, input-data
source, provider account, plan, and written terms.

## Sentiment gates

Every candidate must pass all of these gates:

1. commercial-use rights;
2. explicit model or lexicon rights;
3. rights to use the input text for automated inference;
4. Python 3.10+ compatibility on the pinned runtime;
5. deterministic, revisioned preprocessing;
6. a labeled Catalyst benchmark meeting fixed acceptance thresholds;
7. rounded output with fixed precision; and
8. fixed bullish, neutral, and bearish thresholds.

| Candidate | Rights | Python 3.10+ | Preprocessing | Labeled quality | Output contract | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Finnhub social sentiment | Fails current commercial/input-data rights; vendor model rights undocumented | Adapter compatible | Vendor pipeline opaque | Not run | Delta threshold exists; approved rounding absent | Disabled |
| TextBlob 0.20 | MIT code; vendored asset and input-data review incomplete | Declared 3.10+ | Not fixed | Not run | Not fixed | Disabled |
| VADER 3.3 | MIT engine/lexicon; input-data rights absent | Explicit 3.10+ matrix absent | Not fixed for Catalyst | Upstream social data is not a Catalyst acceptance run | Upstream ±0.05 exists; Catalyst rounding absent | Disabled |
| DistilBERT SST-2 | Apache-2.0 model card; input-data rights absent | Pinned runtime not tested | Not pinned | Generic SST-2 domain fails the required finance/social benchmark gate | Not fixed | Disabled |
| ProsusAI FinBERT | Apache-2.0 code repo; hosted weight card lacks an explicit license tag; input-data rights absent | Pinned runtime not tested | Not pinned | Financial PhraseBank training is not a Catalyst social-text acceptance run | Not fixed | Disabled |

Official review evidence:

- [TextBlob license](https://github.com/sloria/TextBlob/blob/dev/LICENSE) and
  [Python metadata](https://github.com/sloria/TextBlob/blob/dev/pyproject.toml)
- [VADER repository](https://github.com/cjhutto/vaderSentiment) and
  [MIT license](https://github.com/cjhutto/vaderSentiment/blob/master/LICENSE.txt)
- [DistilBERT SST-2 model card](https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english)
- [ProsusAI FinBERT code license](https://github.com/ProsusAI/finBERT/blob/master/LICENSE)
  and [hosted model card](https://huggingface.co/ProsusAI/finbert)
- [Finnhub signup rights statement](https://finnhub.io/register) and
  [pricing/license matrix](https://api.finnhub.io/pricing)

### Required benchmark before enablement

The acceptance corpus must contain at least 600 source-authorized, exact-ticker
English observations with at least 150 adjudicated examples in each of bullish,
bearish, and neutral. Two annotators label each item; disagreements are
adjudicated. Validation and test partitions must be later in time and
issuer-disjoint from training. The test set must include at least 40 examples
each for negation, sarcasm, cashtags, emoji, finance terminology, and link-heavy
text.

Before a candidate can pass, its pinned revision must achieve macro F1 ≥ 0.70,
bullish and bearish precision ≥ 0.70, neutral recall ≥ 0.60, and no robustness
slice below macro F1 0.60. The run must record the confusion matrix, per-class
metrics, exact preprocessing revision, deterministic seed/runtime, and 95%
bootstrap confidence intervals. No candidate has run this benchmark, so there
are no passing quality results.

The eventual output contract must map the pinned candidate to a finite signed
score in `[-1, 1]`, round to four decimals before persistence or thresholding,
and record immutable thresholds in the audit. Upstream defaults do not become
Catalyst thresholds without the labeled acceptance run.

## Options entitlement gates

True `options_flow` requires transaction records plus contemporaneous quotes,
non-display automation rights, retention/storage rights, derived-output rights,
a documented API, and an approval bound to the deployed account and plan.

| Candidate | Data semantics | Automation | Storage/output | API/account binding | Decision |
| --- | --- | --- | --- | --- | --- |
| FlowAlgo | Order-flow records; no approved trade-time quote contract | Public terms prohibit automated extraction | Public terms prohibit redistribution/commercial reuse; storage right absent | No approved API or enterprise agreement recorded | Not composed |
| CheddarFlow | Product describes trades and bid/ask context | Public terms treat scraping as a breach | Personal-research export does not grant service storage; redistribution is prohibited | No approved API or enterprise agreement recorded | Not composed |
| Future OPRA vendor | Unselected | Missing | Missing | Missing | Not composed |
| yfinance | Chain snapshot is not transaction flow | Not commercially cleared | No production storage/output rights | Private diagnostic only | Not composed |

Official review evidence:

- [FlowAlgo terms](https://help.flowalgo.com/en/articles/3365195-terms-of-service-and-refund-policy)
- [CheddarFlow terms/refund policy](https://www.cheddarflow.com/refund-policy/)
  and [product data description](https://www.cheddarflow.com/features/unusual-options-flow-scanner/)

The production composition root now makes no options request. Adapter code is
retained only for isolated parser fixtures and explicit private diagnostics.
Typed `licensed_feed_required` missingness remains the production behavior.

## Live entitlement recheck — 2026-07-14

Secret-free probes of the configured accounts confirmed that the FMP technical
indicator endpoint returns HTTP 402 and Finnhub social sentiment returns HTTP
403. No usable FlowAlgo or CheddarFlow credential is configured. These results
confirm endpoint and account-plan unavailability; they do not create commercial,
storage, inference, or derived-output rights. Options flow, licensed OHLC
technicals, and sentiment therefore remain correctly uncomposed until the
deployment owner supplies a qualifying contract and account binding.

## Verification

- `UT_SENTIMENT_CANDIDATES_ARE_DISABLED_FAIL_CLOSED`
- `UT_SENTIMENT_GATE_REJECTS_EACH_MANDATORY_FAILURE`
- `UT_SENTIMENT_GATE_REJECTS_INCOMPLETE_AUDIT_SCHEMA`
- `UT_OPTIONS_ENTITLEMENTS_REMAIN_UNCOMPOSED`
- `test_build_service_never_composes_unentitled_options_provider`
- `FX_SENTIMENT_MODEL_DISABLED_GETS_NO_SCORE_COVERAGE_OR_READINESS`
