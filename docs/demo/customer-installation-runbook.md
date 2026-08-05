# Local Self-Serve Installation and Rollback Runbook

**Status:** Current Local Beta procedure for the pinned PyPI package. The legacy filename
is retained for release continuity. It does not authorize additional source enablement.

## Prerequisites

- Python 3.10+ and `uv`.
- Claude Desktop, Codex, or another local stdio MCP client.
- The pinned `catalyst-edge-mcp==0.1.2` PyPI package.
- A monitored SEC identity in `Company email@example.com` form.
- An absolute user-owned local evidence-store path.
- The prior pinned wheel/configuration when testing rollback.

Issuer feeds, GDELT, Bluesky, options, and sentiment are disabled by default. Do not
enable them merely to obtain more output; follow the current source-rights matrix.

## Install from PyPI

```bash
uv tool install 'catalyst-edge-mcp==0.1.2'
uv tool list
```

Keep credentials out of chat, committed files, and shell history. The SEC identity is a
contact identifier, not a secret, but it must be real and monitored.

## Public-default environment

```text
CATALYST_EDGE_SEC_USER_AGENT=Company ops@example.com
CATALYST_EDGE_TRANSPORT=stdio
CATALYST_EDGE_ISSUER_FEEDS=disabled
CATALYST_EDGE_GDELT=disabled
CATALYST_EDGE_BLUESKY=disabled
CATALYST_EDGE_OPTIONS_PROVIDER=none
CATALYST_EDGE_SENTIMENT_MODEL=disabled
CATALYST_EDGE_EVIDENCE_STORE=/absolute/local/path/evidence.sqlite3
```

## Add to Codex

The installed Codex CLI supports stdio MCP registration with `codex mcp add`:

```bash
codex mcp add catalyst-edge \
  --env 'CATALYST_EDGE_SEC_USER_AGENT=Company ops@example.com' \
  --env 'CATALYST_EDGE_EVIDENCE_STORE=/absolute/local/path/evidence.sqlite3' \
  -- uvx --from 'catalyst-edge-mcp==0.1.2' catalyst-edge-mcp
codex mcp get catalyst-edge
```

The omitted source toggles remain disabled by runtime default. Open a fresh Codex task and
confirm exact discovery of `catalyst_edge_score` and `catalyst_edge_claim_sources` before
calling one public ticker.

## Add to Claude Desktop manually

Configure the pinned PyPI package manually while the production-trusted one-click `.mcpb`
channel remains withheld:

```json
{
  "mcpServers": {
    "catalyst-edge": {
      "command": "uvx",
      "args": ["--from", "catalyst-edge-mcp==0.1.2", "catalyst-edge-mcp"],
      "env": {
        "CATALYST_EDGE_SEC_USER_AGENT": "Company ops@example.com",
        "CATALYST_EDGE_EVIDENCE_STORE": "/absolute/local/path/evidence.sqlite3"
      }
    }
  }
}
```

Restart Claude Desktop and confirm exact discovery of the same two tools. Process startup
without client tool readback does not prove onboarding.

## Local SDK artifact proof

Maintainers can verify a wheel/sdist without changing a user MCP configuration:

```bash
uv run python scripts/verify_release.py artifact \
  --wheel /absolute/path/catalyst_edge_mcp-VERSION-py3-none-any.whl \
  --sdist /absolute/path/catalyst_edge_mcp-VERSION.tar.gz \
  --python 3.10 \
  --manifest /absolute/path/catalyst-edge-mcp-VERSION-SHA256SUMS.txt \
  --record /absolute/path/artifact-verification.json
```

This proves SDK-client installation and tool discovery; it does not replace the Codex and
Claude Desktop user-path checks.

## Local data and privacy boundary

- The evidence store is local SQLite/WAL state at the configured absolute path.
- Back up or delete the SQLite file and any `-wal`/`-shm` companions together while the
  MCP process is stopped.
- Tool inputs are public-company tickers and research-mode options. Do not submit holdings,
  positions, account credentials, material nonpublic information, or personal financial
  data.
- Provider credentials, if ever added under an approved source decision, remain in the
  local process environment and must not be logged or returned.

## Rollback

1. Stop the local MCP client/process.
2. Back up the current configuration and SQLite database plus WAL/SHM companions.
3. Reinstall the prior wheel by exact path; do not delete the evidence store.
4. Restore the prior secret-free configuration.
5. Restart the client and retain exact two-tool discovery plus one schema-valid call.
6. Record artifact/configuration hashes, versions, commands, readback, warnings, and
   backup path.

Any incompatible or one-way database migration blocks release until this restore test
passes.

## Required retained QA record

- start/end time and first-attempt duration;
- platform, Python, `uv`, MCP client, and package versions;
- artifact, configuration, registry, and manifest hashes;
- install/registration commands and exits;
- exact two-tool discovery readback;
- schema-valid call boundary, never personal research content;
- every correction/exception; and
- rollback artifacts, backup path, and post-rollback readback.
