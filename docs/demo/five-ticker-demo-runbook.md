# Five-Ticker Design-Partner Demo Runbook

**Purpose:** Prove the implemented core contract only: five repeated one-ticker calls, one dossier review, complete bounded provenance pagination, and one explicit missing or rejected-data case.

## Preconditions

- Use the exact release candidate and customer configuration being evaluated.
- Complete the deployment rights record first; disabled sources remain disabled.
- Ask the customer for five public-company tickers. Do not request holdings, position sizes, cost basis, risk limits, or personal financial data.
- Use `risk_mode=research`, `include_sources=true`, and `include_raw_signals=false` unless the signed scope says otherwise.
- Create an empty customer-approved output directory. Dossiers may contain licensed or customer-restricted metadata; do not publish them.

## Run

From the installed release checkout or equivalent environment:

```bash
uv run python scripts/run_design_partner_demo.py \
  TICKER1 TICKER2 TICKER3 TICKER4 TICKER5 \
  --output-dir /customer-approved/path/five-ticker-demo
```

The runner calls `catalyst_edge_score` once per ticker through the real local composition root. It writes five full dossier JSON files plus `manifest.json`. If a returned evidence item contains a claim ID, it reads every `catalyst_edge_claim_sources` page from the same local evidence store with a page size of one, writes those pages, and verifies exact total/no duplicates. It also selects a typed missing family or retained rejection reason for A7.

Exit status:

- `0`: five calls completed, complete claim pagination was verified, and a missing/rejected case was found.
- `1`: all calls completed but A6 or A7 lacks proof; this is a failed demo gate, not a reason to invent evidence.
- `2`: invalid inputs, configuration, output, or invocation failure.

## Review one dossier

Open the dossier named by `review_ticker` in `manifest.json` and have the customer identify:

1. `scoring_method=deterministic_v1` and `model_status=not_trained`.
2. Direction, score, confidence, and why missing coverage limits interpretation.
3. Each evidence family, timestamp, contribution, and visible source link.
4. `data_quality.coverage`, missing/stale families, warnings, and retained reason records.
5. The next checks and the absence of a buy/sell recommendation.

## Review provenance

Use `claim_pagination` in the manifest:

- confirm the claim ID equals the claim ID in the selected evidence context;
- open page files in order until `next_cursor` is null;
- confirm `returned_source_count == total_sources`;
- confirm every `source_reference_id` is unique;
- inspect source ID/tier, accession or record ID, canonical URL, publication/observation/retrieval time, hash if present, parser version, and policy decision.

## Review missing or rejected data

Use `missing_or_rejected_case` in the manifest. Confirm the named family/reason is displayed as data quality, contributes no fabricated evidence, and does not become a directional signal. Typical valid examples are `licensed_transaction_feed_required`, `licensed_ohlc_feed_required`, unsupported fund identity, rejected discovery entity, source outage, or no observation.

## Record result

Record release version/hash, configuration hash without secrets, five customer tickers, start/end time, runner exit status, output manifest hash, reviewer, A1-A8 result, and any explicit exception. A successful terminal command without the retained dossier/page evidence is not acceptance proof.
