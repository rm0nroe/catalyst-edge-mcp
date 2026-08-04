const crypto = require("node:crypto");
const { del, get, head, list, put, rename } = require("@vercel/blob");

const OFFER_VERSION = "hosted-pro-29-v1-2026-08-04";
const RECENT_SECONDS = 180 * 24 * 60 * 60;
const CLIENTS = new Set(["claude", "codex", "cursor", "other"]);

function json(res, status, value) {
  res.status(status).setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(value));
}

function env(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing ${name}`);
  return value;
}

async function exists(pathname) {
  try {
    await head(pathname);
    return true;
  } catch {
    return false;
  }
}

async function createJson(pathname, value) {
  try {
    await put(pathname, JSON.stringify(value), {
      access: "private",
      addRandomSuffix: false,
      contentType: "application/json",
      cacheControlMaxAge: 60,
    });
    return true;
  } catch (error) {
    if (await exists(pathname)) return false;
    throw error;
  }
}

async function readJson(pathname) {
  const result = await get(pathname, { access: "private", useCache: false });
  if (!result || result.statusCode !== 200) return null;
  return JSON.parse(await new Response(result.stream).text());
}

async function listAll(prefix) {
  const blobs = [];
  let cursor;
  do {
    const page = await list({ prefix, cursor, limit: 1000 });
    blobs.push(...page.blobs);
    cursor = page.hasMore ? page.cursor : undefined;
  } while (cursor);
  return blobs;
}

async function remove(pathname) {
  await del(pathname);
}

async function move(from, to) {
  await rename(from, to, { access: "private", addRandomSuffix: false });
}

function hmac(value, secret = env("INTENT_HASH_SECRET")) {
  return crypto.createHmac("sha256", secret).update(value).digest("hex");
}

function tokenHash(token) {
  return crypto.createHash("sha256").update(token).digest("hex");
}

function normalizeEmail(value) {
  const email = String(value || "").trim().toLowerCase();
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    throw new Error("Enter a valid email address");
  }
  return email;
}

function encryptEmail(email) {
  const key = crypto.createHash("sha256").update(env("PII_ENCRYPTION_KEY")).digest();
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  const encrypted = Buffer.concat([cipher.update(email, "utf8"), cipher.final()]);
  return [iv, cipher.getAuthTag(), encrypted].map((part) => part.toString("base64url")).join(".");
}

function decryptEmail(value) {
  const [iv, tag, encrypted] = value.split(".").map((part) => Buffer.from(part, "base64url"));
  const key = crypto.createHash("sha256").update(env("PII_ENCRYPTION_KEY")).digest();
  const decipher = crypto.createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(encrypted), decipher.final()]).toString("utf8");
}

function cleanText(value, max = 64) {
  const text = String(value || "direct").trim().slice(0, max);
  return /^[a-zA-Z0-9._:/?&=-]+$/.test(text) ? text : "other";
}

function validateVisitor(value) {
  const visitorId = String(value || "");
  if (!/^[a-f0-9-]{16,64}$/i.test(visitorId)) throw new Error("Invalid visitor ID");
  return visitorId;
}

function validateIntent(body) {
  if (!body || typeof body !== "object") throw new Error("Invalid request");
  if (body.offerVersion !== OFFER_VERSION) throw new Error("Offer version changed; reload the page");
  if (!CLIENTS.has(body.client)) throw new Error("Choose an MCP client");
  if (body.definitelyPay !== true) throw new Error("Confirm the exact $29/month offer");
  if (body.privacyConsent !== true) throw new Error("Confirm the privacy notice");
  return {
    email: normalizeEmail(body.email),
    client: body.client,
    visitorId: validateVisitor(body.visitorId),
    source: cleanText(body.source),
    qa: body.qa === true,
    honeypot: String(body.company || ""),
  };
}

function botReason(req, input = {}) {
  if (input.honeypot) return "honeypot";
  if (/bot|crawler|spider|headless|preview/i.test(String(req.headers["user-agent"] || ""))) return "bot";
  if (input.qa) return "qa";
  return null;
}

function staffReason(emailHash) {
  const staff = String(process.env.STAFF_EMAIL_HASHES || "").split(",").map((v) => v.trim()).filter(Boolean);
  return staff.includes(emailHash) ? "staff" : null;
}

function ipRateKey(req, scope) {
  const ip = String(req.headers["x-forwarded-for"] || req.socket?.remoteAddress || "unknown").split(",")[0].trim();
  return `rate:${scope}:${hmac(ip)}`;
}

function publicUrl() {
  const value = process.env.PUBLIC_SITE_URL || (process.env.VERCEL_URL ? `https://${process.env.VERCEL_URL}` : "");
  if (!value) throw new Error("Missing PUBLIC_SITE_URL");
  return value.replace(/\/$/, "");
}

async function sendConfirmation(email, token) {
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env("RESEND_API_KEY")}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env("INTENT_FROM_EMAIL"),
      to: [email],
      subject: "Confirm your Catalyst Edge Hosted Pro interest",
      text: `Confirm that you would definitely pay $29/month for zero-install hosted access and managed updates:\n\n${publicUrl()}/confirm?token=${encodeURIComponent(token)}\n\nThis is a price-aware interest test, not a purchase or product account. The link expires in 24 hours.`,
    }),
  });
  if (!response.ok) throw new Error(`Email provider ${response.status}`);
}

function safeEqual(left, right) {
  const a = Buffer.from(String(left || ""));
  const b = Buffer.from(String(right || ""));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function wilsonLowerBound(successes, total) {
  if (!total) return 0;
  const z = 1.6448536269514722;
  const p = successes / total;
  const denominator = 1 + (z * z) / total;
  const center = p + (z * z) / (2 * total);
  const margin = z * Math.sqrt((p * (1 - p) + (z * z) / (4 * total)) / total);
  return Math.max(0, (center - margin) / denominator);
}

module.exports = {
  OFFER_VERSION,
  RECENT_SECONDS,
  botReason,
  cleanText,
  createJson,
  decryptEmail,
  encryptEmail,
  env,
  exists,
  hmac,
  ipRateKey,
  json,
  listAll,
  move,
  publicUrl,
  readJson,
  remove,
  safeEqual,
  sendConfirmation,
  staffReason,
  tokenHash,
  validateIntent,
  validateVisitor,
  wilsonLowerBound,
};
