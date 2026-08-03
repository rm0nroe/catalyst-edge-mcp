# Catalyst Edge MCPB Release Candidate 0.1.1

**Status:** Private preparatory evidence only. No repository visibility change, tag,
release, package upload, registry submission, landing-page change, or customer delivery
is authorized or represented by this record.

## Candidate provenance

- Base: local `main` at `1bbbb12187b9ef70a7b28129214b2331c53795e1`.
- Branch: `codex/mcpb-signing` in an isolated worktree.
- Package and manifest version: `0.1.1`.
- MCPB CLI: `@anthropic-ai/mcpb@2.1.2`, exact npm integrity pinned in
  `package-lock.json`.
- Runtime contract: MCPB manifest `0.4`, UV server, stdio transport, exactly
  `catalyst_edge_score` and `catalyst_edge_claim_sources`.
- Public defaults: SEC identity required; issuer feeds, GDELT, Bluesky, options, and
  sentiment explicitly disabled.

## Artifact proof

Two independent pack-and-normalize runs produced the same unsigned artifact:

- filename: `catalyst-edge-mcp-0.1.1.mcpb`;
- current SHA-256 after rebasing onto the 2026-08-03 `main` baseline:
  `6d7424f73ea34082f22736e7c5446df7b756cb53f2e0fec1076e8b056365f3b0`;
- allowed members: 47;
- ZIP order: lexical;
- ZIP timestamps: `1980-01-01T00:00:00`;
- prohibited credentials, `.env`, state, caches, tests, scripts, docs, and build output:
  absent.

The rebased installed-artifact proof produced:

- wheel `catalyst_edge_mcp-0.1.1-py3-none-any.whl` SHA-256
  `d4484ab855e14a85359f30eae7e9b23093b0720b920a6c64c721d03b160b902f`;
- sdist `catalyst_edge_mcp-0.1.1.tar.gz` SHA-256
  `ec8a45059f8caac64b12811b430354db839e6bc7ada5c463a08f49a6b2449714`;
- 51 allowed sdist members and no prohibited paths; and
- first-attempt wheel onboarding in 2.854 seconds with exact two-tool stdio and HTTP
  discovery plus schema-valid typed-missingness probes.

The pre-documentation unsigned payload used for client/signing QA had SHA-256
`ed3a473733202556355a8e0e69193b50dbfe97fead98bd4e13bfce18a97e347e`; only the
bundled README changed before the current candidate was packed. Its MCPB CLI
self-signed artifact had SHA-256
`566c2450eea76cb9c1f09bc49d27c9295ae93ae742694d212949143b7676f28e`.
Independent OpenSSL CMS verification passed and recovered that exact pre-documentation
unsigned SHA.
The CLI's own verification reported the self-signed certificate as untrusted, so it did
not provide an affirmative self-verification result.

Claude Desktop `1.24012.9` rejected that signed artifact during preview before install:

> Failed to preview extension: Invalid comment length. Expected: 2264. Found: 0.

The signature bytes appended by the CLI are therefore incompatible with this Claude ZIP
reader. This blocks a release-signed Claude artifact; the unsigned payload was used only
for local QA after its exact hash and inventory were verified.

## Client proof

### Codex

- Codex CLI `0.144.1` ran with an isolated home; persistent user configuration was not
  changed.
- All 45 extracted member bytes matched the exact self-signed QA archive.
- With the documented server-scoped tool approval set to `approve`, an AAPL call using
  the schema field `ticker` returned `coverage=partial`,
  `scoring_method=deterministic_v1`, `model_status=not_trained`, two SEC evidence items,
  and two null `claim_id` values.
- The isolated auth/config copies were securely destroyed after the run.

### Claude Desktop

- The exact self-signed QA artifact SHA-256
  `89633f4a3cd33e29c7619699fb6efd715f93e842b9ce7c88027b16c5a4da1797`
  was previewed, installed, configured, and enabled after explicit action-time approval.
- Preview displayed exactly the two public tools and all runtime requirements met; the
  developer remained unverified because the bundled verifier is fail-closed.
- A fresh AAPL call completed with partial coverage, deterministic v1 scoring,
  `not_trained`, and two SEC evidence items.
- `catalyst_edge_claim_sources` was discoverable but not called: it requires a real
  `claim_id`, and both returned items had `claim_id=null`. No identifier was fabricated.
- All 45 installed member bytes matched the exact self-signed archive.
- The materialized evidence store retained its exact SHA-256, sentinel, 11 tables, and
  `ok` integrity result across uninstall of the unsigned fallback, self-signed install,
  configuration, and invocation.
- Existing Claude extensions were left unchanged; Catalyst Edge is left installed and
  enabled for QA.

## Fixed SEC-only sample

The runner generated five separate schema-valid dossiers outside the repository at
`/tmp/catalyst-edge-sec-samples.ZNn2oh`. The path is ephemeral QA evidence and is not a
publication source.

| Ticker | Coverage | Method | Model | Evidence |
| --- | --- | --- | --- | ---: |
| AAPL | partial | deterministic_v1 | not_trained | 2 |
| NVDA | none | deterministic_v1 | not_trained | 0 |
| TSLA | partial | deterministic_v1 | not_trained | 2 |
| RKLB | none | deterministic_v1 | not_trained | 0 |
| BRK.B | none | deterministic_v1 | not_trained | 0 |

