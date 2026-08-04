const crypto = require("node:crypto");
const {
  OFFER_VERSION,
  botReason,
  createJson,
  encryptEmail,
  exists,
  hmac,
  ipRateKey,
  json,
  readJson,
  remove,
  sendConfirmation,
  staffReason,
  tokenHash,
  validateIntent,
} = require("./_lib");

module.exports = async (req, res) => {
  if (req.method !== "POST") return json(res, 405, { error: "Method not allowed" });
  if (Number(req.headers["content-length"] || 0) > 5000) return json(res, 413, { error: "Request too large" });

  try {
    const input = validateIntent(req.body);
    const exclusion = botReason(req, input);
    if (exclusion === "bot" || exclusion === "honeypot") return json(res, 202, { ok: true });

    const minute = Math.floor(Date.now() / 60000);
    const allowed = await createJson(`measure/${OFFER_VERSION}/rate/${minute}/${ipRateKey(req, "intent")}.json`, { at: Date.now() });
    if (!allowed) return json(res, 429, { error: "Please wait a minute and try again" });

    const emailHash = hmac(input.email);
    const base = `measure/${OFFER_VERSION}/intent`;
    const confirmed = await Promise.all([
      exists(`${base}/confirmed/linked/${emailHash}.json`),
      exists(`${base}/confirmed/unlinked/${emailHash}.json`),
      exists(`${base}/excluded/${emailHash}.json`),
    ]);
    if (confirmed.some(Boolean)) return json(res, 200, { ok: true, alreadyConfirmed: true });

    const visitorHash = hmac(input.visitorId);
    const activation = await readJson(`measure/${OFFER_VERSION}/events/activation_report/${visitorHash}.json`);
    const token = crypto.randomBytes(32).toString("base64url");
    const pendingKey = `${base}/pending/${tokenHash(token)}.json`;
    const record = {
      offerVersion: OFFER_VERSION,
      emailHash,
      emailCiphertext: encryptEmail(input.email),
      client: input.client,
      source: input.source,
      visitorHash,
      activationLinkedAt: activation?.at || null,
      excludedReason: exclusion || staffReason(emailHash),
      createdAt: new Date().toISOString(),
    };

    await createJson(pendingKey, record);
    try {
      await sendConfirmation(input.email, token);
    } catch (error) {
      await remove(pendingKey);
      throw error;
    }
    return json(res, 202, { ok: true });
  } catch (error) {
    const publicMessage = /^Enter|^Choose|^Confirm|^Offer|^Invalid/.test(error.message)
      ? error.message
      : "Signup is temporarily unavailable";
    return json(res, publicMessage === error.message ? 400 : 503, { error: publicMessage });
  }
};
