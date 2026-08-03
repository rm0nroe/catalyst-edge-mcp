# Bluesky Partial Public Attention Decision — 2026-08-03

**Decision:** Implemented but disabled by public default. A local user may explicitly
opt in with `CATALYST_EDGE_BLUESKY=enabled`. This is an engineering and product-output
decision, not legal advice or permission to sell or redistribute user content.

## Approved local behavior

- Use only unauthenticated `app.bsky.feed.searchPosts` reads on
  `public.api.bsky.app`, with `api.bsky.app` as the only fallback.
- Run collection outside MCP requests every six hours. Query one bounded ranked first
  page for the previous completed UTC day; never follow a cursor and never backfill a
  claimed historical series.
- Search only reviewed exact cashtags and reviewed company aliases. Deduplicate AT URIs
  in memory before deriving a daily bucket.
- Retain 14 completed daily buckets: post count, unique-author count, pseudonymous
  SHA-256 URI and author identifiers, response hash, coverage/outage state, timestamps,
  and at most three representative links per bucket. Never retain post bodies, profile
  text, images, engagement metadata, direct messages, credentials, or account data.
- Auto-prune older buckets. `catalyst-edge-purge-bluesky-cache TICKER...` deletes a
  reviewed issuer's Bluesky buckets and collector state immediately.
- If a recheck loses a previously observed URI hash, mark the bucket
  `deletion_uncertain` and emit no trend. A known report, deletion, or takedown requires
  local purge and a new 14-day warm-up; search does not provide a reliable deletion feed.

## Output contract

- Request-time evaluation reads SQLite only and performs no Bluesky network request.
- Output remains neutral and says `partial public attention`, never sentiment,
  representativeness, market-wide coverage, or predictive value.
- Compare only two locally observed equal seven-day windows after 14 consecutive
  adequate completed-day buckets. Require at least five exact-match posts and three
  unique authors in each window.
- Warm-up, missing days, reported hit overflow, rate limits, permission errors, timeouts, schema
  errors, stale state, deletion uncertainty, and insufficient samples all fail closed.
- Representative source output is limited to three links for the current comparison
  window. Raw signals expose derived counts only when the caller explicitly requests
  raw signals.

## Source and rights boundary

The official API directory says many public endpoints require no authentication and
prefers `public.api.bsky.app` for public-web use. Official AppView rate guidance calls
the limits generous and asks public-web developers to use the cached host. The developer
guidelines require a deletion method, monitored contact information, and reasonable
security. Bluesky's terms state that users retain ownership of their content and describe
account/content deletion across the decentralized network.

Those materials do not provide Catalyst Edge a blanket license to rehost post bodies or
an explicit commercial-output grant over user-owned content. Therefore Local Beta keeps
Bluesky disabled by default even though the minimized local implementation exists.

Official references:

- <https://docs.bsky.app/docs/advanced-guides/api-directory>
- <https://docs.bsky.app/docs/advanced-guides/rate-limits>
- <https://docs.bsky.app/docs/support/developer-guidelines>
- <https://bsky.social/about/support/tos>
- <https://bsky.social/about/support/privacy-policy>

## Remaining release gates

- Owner approval of this exact opt-in/output policy against the then-current terms.
- Fourteen consecutive adequate live daily buckets and one complete cache-only MCP
  response containing a neutral Bluesky observation.
- Public contact/report handling and the package privacy link must be present in the
  release artifact.
- The MCPB may expose its disabled-default opt-in only after this forward-collector code
  is integrated into the release worktree; the current 0.1.1 artifact remains hard-disabled.

Until all three pass, the MCPB and registry defaults remain `disabled`.
