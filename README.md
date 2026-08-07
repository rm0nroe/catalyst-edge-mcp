# CATALYST/EDGE

<!-- mcp-name: io.github.rm0nroe/catalyst-edge-mcp -->

![Abstract source-linked evidence ledger](assets/readme/catalyst-edge-social-preview.png)

Source-linked market intelligence for AI agents.

Catalyst Edge is a local, read-only [Model Context Protocol](https://modelcontextprotocol.io/)
server for public-company research. Ask an agent what changed for a ticker, why it
matters, what contradicts it, and which sources support the answer.

It combines direct SEC filings and ownership records with optional, policy-gated
sources into a compact evidence dossier. Every result preserves its source links
and missing-data warnings.

**Local first.** Evidence and configuration stay on your machine. **Research only.**
The deterministic scorer is untrained and unbacktested; Catalyst Edge does not provide
investment advice, trading signals, or execution.

---

## Install

Catalyst Edge requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).
The SEC requires an identifiable `User-Agent`; use your organization and a monitored
email address.

### Codex

```bash
codex mcp add catalyst-edge \
  --env 'CATALYST_EDGE_SEC_USER_AGENT=YOUR_ORGANIZATION YOUR_EMAIL' \
  --env 'CATALYST_EDGE_EVIDENCE_STORE=/absolute/local/path/evidence.sqlite3' \
  -- uvx --from 'catalyst-edge-mcp==0.1.4' catalyst-edge-mcp
```

Start a fresh task and verify that Codex discovers these two tools:

| Tool | Use |
| --- | --- |
| `catalyst_edge_score` | Return a compact catalyst-evidence dossier for a ticker. |
| `catalyst_edge_claim_sources` | Page through the immutable source records behind a claim. |

### Claude Desktop

Download [`catalyst-edge-mcp-0.1.4.mcpb`](https://github.com/rm0nroe/catalyst-edge-mcp/releases/download/v0.1.4/catalyst-edge-mcp-0.1.4.mcpb),
then choose **Settings → Extensions → Advanced settings → Install Extension…**.
Enter the same SEC identity when prompted. The extension is an unsigned custom bundle;
review the source and published checksum before accepting Claude Desktop's warning.

---

## Use

Ask your agent a focused research question, for example:

> What changed for NVDA in the last 14 days? Include sources, missing evidence, and
> anything that would weaken the conclusion.

The primary tool accepts a ticker, a 1–90 day lookback, source inclusion, and a
research context:

```json
{
  "ticker": "NVDA",
  "lookback_days": 14,
  "include_sources": true,
  "include_raw_signals": false,
  "risk_mode": "research"
}
```

`risk_mode` also supports `alert_triage` and `thesis_review`. Ticker validation runs
before any provider is composed; invalid inputs fail clearly rather than producing a
partial score.

### From a terminal

```bash
# Run the local stdio MCP server
uvx --from 'catalyst-edge-mcp==0.1.4' catalyst-edge-mcp

# Get a dossier directly
uvx --from 'catalyst-edge-mcp==0.1.4' catalyst-edge-score NVDA --lookback-days 14
```

---

## What it uses

| Evidence | Default | Notes |
| --- | --- | --- |
| SEC filings and ownership records | Enabled with `CATALYST_EDGE_SEC_USER_AGENT` | Primary regulatory evidence. |
| GDELT Web NGrams discovery | Enabled | Attributed, cache-only discovery metadata; set `CATALYST_EDGE_GDELT=disabled` to opt out. |
| Issuer RSS/Atom feeds | Disabled | Enable explicitly with `CATALYST_EDGE_ISSUER_FEEDS=enabled`. |
| Bluesky public attention | Disabled | Enable explicitly with `CATALYST_EDGE_BLUESKY=enabled`; it is incomplete, neutral-only context. |
| Options, technicals, and sentiment | Disabled | Not composed without an approved, rights-cleared provider. |

The default evidence store is local SQLite at
`~/.local/state/catalyst-edge-mcp/evidence.sqlite3`. Set
`CATALYST_EDGE_EVIDENCE_STORE` to choose another local path.

### Check local readiness

```bash
CATALYST_EDGE_SEC_USER_AGENT='YOUR_ORGANIZATION YOUR_EMAIL' \
uvx --from 'catalyst-edge-mcp==0.1.4' catalyst-edge-smoke NVDA --lookback-days 14
```

The smoke check reports sanitized configuration, provenance, coverage, and readiness
status. It never prints credentials or provider payloads.

---

## How to read a result

Each dossier includes a deterministic `score`, `direction`, `confidence`, source-linked
evidence, missing or stale families, and next checks. `model_status` is always
`not_trained` in this release. A neutral or no-data result is a valid answer: missing
evidence is uncertainty, not bearish evidence.

Evidence is compact by design. Use `catalyst_edge_claim_sources` with a claim ID to
retrieve its paginated source records, including canonical URLs, timestamps, hashes,
parsers, and policy decisions.

```json
{
  "ticker": "NVDA",
  "edge": {"score": 62, "direction": "bullish", "confidence": 0.69, "scoring_method": "deterministic_v1", "model_status": "not_trained"},
  "data_quality": {"coverage": "partial", "missing_families": [], "warnings": ["Deterministic v1 scoring is not backtested."]}
}
```

```json
{
  "ticker": "NVDA",
  "edge": {"score": 50, "direction": "neutral", "confidence": 0, "scoring_method": "deterministic_v1", "model_status": "not_trained"},
  "data_quality": {"coverage": "none", "missing_families": ["options_flow"], "warnings": ["options_flow provider yfinance is private diagnostic only; no production evidence or coverage credit was granted."]}
}
```

```json
{
  "ticker": "NVDA",
  "edge": {"score": 50, "direction": "neutral", "confidence": 0, "scoring_method": "deterministic_v1", "model_status": "not_trained"},
  "data_quality": {"coverage": "none", "missing_families": ["filings_news", "insider_trading", "options_flow", "social", "technical"], "warnings": ["No live evidence adapters are configured."]}
}
```

---

## Privacy

Results and SQLite evidence remain on your machine. Ticker and issuer queries may be
sent directly to whichever public-source providers you enable. The SEC identity is sent
only to `sec.gov` as its required request `User-Agent`.

Read the [Catalyst Edge Privacy Policy](https://catalyst.ryanmonroe.ai/privacy.html).

---

## Build from source

```bash
uv sync --frozen --extra dev
uv run --frozen pytest
uv run --frozen ruff check .
uv build --no-sources --out-dir dist
```

Default tests are offline and use sanitized fixtures. The release workflow tests Python
3.10 and 3.14, MCP contracts, a clean build, and the packaged artifact.

## License

[MIT](LICENSE)
