# Real Catalyst Product Evaluation — 2026-07-15

## Scope

This evaluation uses 25 real SEC filings across eight issuers. Twenty-two cases
cover the reviewed AAPL, NVDA, TSLA, RKLB, and BRK-B cohort. Three additional
cases exercise real non-reliance, bankruptcy, and merger-related delisting
semantics from FDCTech, iRobot, and Dayforce.

The source facts are recorded in
`tests/fixtures/validation/real_catalyst_cases.json`. Each accession and primary
document returned HTTP 200 from the official SEC archive on 2026-07-15. The
fixture retains accession metadata, item codes, expected semantics, and five
short classification phrases; it does not retain filing or publisher bodies.
Those phrases verify the recorded cases but do not establish broad wording or
layout coverage. Separate representative primary-document fixtures cover HTML
structure, tables, inline XBRL, amendments, negation, proposed events, multiple
specific events, and near matches.

## Evaluation criteria

- Primary-link validity and immutable accession provenance.
- Event classification against the primary filing.
- Fail-closed direction semantics.
- Accepted-timestamp freshness and observation semantics.
- Split behavior for four nearby but distinct filing pairs.
- Human-reviewed research value (`high` or `medium`).
- Final dossier direction through the deterministic scorer.

## First-pass results

| Criterion | Result |
| --- | ---: |
| Primary links valid | 25/25 |
| Specific event classification | 18/25 |
| Direction correct | 24/25 |
| Provenance and accepted timestamps correct | 25/25 |
| Nearby distinct pairs kept separate | 4/4 |
| Research value high | 18/25 |
| Research value medium | 7/25 |

The first pass exposed three defects:

1. Multi-item context used lexical item order, so iRobot's Item 1.03 bankruptcy
   event was labeled as an Item 1.02 agreement termination.
2. Item 3.01 was always bearish, including Dayforce's expected listing
   termination after a completed change-of-control transaction.
3. Five Item 8.01 cases remained generic even though their primary documents
   identified debt offerings, an equity distribution agreement, a prospectus
   supplement, or active share repurchases.

## Corrections

- Added explicit materiality priority for multi-item 8-K context.
- Treat Item 3.01 as non-adverse when Items 2.01 and 5.01 establish a completed
  change of control; the event is classified as an acquisition or disposition.
- For otherwise generic Item 8.01 events only, fetch the official primary
  document under the existing SEC rate gate, enforce an exact archive URL and a
  2 MB response ceiling, derive a bounded classification, hash the response,
  and discard the body.
- Added versioned deterministic rules for completed debt offerings, entered or
  amended equity distribution agreements, filed prospectus supplements, and
  actual share-repurchase activity.
- Record the ruleset, rule identity, and rule version. Proposed, negated,
  unsupported, or multiple-specific-event documents fail closed to the generic
  Item 8.01 classification.

## Post-correction results

| Criterion | Result |
| --- | ---: |
| Primary links valid | 25/25 |
| Specific event classification | 25/25 |
| Direction correct | 25/25 |
| Provenance and accepted timestamps correct | 25/25 |
| Nearby distinct pairs kept separate | 4/4 |
| Dossier direction correct | 25/25 |
| Cases rated useful for research | 25/25 |

The executable evaluation is `tests/test_real_catalyst_evaluation.py`. It uses
recorded real facts offline and does not replace live source checks when SEC
data changes.

The post-correction table is an acceptance result for this recorded corpus, not
a general SEC semantic-enrichment benchmark.

## Scorer decision

No numerical weight or confidence threshold changed. The corpus contains 23
correctly neutral cases and two correctly bearish cases, but no forward-return
labels and no licensed options or technical evidence. Changing score weights
from this sample would imply outcome calibration the data does not support.
The recorded result instead justified semantic fixes upstream of scoring. The
scorer remains explicitly deterministic and unbacktested.
