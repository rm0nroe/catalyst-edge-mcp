const {
  OFFER_VERSION,
  botReason,
  cleanText,
  createJson,
  exists,
  hmac,
  json,
  move,
  readJson,
  validateVisitor,
} = require("./_lib");

const EVENTS = new Set(["offer_exposure", "install_click", "activation_report"]);

module.exports = async (req, res) => {
  if (req.method !== "POST") return json(res, 405, { error: "Method not allowed" });
  try {
    const body = req.body || {};
    if (body.offerVersion !== OFFER_VERSION || !EVENTS.has(body.event)) throw new Error("Invalid event");
    const visitorId = validateVisitor(body.visitorId);
    if (botReason(req, { qa: body.qa === true, honeypot: body.company })) return json(res, 202, { ok: true, excluded: true });
    const source = cleanText(body.source);
    const visitorHash = hmac(visitorId);
    const uniqueKey = `measure/${OFFER_VERSION}/events/${body.event}/${visitorHash}.json`;
    const first = await createJson(uniqueKey, { source, at: new Date().toISOString() });
    if (!first) return json(res, 200, { ok: true, duplicate: true });

    if (body.event === "activation_report") {
      const base = `measure/${OFFER_VERSION}/intent`;
      const mapping = await readJson(`${base}/visitor/${visitorHash}.json`);
      if (mapping?.emailHash) {
        const from = `${base}/confirmed/unlinked/${mapping.emailHash}.json`;
        const to = `${base}/confirmed/linked/${mapping.emailHash}.json`;
        if (await exists(from)) {
          await move(from, to);
        }
      }
    }
    return json(res, 202, { ok: true });
  } catch {
    return json(res, 400, { error: "Invalid event" });
  }
};
