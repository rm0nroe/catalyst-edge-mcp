const { json, listAll } = require("./_lib");

module.exports = async (req, res) => {
  if (req.method !== "GET") return json(res, 405, { error: "Method not allowed" });
  try {
    await listAll("health/");
    const configured = Boolean(process.env.RESEND_API_KEY && process.env.INTENT_FROM_EMAIL && (process.env.PUBLIC_SITE_URL || process.env.VERCEL_URL));
    return json(res, configured ? 200 : 503, { ok: configured });
  } catch {
    return json(res, 503, { ok: false });
  }
};
