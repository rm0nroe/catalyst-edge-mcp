const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

process.env.INTENT_HASH_SECRET = "test-hash-secret";
process.env.PII_ENCRYPTION_KEY = "test-encryption-secret";
const { decryptEmail, encryptEmail, validateIntent, wilsonLowerBound } = require("../api/_lib");

test("intent validation, private email storage, and decision bound", () => {
  const input = validateIntent({
    email: "Builder@Example.com",
    client: "codex",
    definitelyPay: true,
    privacyConsent: true,
    offerVersion: "hosted-pro-29-v1-2026-08-04-live",
    visitorId: "019fceaa-b7a2-7490-bac8-1f0325762477",
    source: "github",
  });
  assert.equal(input.email, "builder@example.com");
  const ciphertext = encryptEmail(input.email);
  assert.equal(ciphertext.includes(input.email), false);
  assert.equal(decryptEmail(ciphertext), input.email);
  assert.ok(Math.abs(wilsonLowerBound(12, 250) - 0.0302) < 0.0002);
});

test("public site has safe install, discovery, sharing, and privacy paths", () => {
  const root = path.join(__dirname, "..");
  const index = fs.readFileSync(path.join(root, "site/index.html"), "utf8");
  const app = fs.readFileSync(path.join(root, "site/app.js"), "utf8");
  const privacy = fs.readFileSync(path.join(root, "site/privacy.html"), "utf8");

  assert.match(index, /rel="canonical"/);
  assert.match(index, /Official MCP Registry/);
  assert.match(index, /pypi\.org\/project\/catalyst-edge-mcp/);
  assert.match(index, /data-copy="codex-command" disabled/);
  assert.doesNotMatch(index, /ops@example\.com/);
  assert.doesNotMatch(index, />Watch the 90-second example</);
  assert.match(app, /secEmail\.checkValidity\(\)/);
  assert.match(privacy, /Request earlier deletion/);
});
