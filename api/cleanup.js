const { OFFER_VERSION, listAll, json, remove, safeEqual } = require("./_lib");

module.exports = async (req, res) => {
  const supplied = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  if (!process.env.CRON_SECRET || !safeEqual(supplied, process.env.CRON_SECRET)) {
    return json(res, 401, { error: "Unauthorized" });
  }
  try {
    const blobs = await listAll(`measure/${OFFER_VERSION}/`);
    const now = Date.now();
    const expired = blobs.filter((blob) => {
      const age = now - new Date(blob.uploadedAt).getTime();
      if (blob.pathname.includes("/pending/")) return age > 24 * 60 * 60 * 1000;
      if (blob.pathname.includes("/rate/")) return age > 2 * 24 * 60 * 60 * 1000;
      return age > 180 * 24 * 60 * 60 * 1000;
    });
    await Promise.all(expired.map((blob) => remove(blob.pathname)));
    return json(res, 200, { ok: true, removed: expired.length });
  } catch {
    return json(res, 503, { error: "Cleanup is temporarily unavailable" });
  }
};
