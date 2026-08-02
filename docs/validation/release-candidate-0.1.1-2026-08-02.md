# Catalyst Edge MCP Local Release Candidate 0.1.1

**Recorded:** 2026-08-02
**Status:** Local technical evidence only. No commit, tag, push, release, upload, registry listing, customer delivery, source enablement, price, legal approval, or signature is authorized or represented by this record.

## Source and version decision

- Branch: `codex/dynamic-market-universe-design`.
- Base source identity: `HEAD == main == origin/main == 3ddec750ae025c8b990ecfbad0b0346c8c625595` before this implementation.
- Merge state: no `.git/MERGE_HEAD`.
- Candidate version: `0.1.1`, deliberately distinct from prior pinned `0.1.0` so forward install and rollback can be proven without ambiguous same-version artifacts.
- Package and lock agree on `0.1.1`; `uv.lock` SHA-256 is `a996b00ce76863f83f579ddf7a28631f2fd5461fec505a25165b3484f153e2e3`.
- The working tree is intentionally uncommitted and contains the recorded execution pack plus preserved unrelated `notes/` artifacts. This prevents a clean-commit release claim and keeps R1/R2 partial.

## Candidate artifacts

Build command:

```text
uv build --no-sources --out-dir /tmp/catalyst-edge-rc-0.1.1-listing-final.zglGAM
```

| Artifact/record | SHA-256 |
| --- | --- |
| `catalyst_edge_mcp-0.1.1-py3-none-any.whl` | `f600d83481a5dde0a5771bd2fa3f4630d063f9ea6717a3286867dc1b463b68d3` |
| `catalyst_edge_mcp-0.1.1.tar.gz` | `e360daf2d9d3d76912ac4f7d5d233b82be7eb4f19e08f7d199b9290dc1f002c1` |
| `catalyst-edge-mcp-0.1.1-SHA256SUMS.txt` | `983410b6e7435564ea901632e60fdd4fd295c4c79cfdf768b5d4b3ef300a0f38` |
| `artifact-verification.json` | `e991aa0e4f14d008599310320f5fa4cde2a264c86dec988fb694ba6477072f8b` |

Local artifact directory: `/tmp/catalyst-edge-rc-0.1.1-listing-final.zglGAM`.

An independent build at `/tmp/catalyst-edge-rc-0.1.1-listing.GtDu3u` reproduced both artifact hashes byte-for-byte and repeated the installed-artifact probes successfully.

Both wheel and sdist installed offline into separate fresh Python 3.10 environments. Each exposed the five declared console scripts, including required `catalyst-edge-mcp`, `catalyst-edge-score`, and `catalyst-edge-smoke`; the actual MCP SDK client discovered exactly `catalyst_edge_score` and `catalyst_edge_claim_sources`; and one offline invocation returned the schema-valid `deterministic_v1`, `not_trained`, `coverage=none` response. The installed wheel passed that same proof over loopback streamable HTTP as well as stdio; the sdist repeated stdio coverage.

## Source-distribution inventory

The sdist has 49 members. The verifier found no absolute/traversal/link entries, `.env`, bytecode/cache, SQLite/WAL/SHM state, or credential/secret filename. Its exact non-generated inventory is:

```text
.env.example
uv.lock
catalyst_edge_mcp/__init__.py
catalyst_edge_mcp/capability_gates.py
catalyst_edge_mcp/cli.py
catalyst_edge_mcp/collection_lifecycle.py
catalyst_edge_mcp/compat.py
catalyst_edge_mcp/discovery_registry.py
catalyst_edge_mcp/entity_resolution.py
catalyst_edge_mcp/evidence_store.py
catalyst_edge_mcp/gdelt_refresh.py
catalyst_edge_mcp/gdelt_web_ngrams.py
catalyst_edge_mcp/issuer_registry.py
catalyst_edge_mcp/models.py
catalyst_edge_mcp/reason_records.py
catalyst_edge_mcp/redaction.py
catalyst_edge_mcp/registry_config.py
catalyst_edge_mcp/registry_models.py
catalyst_edge_mcp/scorer.py
catalyst_edge_mcp/sec_document_rules.py
catalyst_edge_mcp/sec_filings.py
catalyst_edge_mcp/sec_funds.py
catalyst_edge_mcp/sec_ownership.py
catalyst_edge_mcp/server.py
catalyst_edge_mcp/service.py
catalyst_edge_mcp/settings.py
catalyst_edge_mcp/smoke.py
catalyst_edge_mcp/social_registry.py
catalyst_edge_mcp/source_policy.py
catalyst_edge_mcp/summary.py
catalyst_edge_mcp/validation.py
catalyst_edge_mcp/adapters/__init__.py
catalyst_edge_mcp/adapters/base.py
catalyst_edge_mcp/adapters/bluesky.py
catalyst_edge_mcp/adapters/finnhub.py
catalyst_edge_mcp/adapters/fmp.py
catalyst_edge_mcp/adapters/gdelt.py
catalyst_edge_mcp/adapters/issuer_feeds.py
catalyst_edge_mcp/adapters/options.py
catalyst_edge_mcp/adapters/sec.py
catalyst_edge_mcp/data/reviewed_registries.json
docs/demo/five-ticker-demo-runbook.md
scripts/run_design_partner_demo.py
LICENSE
README.md
server.json
pyproject.toml
```

