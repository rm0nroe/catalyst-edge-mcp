# Bluesky Forward Collector Live Validation — 2026-08-03

## Result

The out-of-band collector reached the official direct AppView fallback and recorded
one completed UTC day in an isolated SQLite store. AAPL, TSLA, RKLB, and Berkshire
produced adequate day-1 buckets. NVDA failed closed because AppView reported 491 hits
against a 100-row bounded first page.

This validates live first-page collection, exact-match filtering, safe retention,
reported-overflow handling, and cache-only MCP warm-up. It does **not** satisfy the
14-day live observation gate, enable the public default, or prove representative social
coverage.

## Live collection

- Window: `2026-08-02T00:00:00Z` through `2026-08-03T00:00:00Z`
- Hosts: `public.api.bsky.app` first, `api.bsky.app` only fallback; persisted collector
  state records the direct official fallback.
- Isolated store: `/tmp/catalyst-bluesky-live.QTasb6/evidence.sqlite3`
- Command:

```bash
CATALYST_EDGE_EVIDENCE_STORE=/tmp/catalyst-bluesky-live.QTasb6/evidence.sqlite3 \
  uv run catalyst-edge-refresh-bluesky AAPL NVDA TSLA RKLB BRK-A BRK-B
```

| Issuer query | Locally exact-matched posts | Unique authors | AppView `hitsTotal` | Cursor present | Bucket state |
| --- | ---: | ---: | ---: | --- | --- |
| AAPL / Apple Inc | 17 | 7 | 67 | yes | adequate; warm-up 1/14 |
| NVDA / NVIDIA | 81 | 55 | 491 | yes | truncated; failed closed |
| TSLA / Tesla Inc | 13 | 5 | 29 | yes | adequate; warm-up 1/14 |
| RKLB / Rocket Lab | 9 | 8 | 10 | yes | adequate; warm-up 1/14 |
| BRK-A + BRK-B / Berkshire Hathaway | 23 | 9 | 32 | yes | adequate; warm-up 1/14 |

AppView returned a cursor even when `hitsTotal` equaled the returned page size. The
collector therefore treats a reported hit total greater than the page length—not cursor
presence alone—as overflow, while still never making a cursor request. NVDA demonstrated
the overflow gate.

## Cache-only MCP readback

With Bluesky explicitly enabled against the isolated store, the AAPL MCP response
reported:

```json
{
  "family": "social",
  "available": false,
  "status": "no_observations",
  "reason": "no_observations",
  "coverage_ratio": 0.0,
  "warning": "Bluesky partial public attention warm_up: 1 of 14 adequate forward daily buckets; no trend was inferred.",
  "social_evidence": []
}
```

No request-time AppView call is possible in the production composition root; focused
tests replace its HTTP client with a transport that raises on any request.

## Retention proof

The live `social_bucket.metrics_json` objects contained only these keys:

`author_sha256s`, `coverage`, `coverage_state`, `cursor_present`, `newest_at`,
`partial_population`, `post_count`, `raw_sha256`, `reported_hits_total`,
`representative_urls`, `search_model`, `unique_authors`, `uri_sha256s`, `window_end`,
and `window_start`.

No post body, profile text, image, engagement field, raw cursor, account credential, or
private data is retained. The implementation auto-prunes to 14 completed daily buckets
and provides `catalyst-edge-purge-bluesky-cache TICKER...` for immediate local deletion.

## Remaining gates

- Accumulate 14 consecutive adequate completed-day buckets. NVDA cannot qualify while
  its daily query reports more than the bounded first page.
- Prove at least one neutral social observation through the complete live MCP response.
- Integrate the forward collector into the MCPB release worktree, then expose the
  disabled-default package opt-in and privacy link.
- Obtain explicit owner approval of the exact policy and current terms before public or
  customer enablement.
