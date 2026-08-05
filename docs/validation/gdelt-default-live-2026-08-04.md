# GDELT Default-Enable Live Validation — 2026-08-04

## Decision

Enable attributed GDELT Web NGrams discovery by default in Catalyst Edge Research
v0.1.4. Preserve `CATALYST_EDGE_GDELT=disabled` as an explicit opt-out. GDELT evidence
remains neutral discovery metadata and cannot establish readiness or outrank primary
evidence.

## Rights and output contract

The official [GDELT Terms of Use](https://www.gdeltproject.org/about.html#termsofuse),
read on 2026-08-04, allow unlimited academic, commercial, and governmental use and
redistribution without fee while requiring every use or redistribution to cite and link
to the GDELT Project. Version 0.1.4 returns `The GDELT Project` and
`https://www.gdeltproject.org/` in every GDELT-bearing dossier and claim page, including
when `include_sources=false`, and in GDELT refresh and health output.

## Fresh isolated-cache proof

- Cohort: AAPL, NVDA, TSLA, RKLB, BRK-B; 14-day reporting window.
- Collector: two bounded Web NGrams minute files, request-time cache disabled during
  refresh, no article-body retrieval or retention.
- Freshness: all five registered issuers reported `fresh`, no degraded result, with the
  same successful check timestamp.
- NVDA: 14 candidates, 4 accepted/ingested, 10 rejected as `title_not_aligned`.
- TSLA: 7 candidates, 0 accepted; five rejected for missing required context and two for
  title misalignment.
- AAPL, RKLB, BRK-B: no candidates in the bounded minute sample.
- Manual review of the three surfaced NVDA dossier items found each title explicitly
  aligned to NVIDIA. Every item remained `publisher_link_discovery`, neutral, and
  `discovery_only`.
- Refresh, health, and dossier outputs each included the mandatory GDELT citation/link.

This proves a fresh bounded collector and precise fail-closed sample, not comprehensive
news coverage or predictive value.