Hatchling also generated `.gitignore` and `PKG-INFO`, bringing the archive total to 49.

The official MCP Registry metadata at `server.json` passed the live `2025-12-11` schema. Its `0.1.1` PyPI/stdin package metadata matches the project version, and the packaged README contains the matching `io.github.rm0nroe/catalyst-edge-mcp` ownership marker.

## CI and local verification

`.github/workflows/validation.yml` implements read-only pull-request and release-tag validation with no publish, upload, release-creation, registry, or credential step:

- lock check and Ruff;
- the offline suite on Python 3.10 and 3.14;
- existing stdio and loopback streamable-HTTP contracts;
- clean `uv build --no-sources`;
- fresh wheel/sdist installation, required entrypoints, exact two-tool discovery, and typed no-data invocation;
- sdist inventory and secret/state exclusions;
- SHA-256 and collected-test summaries retained in the GitHub job summary.
- release-tag/package-version equality before any tag build can pass.
- a parsed workflow contract test for triggers, permissions, matrices, pinned actions, required commands, and absent publish/release/secret steps.

Local results after the final implementation:

| Check | Result |
| --- | --- |
| `uv lock --check` | Pass |
| `uv run ruff check .` | Pass |
| Python 3.10 offline suite | 443 collected, pass |
| Python 3.14 offline suite | 443 collected, pass |
| `git diff --check` | Pass |

The first Python 3.10 matrix attempt failed one composition-root test because workflow-wide source-disable variables changed expected default adapters from `issuer_feed/gdelt/bluesky` to none. Those semantic overrides were removed; the fixture/transport suite itself is offline, and both matrix endpoints then passed. This correction is retained rather than rewriting the first attempt.

Focused negative tests now reject unsafe/traversal/link archive members, runtime state and secret-like package paths, malformed/non-string/secret-like configuration, malformed or non-no-data responses, missing tools/entrypoints, and wheel/sdist version mismatch.

The workflow has not run on GitHub because no commit or push was authorized. R2 therefore remains partial despite local CI-equivalent success.

## Bounded package hygiene

Gitleaks 8.30.1 scanned the unpacked final wheel (44 files, 398.15 KB) and sdist (49 files, 949.25 KB) with full redaction and found no leaks. The verifier's filename/state rules found no `.env`, cache/bytecode, SQLite/WAL/SHM, or credential/secret-like path in either unpacked tree. Scan root: `/tmp/catalyst-edge-package-scan-listing.sfQ1hJ`. This is evidence only for those two unpacked artifacts, not the repository, machine, or external systems.

## Evidence audit

`docs/validation/release-candidate-0.1.1-2026-08-02.json` is the machine-readable source of truth for the current local proof paths, hashes, test counts, and R0-R7 statuses; SHA-256 `2efbf90230a1edefb4c8bbc9795fc3108e8b6c56ec3f9bc98634d3a94b1f0ddd`. `scripts/verify_release.py audit` re-read live package/lock versions, twelve source hashes, artifacts/manifest, stdio/HTTP probes, onboarding, rollback, demo records, both collected-test counts, and fail-closed gate statuses without rewriting the record; it passed.

The first audit attempt failed because its internal `uv run` omitted the `dev` extra and therefore lacked `rapidfuzz`. Adding the existing `dev` extra to that subprocess fixed the invocation; the evidence record then passed unchanged except for the verifier's updated source hash.

## Timed onboarding

