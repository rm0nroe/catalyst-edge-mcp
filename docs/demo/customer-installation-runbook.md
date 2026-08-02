# Customer-Installed MCP Runbook

**Status:** Reusable local procedure. Replace every placeholder with the accepted customer release record; this document does not authorize delivery or source enablement.

## Prerequisites and timer boundary

Have these ready before starting the onboarding timer:

- a supported Python runtime, `uv`, and the customer's local MCP client;
- the pinned wheel, source distribution, and signed SHA-256 manifest;
- an absolute customer-owned evidence-store path;
- the completed customer configuration and deployment rights records;
- the prior pinned wheel and prior configuration for rollback.

Start the timer immediately before artifact hash verification. Stop only when the actual MCP client lists exactly `catalyst_edge_score` and `catalyst_edge_claim_sources`. Retain the first attempt, all commands, versions, exits, corrections, and readback even if the five-minute target is missed.

## Verify and install

```bash
sha256sum -c catalyst-edge-mcp-VERSION-SHA256SUMS.txt
uv venv --python 3.10 /absolute/customer/path/catalyst-edge-venv
uv pip install \
  --python /absolute/customer/path/catalyst-edge-venv/bin/python \
  /absolute/customer/path/catalyst_edge_mcp-VERSION-py3-none-any.whl
```

Do not copy credentials into client-visible chat or command history. Inject any approved credentials through the customer-controlled process environment. A credential does not approve a source.

The fail-closed offline configuration is:

```text
CATALYST_EDGE_TRANSPORT=stdio
CATALYST_EDGE_ISSUER_FEEDS=disabled
CATALYST_EDGE_GDELT=disabled
CATALYST_EDGE_BLUESKY=disabled
CATALYST_EDGE_OPTIONS_PROVIDER=none
CATALYST_EDGE_SENTIMENT_MODEL=disabled
CATALYST_EDGE_EVIDENCE_STORE=/absolute/customer/path/evidence.sqlite3
```

Use the absolute installed command in the customer's MCP client configuration:

```json
{
  "mcpServers": {
    "catalyst-edge": {
      "command": "/absolute/customer/path/catalyst-edge-venv/bin/catalyst-edge-mcp",
      "env": {
        "CATALYST_EDGE_TRANSPORT": "stdio",
        "CATALYST_EDGE_ISSUER_FEEDS": "disabled",
        "CATALYST_EDGE_GDELT": "disabled",
        "CATALYST_EDGE_BLUESKY": "disabled",
        "CATALYST_EDGE_OPTIONS_PROVIDER": "none",
        "CATALYST_EDGE_SENTIMENT_MODEL": "disabled",
        "CATALYST_EDGE_EVIDENCE_STORE": "/absolute/customer/path/evidence.sqlite3"
      }
    }
  }
}
```

Restart the customer-owned MCP client and retain its tool-list readback. A server process that starts without the client readback does not pass onboarding.

## Local release-candidate proof

The repository verifier uses the official MCP SDK client against a clean installed wheel and sdist, checks exact two-tool discovery, and makes one schema-valid no-data call:

```bash
uv run python scripts/verify_release.py artifact \
  --wheel /absolute/path/catalyst_edge_mcp-VERSION-py3-none-any.whl \
  --sdist /absolute/path/catalyst_edge_mcp-VERSION.tar.gz \
  --python 3.10 \
  --manifest /absolute/path/catalyst-edge-mcp-VERSION-SHA256SUMS.txt \
  --record /absolute/path/artifact-verification.json
```

This local SDK proof is CI and runbook evidence. Customer acceptance still requires readback from the customer's named client and environment.

## Rollback

1. Stop the customer-owned MCP process.
2. Copy the current configuration and SQLite database, including WAL/SHM companions when present, to the customer-approved backup location.
3. Reinstall the prior wheel by exact path; do not delete the evidence store.
4. Restore the prior configuration without overwriting customer-controlled secrets.
5. Restart the MCP client and retain exact two-tool discovery plus one schema-valid call.
6. Record artifact/configuration hashes, versions, commands, readback, data warnings, and backup ownership.

Any incompatible or one-way database migration blocks delivery until an explicit restore test passes.

## Required retained record

- start/end time and first-attempt duration;
- platform, Python, `uv`, MCP client, and package versions;
- wheel/sdist/configuration/registry hashes;
- install command and exit status;
- exact two-tool discovery readback;
- schema-valid call result boundary, not customer evidence content;
- every correction and exception;
- rollback artifact/configuration, backup path/owner, and post-rollback readback.
