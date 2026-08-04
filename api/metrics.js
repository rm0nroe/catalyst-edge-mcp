const {
  OFFER_VERSION,
  json,
  listAll,
  safeEqual,
  wilsonLowerBound,
} = require("./_lib");

module.exports = async (req, res) => {
  if (req.method !== "GET") return json(res, 405, { error: "Method not allowed" });
  const supplied = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  if (!process.env.METRICS_TOKEN || !safeEqual(supplied, process.env.METRICS_TOKEN)) {
    return json(res, 401, { error: "Unauthorized" });
  }
  try {
    const base = `measure/${OFFER_VERSION}`;
    const [exposures, installs, activations, verified, linked] = await Promise.all([
      listAll(`${base}/events/offer_exposure/`),
      listAll(`${base}/events/install_click/`),
      listAll(`${base}/events/activation_report/`),
      listAll(`${base}/intent/confirmed/`),
      listAll(`${base}/intent/confirmed/linked/`),
    ]);
    const lowerBound = wilsonLowerBound(verified.length, exposures.length);
    return json(res, 200, {
      offerVersion: OFFER_VERSION,
      observedSince: process.env.MEASUREMENT_STARTED_AT || null,
      recentWindowDays: 180,
      uniqueQualifiedExposures: exposures.length,
      installClicks: installs.length,
      successfulInstallReports: activations.length,
      verifiedPriceAwareIntent: verified.length,
      activationLinkedVerifiedIntent: linked.length,
      rawVerifiedIntentRate: exposures.length ? verified.length / exposures.length : 0,
      oneSided95WilsonLowerBound: lowerBound,
      decisionReady: exposures.length >= 250,
      thresholds: { compatibilitySpike: 350, scopedReview: 1350, fullBuildReconsideration: 11100 },
    });
  } catch {
    return json(res, 503, { error: "Metrics are temporarily unavailable" });
  }
};
