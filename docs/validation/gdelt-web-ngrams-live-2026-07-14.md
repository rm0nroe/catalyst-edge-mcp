# GDELT Web NGrams live validation — 2026-07-14

## Decision

The out-of-band discovery command now uses GDELT's official June 2026 Web
NGrams plus TOC files instead of the overloaded legacy DOC 2.0 search API.
Request-time MCP evaluation remains cache-only.

Official source documentation:

- [Using The New Web NGrams Dataset To Find Relevant Coverage](https://blog.gdeltproject.org/using-the-new-web-ngrams-dataset-to-find-relevant-coverage/)

## Live upstream evidence

- The legacy AAPL DOC request returned HTTP 429 and directed high-traffic users
  to the Web NGrams dataset.
- The secure Google Storage path published current index and TOC files. The
  sampled `20260714230100` pair was approximately 7.6 MB compressed for the
  quadgram index and 256 KB compressed for the TOC.
- The replacement command processed two current minute pairs once for the full
  five-ticker batch and exited 0.

```text
AAPL   fresh           11 cached evidence items, 0 new matches
NVDA   fresh            5 cached evidence items, 6 new matches
TSLA   fresh            1 cached evidence item,  1 new match
BRK.B  fresh            3 cached evidence items, 3 new matches
RKLB   no_observations  0 cached evidence items, 0 new matches
```

The cache count can be lower than the raw match count because the canonical
event graph deduplicates repeated publisher coverage.

## Request-time verification

The subsequent five live smokes contained no GDELT stale-cache, timeout,
rate-limit, or schema warning. AAPL, NVDA, TSLA, and BRK.B returned fresh GDELT
publisher-link evidence. RKLB correctly returned no GDELT observations while
retaining SEC provenance and `launch_ready=true`.

## Safety and retention

- Only the exact HTTPS `storage.googleapis.com/data.gdeltproject.org/gdeltv5/
  weblegacy/ngrams` file path is accepted.
- Each minute pair is downloaded once and matched against every requested
  reviewed issuer.
- Compressed and decompressed byte limits, a five-file limit, a 20-minute
  discovery window, 30-second per-file timeouts, 64 KB line limits, and a
  50-document per-issuer cap bound the collector.
- Only TOC title, timestamp, domain, hash, and HTTPS publisher URL metadata is
  retained. Ngram context and article bodies are not stored.
- Missing files, HTTP failures, timeouts, malformed gzip/schema, and unexpected
  endpoints remain typed failures that preserve prior cached evidence.

## Verification

- `uv run pytest -q`
- `uv run ruff check .`
- `uv lock --check`
- `git diff --check`
- `uv run --env-file .env catalyst-edge-refresh-gdelt AAPL NVDA TSLA BRK.B RKLB --lookback-days 14`
- Five live `catalyst-edge-smoke` runs against the same ticker set