- Record: `/tmp/catalyst-edge-rc-0.1.1-listing-final.zglGAM/artifact-verification.json`.
- Python: CPython 3.10; `uv 0.9.17`; actual client: installed `mcp` SDK `ClientSession` over stdio and loopback streamable HTTP.
- Start: artifacts, Python, `uv`, and MCP client prerequisite available; immediately before hash/inventory verification.
- Stop: the clean installed wheel returned exact two-tool discovery.
- First attempt: pass with no manual correction.
- Duration: **2.679 seconds**, below the 300-second target.

This is a clean local SDK-client proof, not a named customer's client/environment acceptance record.

## Rollback proof

The prior artifact was rebuilt from the exact clean checkpoint HEAD using `git archive HEAD`, producing the same recorded prior wheel hash:

- prior `0.1.0` wheel: `e6df5360edb6e3cee43b37a41b01e97980b4963d8c838d51a8253433e6d4d5d4`;
- prior configuration: `d56ce4a1d36e3a44976b4ee412db596639c1737ef847d74b5f5258baf98868aa`;
- candidate configuration: `c26ff14086d4c7ef7d161210cfe5d9062e705fed0f329c1c88129c539bc1f0ca`.

One clean Python 3.10 environment exercised `0.1.0 -> 0.1.1 -> 0.1.0`. Every state returned exact two-tool discovery and a schema-valid typed no-data call. The retained evidence-store backup, post-candidate store, and post-rollback store all hash to:

```text
edfee292409903a3fa4c7cf7ffc4da906b374d31cafc5c045224bb67e43be616
```

The `preserve-me` sentinel remained readable. Proof directory: `/tmp/catalyst-edge-rollback-0.1.1-listing.vtGXYT`; record SHA-256: `375813e8da5f98ecb4f6f2332d253a4d9984a2636d3cf8fe9c2de23826c391b4`.

## Five-ticker proof

Candidate `0.1.1` ran the approved local sample `AAPL NVDA TSLA RKLB BRK.B` with one call per ticker; this did not inspect or mutate the personal Watchlist.

- Five schema-valid calls: pass.
- AAPL claim `clm_15a3394ebfd24180731f6b8ff46e6b700455c27ce3a861e005c8d083f3af43ff`: one source, one page, exact total, no duplicate source ID.
- Missing/rejected proof: AAPL `insider_trading`, `source_unsupported` at family scope.
- Manifest: `/tmp/catalyst-edge-demo-0.1.1-listing.qqxKG5/proof/manifest.json`.
- Manifest SHA-256: `28076d08130f7943f568497cd16b0a342d7fd8d7be6227b34ad5dca06c8e67d1`.

The first regenerated attempt is retained at `/tmp/catalyst-edge-demo-0.1.1-followups.uJax71/proof`: five calls and typed missingness passed, but A6 failed because the synthetic title did not satisfy the reviewed issuer-alias policy (`cached_title_not_aligned=1`). The corrected local fixture explicitly named `Apple Inc. AAPL`; no live source, customer data, or personal Watchlist was read or mutated.

Automated A4/A6/A7 evidence passed. A5 still requires a customer reviewer to identify and acknowledge the dossier fields and limitations.

## R0-R7 status

| Gate | Status | Exact boundary |
| --- | --- | --- |
| R0 scope freeze | **Met locally** | product specification/technical specification/GTM retain two read-only local tools, one ticker per score call, deterministic unbacktested scoring, typed missingness, and no recommendation. |
| R1 reproducible artifact | **Partial** | Local `0.1.1` wheel/sdist, hashes, inventory, and fresh installs pass; no clean reviewed commit, tag, or release artifact exists. |
| R2 validation CI | **Partial** | Workflow is implemented and local Python 3.10/3.14 equivalents pass; no GitHub-hosted run or required-check configuration exists. |
| R3 configuration contract | **Partial** | `.env.example`, fail-closed customer template, local state/retention/credential rules, and diagnostics exist; actual customer owners, paths, rights rows, retention, and approvals do not. |
| R4 five-minute onboarding | **Partial** | Local actual MCP SDK client first attempt passed in 2.679 seconds; no named customer client/environment timing exists. |
| R5 demo acceptance | **Partial** | Local candidate passes automated five-call, pagination, and missingness evidence; customer-selected tickers, A5 review, and customer acknowledgement remain open. |
| R6 rollback | **Met locally** | Two pinned versions/configurations were exercised and prior version/tool contract restored without changing the retained evidence store. |
| R7 delivery authority | **Open; blocks delivery** | No actual customer/environment/source rights record, counsel-approved terms, selected price, authorized owners, or signatures exist. |

Passing the local technical evidence does not clear R7 and does not authorize paid delivery.