The five dossier files contain no personal identity, local path, or enabled non-SEC
provider marker. The sample manifest SHA-256 is
`830baa1b4ba9a3f434fe84e80b44cef94509fc74dc9b82b04f9168835bcc4919`.
No available grouped claim existed, so claim-pagination proof remains open. A public
60-90 second example also remains subject to human review.

## Gate boundary

- R0/R3: the rebased scope/configuration contracts and full local suite pass.
- R1: unsigned reproducibility and a clean preparatory commit pass; matching tag and
  compatible production signing remain open.
- R2: local Python 3.10/3.14, lint, npm audit, MCPB, and inventory checks pass; fresh PR CI
  remains required.
- R4: Codex and Claude invocation pass against the prior exact self-signed QA member bytes;
  the rebased candidate still needs production-trusted exact-byte client proof.
- R5: five fixed calls and typed missingness pass; the explicit no-claim boundary remains,
  and the visual launch-example package still requires Ryan's human approval.
- R6: extension/config rollback and exact SQLite hash/sentinel preservation pass for the
  prior unsigned-to-self-signed QA reinstall path; repeat against the final signed bytes.
- R7: publication authority remains open and blocks every public action.

## Post-merge signing investigation

The rebased unsigned candidate is deterministic at SHA-256
`6d7424f73ea34082f22736e7c5446df7b756cb53f2e0fec1076e8b056365f3b0` with 47 allowed
members. The earlier 45-member exact-byte client proof remains historical QA evidence; the
rebased bytes require a new production-signed client and rollback run before release.

The released MCPB CLI `2.1.2` is still the latest published version and still appends a
detached CMS block without updating the ZIP end-of-central-directory comment length.
Upstream merged [modelcontextprotocol/mcpb#204](https://github.com/modelcontextprotocol/mcpb/pull/204)
to address the strict-ZIP error, but that implementation changes the stored ZIP bytes
after computing the signature. Upstream
[issue #260](https://github.com/modelcontextprotocol/mcpb/issues/260) and open
[PR #255](https://github.com/modelcontextprotocol/mcpb/pull/255) confirm the resulting
digest mismatch and the separate unimplemented `node-forge` verification path. Claude
Desktop ships the same fail-closed verifier and cannot surface a publisher as trusted.

`scripts/sign_mcpb.py` now provides a narrow two-pass compatibility path: determine the
CMS block length, write that length into the unsigned ZIP before signing, sign those
exact bytes, append the declared ZIP comment, and independently verify CMS recovery of
the exact content. A temporary code-signing-EKU self-signed QA certificate produced:

- signed QA SHA-256
  `89633f4a3cd33e29c7619699fb6efd715f93e842b9ce7c88027b16c5a4da1797`;
- 1,375-byte signature block matching the ZIP comment length;
- passing independent OpenSSL CMS verification and ZIP member validation; and
- successful Claude Desktop `1.24012.9` preview with exactly the two public tools and
  all runtime requirements met.

Claude still displayed the developer as unverified, and MCPB CLI `info` still reported
`WARNING: Not signed`, as expected from the upstream verifier defect. The QA private key
was destroyed after artifact creation. The signed QA bytes were then installed, configured,
enabled, and invoked only after explicit action-time confirmation. No production
certificate, trusted-client readback, release-signed artifact, or distribution proof
exists; production signing therefore remains fail-closed.

## Post-merge exact-byte client and rollback proof

The configured isolated Claude QA path
`/tmp/catalyst-edge-claude-qa.d4cBgb/evidence.sqlite3` is now materialized through the
installed package's `EvidenceStore` with all 11 application tables. It also contains the
sentinel `preserve-through-mcpb-reinstall-2026-08-03`; SQLite integrity check returns
`ok`, and the closed database SHA-256 before reinstall is
`6f42710a2ae2449dcb088ca3cdd9062279338a025b34c87da54f09c44d796b2a`.

Claude uninstalled the prior unsigned fallback, installed the exact self-signed QA
artifact, and saved the same SEC-only configuration through its Configure UI. Restoring
the configuration file on disk alone did not update the already-running client: the
first new chat correctly reported the tool unavailable and made no call. Saving through
the UI resolved that client-state boundary. A fresh Claude chat then invoked
`catalyst_edge_score` exactly once for AAPL and returned partial coverage,
`deterministic_v1`, `not_trained`, two SEC evidence items, and two null `claim_id` values.
All 45 installed member bytes matched the signed archive.

Codex CLI `0.144.1` used an isolated home and the same 45 extracted archive members.
Its first approved call failed without returning an error body, so the cause remains
unknown. A retry naming the tool's exact `ticker` field invoked `catalyst_edge_score`
exactly once and returned the same coverage, method, model status, evidence count, and
null-claim count. The per-server approval setting was scoped to the isolated QA home;
the copied Codex auth and MCP configuration were securely destroyed afterward.

After uninstall, reinstall, configuration, and both successful client calls, the closed
SQLite file still had SHA-256
`6f42710a2ae2449dcb088ca3cdd9062279338a025b34c87da54f09c44d796b2a`, retained the
sentinel, and returned `ok` from `PRAGMA integrity_check`. R6 therefore passes for this
QA path. It does not prove production signing trust or distribution rollback.
