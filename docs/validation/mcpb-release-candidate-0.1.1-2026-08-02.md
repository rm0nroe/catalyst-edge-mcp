# Catalyst Edge MCPB Release Candidate 0.1.1

**Status:** Private preparatory evidence only. No repository visibility change, tag,
release, package upload, registry submission, landing-page change, or customer delivery
is authorized or represented by this record.

## Candidate provenance

- Base: `origin/main` at `3f34420ab8909ee4db7b7f6dd3d73077ccbf3a7e`.
- Branch: `codex/mcpb-release-prep` in an isolated worktree.
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
- current SHA-256 after documentation updates:
  `74ad4867e81e816f9a3d14fc30632351d809b2675769b9ecd5d34d90283e7b88`;
- allowed members: 45;
- ZIP order: lexical;
- ZIP timestamps: `1980-01-01T00:00:00`;
- prohibited credentials, `.env`, state, caches, tests, scripts, docs, and build output:
  absent.

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

- Codex CLI `0.144.1` ran with an isolated home and `--ignore-user-config`; persistent
  user configuration was not changed.
- A clean Python 3.14 wheel install exposed exactly the two public tools.
- With documented one-run environment forwarding and tool approval set to `approve`, an
  AAPL call returned `coverage=partial`, `scoring_method=deterministic_v1`,
  `model_status=not_trained`, two SEC evidence items, and explicit missing-data and
  non-advisory warnings.

### Claude Desktop

- The current byte-exact unsigned candidate SHA-256
  `74ad4867e81e816f9a3d14fc30632351d809b2675769b9ecd5d34d90283e7b88`
  was installed after documentation stabilized. Its final AAPL call completed with
  `as_of=2026-08-03T03:20:53.604523Z`, partial coverage, deterministic v1 scoring,
  `not_trained`, and two SEC evidence items.
- Preview displayed exactly the two public tools and all runtime requirements met.
- Unsigned fallback installation plus SEC-only configuration completed in 44 seconds.
- First complete tool readback completed 160 seconds after install began, including the
  interactive one-time approval.
- AAPL returned partial coverage, deterministic v1 scoring, `not_trained`, and two SEC
  evidence items.
- `catalyst_edge_claim_sources` was discoverable but not called: it requires a real
  `claim_id`, and both returned items had `claim_id=null`. No identifier was fabricated.
- Uninstall completed in 7 seconds. Reinstall and reconfiguration completed in 37
  seconds. A fresh post-reinstall AAPL call returned the same score/evidence with an
  advanced retrieval timestamp.
- The isolated evidence-store path was never materialized, so file-preservation across
  uninstall was not demonstrated.
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

- R0/R3: recheck with the final diff.
- R1: unsigned reproducibility passes; clean commit/tag and compatible production
  signing remain open.
- R2: local and PR CI for this diff remain required.
- R4: Codex and unsigned Claude QA pass; signed Claude installation is blocked.
- R5: five fixed calls and typed missingness pass; pagination/example review remain open.
- R6: extension/config rollback passes; evidence-store preservation remains unproved.
- R7: publication authority remains open and blocks every public action.
