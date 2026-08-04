const {
  OFFER_VERSION,
  createJson,
  exists,
  json,
  readJson,
  remove,
  tokenHash,
} = require("./_lib");

module.exports = async (req, res) => {
  if (req.method !== "GET") return json(res, 405, { error: "Method not allowed" });
  const token = String(req.query?.token || "");
  if (!/^[a-zA-Z0-9_-]{40,60}$/.test(token)) return json(res, 400, { error: "Invalid confirmation link" });

  try {
    const base = `measure/${OFFER_VERSION}/intent`;
    const pendingKey = `${base}/pending/${tokenHash(token)}.json`;
    const pending = await readJson(pendingKey);
    if (!pending) return json(res, 410, { error: "This confirmation link expired or was already used" });
    const record = pending;
    if (record.offerVersion !== OFFER_VERSION) return json(res, 409, { error: "This offer is no longer current" });

    const confirmedRecord = { ...record, confirmedAt: new Date().toISOString() };
    const paths = [
      `${base}/confirmed/linked/${record.emailHash}.json`,
      `${base}/confirmed/unlinked/${record.emailHash}.json`,
      `${base}/excluded/${record.emailHash}.json`,
    ];
    const duplicate = (await Promise.all(paths.map(exists))).some(Boolean);
    const confirmedKey = record.excludedReason
      ? paths[2]
      : record.activationLinkedAt ? paths[0] : paths[1];
    const inserted = duplicate ? false : await createJson(confirmedKey, confirmedRecord);
    if (inserted) {
      await createJson(`${base}/visitor/${record.visitorHash}.json`, { emailHash: record.emailHash });
    }
    await remove(pendingKey);
    return json(res, 200, { ok: true, alreadyConfirmed: !inserted });
  } catch {
    return json(res, 503, { error: "Confirmation is temporarily unavailable" });
  }
};
