# Five-Ticker Release-Sample Runbook

**Status:** Current internal QA procedure for the self-serve Local Beta. The legacy
filename and `scripts/run_design_partner_demo.py` entry path are retained for release
continuity; no design partner, customer interview, demo call, or customer acceptance is
part of this procedure.

## Purpose

Prove the implemented contract with five repeated single-ticker calls, one dossier
review, complete available provenance pagination, and one explicit missing or rejected
data case. Produce only a sanitized example that is safe for release review.

This proves product behavior, not alpha, returns, market-wide coverage, investment advice,
or willingness to pay.

## Preconditions

- Use the exact release candidate and public-default configuration being evaluated.
- Use fixed public tickers: `AAPL NVDA TSLA RKLB BRK.B`.
- Do not use holdings, positions, cost basis, risk limits, personal Watchlist data, or any
  personal financial information.
- Configure a monitored SEC identity.
- Keep issuer feeds, GDELT, Bluesky, options, and sentiment disabled.
- Use `risk_mode=research`, `include_sources=true`, and `include_raw_signals=false`.
- Create a new empty local output directory outside the repository. Generated dossiers
  must not be committed or published until separately sanitized and reviewed.

## Run

The current neutral runner filename is a deferred cleanup; invoke it directly:

```bash
CATALYST_EDGE_SEC_USER_AGENT="Company ops@example.com" \
CATALYST_EDGE_ISSUER_FEEDS=disabled \
CATALYST_EDGE_GDELT=disabled \
CATALYST_EDGE_BLUESKY=disabled \
uv run python scripts/run_design_partner_demo.py \
  AAPL NVDA TSLA RKLB BRK.B \
  --output-dir /absolute/local/path/five-ticker-release-sample
```

The runner invokes `catalyst_edge_score` once per ticker through the real local
composition root and writes five dossier JSON files plus `manifest.json`. If an evidence
item contains a claim ID, it reads every `catalyst_edge_claim_sources` page with a page
size of one and verifies exact total/no duplicates. It also selects one typed missing
family or retained rejection reason.

Exit status:

- `0`: five calls, complete available claim pagination, and a missing/rejected case pass.
- `1`: calls completed but claim pagination or missing/rejected proof is absent; record
  the bounded failure and do not invent evidence.
- `2`: input, configuration, output, or invocation failure.

## Review one dossier

Open `review_ticker` from `manifest.json` and verify:

1. `scoring_method=deterministic_v1` and `model_status=not_trained`.
2. Direction, score, confidence, and the effect of missing coverage.
3. Evidence family, timestamp, contribution, and official source links.
4. Coverage, missing/stale families, warnings, and retained reason records.
5. Next checks and the explicit absence of a buy/sell recommendation.

## Review provenance

When `claim_pagination` is present:

- confirm its claim ID matches the selected evidence context;
- open page files until `next_cursor` is null;
- confirm `returned_source_count == total_sources`;
- confirm every `source_reference_id` is unique; and
- inspect source identity/tier, record/accession ID, canonical URL, times, hash, parser
  version, and policy decision.

If SEC-only evidence produces no grouped claim, record that bounded result. Do not enable
an uncleared source solely to force pagination.

## Review missing or rejected data

Confirm `missing_or_rejected_case` is represented as data quality, contributes no
fabricated evidence, and does not become a directional signal. Valid examples include
licensed-source requirements, unsupported fund identity, source outage, or no observation.

## Sanitize the launch example

Before using any output publicly:

- copy only the minimum dossier/provenance fields needed to demonstrate the product;
- remove local paths, environment values, internal timestamps, and machine identifiers;
- retain official source links, method/model status, missingness, and limitations;
- verify every displayed source permits the shown fields and attribution; and
- label the example historical, deterministic, unbacktested, and non-advisory.

## Record result

Record release version/hash, secret-free configuration hash, fixed tickers, start/end
time, exit status, manifest hash, reviewer, each check result, and any explicit exception.
A successful command without retained dossier/page evidence is not release proof.
