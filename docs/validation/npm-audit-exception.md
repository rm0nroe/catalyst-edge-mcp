# Temporary npm audit exception

Reviewed 2026-10-06. Expires 2026-11-06 (the gate fails on that date).

Only [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv)
is accepted, for `node-forge@1.4.0` through `@anthropic-ai/mcpb@2.1.2`.
Both were the latest published versions at review; no patched release was available.
This does not assert that node-forge is fixed or safe for signature verification.

## Reachability

- `.github/workflows/validation.yml` invokes `mcpb validate` and `mcpb pack`.
- MCPB 2.1.2 `dist/cli/cli.js` routes those commands to `validateManifest`
  and `packExtension`. The former reads JSON, validates schemas and checks icon
  bytes. The latter collects files and creates a ZIP with `fflate.zipSync`.
- The CLI imports `dist/node/sign.js`, but neither command calls its
  `verifyMcpbFile` function or node-forge RSA verification.
- `scripts/verify_mcpb.py` validates source pins, archive inventory, timestamps
  and hashes through Python's standard library. It does not verify signatures.
- `npm run mcpb:sign` uses `scripts/sign_mcpb.py`, which signs and verifies CMS
  using OpenSSL. Its existing test rejects tampered signed content.
- `.mcpbignore` excludes `node_modules`; the bundle verifier enforces that
  exclusion. The Python wheel does not include Node dependencies either.

## Validation evidence

The reviewed validate and pack commands passed with a Node preload that exits
86 on any access to `forge.pkcs7`, `forge.pki` or `forge.rsa`. A negative control
accessing `forge.pkcs7` exited 86. Bundle verification also passed. This confirms
those commands did not use the crypto APIs on the reviewed source and manifest.
The offline signing test separately verifies OpenSSL rejects tampered content.

## Enforcement and removal

`scripts/audit_npm.py` still runs a full npm audit at the low severity threshold.
It accepts only the exact advisory and its MCPB parent finding, exact installed
lockfile versions and paths, and no available fix. Other findings, changed
paths/versions, errors, unsupported reports and expiration fail the gate.
The raw audit report remains visible in CI. Branch protection is unchanged.

Remove the exception and restore plain `npm audit --audit-level=low` when an
upstream fix is available. Reassess before changing MCPB commands or adding any
node-forge consumer. Do not use MCPB's `sign`, `verify` or `info` commands under
this assessment; imported code alone does not establish runtime exposure.
