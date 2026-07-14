"""Finnhub social-sentiment and optional lobbying adapters."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import httpx

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.adapters.fmp import _datetime, _number, _url
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import AdapterResult, Change, Direction, Evidence, Source
from catalyst_edge_mcp.redaction import bounded_raw

FINNHUB_BASE = "https://finnhub.io/api/v1"
FINNHUB_QUALITY = 0.80
FINNHUB_GATE = ProviderGate(concurrency=1, requests_per_second=1)


class _FinnhubAdapter:
    provider = "finnhub"

    def __init__(
        self, api_key: str, *, client: httpx.AsyncClient | None = None, clock=None
    ) -> None:
        if not api_key:
            raise ValueError("FINNHUB_API_KEY is required")
        self.api_key = api_key
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    def _now(self) -> datetime:
        value = self._clock()
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        headers = {"X-Finnhub-Token": self.api_key}
        async with FINNHUB_GATE.request():
            if self._client is not None:
                response = await self._client.get(
                    f"{FINNHUB_BASE}{path}", params=params, headers=headers
                )
            else:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    response = await client.get(
                        f"{FINNHUB_BASE}{path}", params=params, headers=headers
                    )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected Finnhub provider schema")
        return payload


class FinnhubSocialAdapter(_FinnhubAdapter):
    family = "social"

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        payload = await self._get("/stock/social-sentiment", {"symbol": ticker})
        rows: list[dict[str, Any]] = []
        for channel in ("reddit", "twitter"):
            channel_rows = payload.get(channel, [])
            if not isinstance(channel_rows, list):
                raise ValueError("Unexpected Finnhub social schema")
            for row in channel_rows:
                if not isinstance(row, dict):
                    raise ValueError("Unexpected Finnhub social row schema")
                rows.append({**row, "channel": channel})

        now = self._now()
        half = max(1, lookback_days / 2)
        current_cutoff = now - timedelta(days=half)
        prior_cutoff = now - timedelta(days=half * 2)
        buckets = {
            "current": {"mentions": 0.0, "weighted": 0.0},
            "prior": {"mentions": 0.0, "weighted": 0.0},
        }
        newest: datetime | None = None
        accepted: list[dict[str, Any]] = []
        current_rows: list[dict[str, Any]] = []
        for row in rows:
            timestamp = _datetime(row.get("atTime") or row.get("date"))
            if timestamp is None or timestamp < prior_cutoff:
                continue
            window = "current" if timestamp >= current_cutoff else "prior"
            mentions = _number(row.get("mention"))
            positive = _number(row.get("positiveMention")) or 0.0
            negative = _number(row.get("negativeMention")) or 0.0
            if mentions is None:
                mentions = positive + negative
            mentions = max(0.0, mentions)
            if mentions <= 0:
                continue
            score = _number(row.get("score"))
            if score is None:
                score = (positive - negative) / max(1.0, positive + negative)
            score = max(-1.0, min(1.0, score))
            buckets[window]["mentions"] += mentions
            buckets[window]["weighted"] += score * mentions
            newest = max(newest or timestamp, timestamp)
            accepted.append(row)
            if window == "current":
                current_rows.append(row)

        current_mentions = buckets["current"]["mentions"]
        prior_mentions = buckets["prior"]["mentions"]
        if current_mentions <= 0:
            return self._result([], ["No recent Finnhub social observations were available."])
        current_sentiment = buckets["current"]["weighted"] / max(1.0, current_mentions)
        has_baseline = prior_mentions > 0
        prior_sentiment = (
            buckets["prior"]["weighted"] / prior_mentions if has_baseline else None
        )
        non_decreasing = has_baseline and current_mentions >= prior_mentions
        sentiment_delta = (
            current_sentiment - prior_sentiment if prior_sentiment is not None else 0.0
        )
        direction = Direction.NEUTRAL
        if non_decreasing and sentiment_delta >= 0.05:
            direction = Direction.BULLISH
        elif non_decreasing and sentiment_delta <= -0.05:
            direction = Direction.BEARISH
        signal = (
            "social_current_observation"
            if not has_baseline
            else "social_sentiment_increase"
            if direction == Direction.BULLISH
            else "social_sentiment_decrease"
            if direction == Direction.BEARISH
            else "social_attention_change"
        )
        timestamp = newest or now
        source_url = next(
            (
                _url(row.get("url") or row.get("link"))
                for row in current_rows
                if _url(row.get("url") or row.get("link"))
            ),
            None,
        )
        evidence = Evidence(
            family=self.family,
            signal=signal,
            direction=direction,
            strength=min(1.0, 0.35 + abs(sentiment_delta)),
            confidence=0.72 if direction != Direction.NEUTRAL else 0.60,
            source_quality=FINNHUB_QUALITY,
            timestamp=timestamp,
            change=(
                Change(
                    description=(
                        f"Social mentions changed from {prior_mentions:.0f} "
                        f"to {current_mentions:.0f}; sentiment changed by "
                        f"{sentiment_delta:+.3f}."
                    ),
                    current_value=current_mentions,
                    baseline_value=prior_mentions,
                    delta=current_mentions - prior_mentions,
                    unit="mentions",
                    comparison_window="current half vs preceding equal window",
                )
                if has_baseline
                else None
            ),
            sources=[
                Source(
                    name="Finnhub social sentiment",
                    url=source_url,
                    observed_at=timestamp,
                )
            ],
            raw_signal=bounded_raw(accepted),
        )
        warnings = [] if has_baseline else ["social baseline_unavailable for the prior window."]
        return self._result([evidence], warnings)

    def _result(self, evidence: list[Evidence], warnings: list[str]) -> AdapterResult:
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=warnings,
            collected_at=self._now(),
        )


class FinnhubLobbyingAdapter(FinnhubSocialAdapter):
    family = "alternative"

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        now = self._now()
        start = (now - timedelta(days=lookback_days)).date().isoformat()
        payload = await self._get(
            "/stock/lobbying",
            {"symbol": ticker, "from": start, "to": now.date().isoformat()},
        )
        rows = payload.get("data", [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Unexpected Finnhub lobbying schema")
        half = max(1, lookback_days / 2)
        current_cutoff = now - timedelta(days=half)
        prior_cutoff = now - timedelta(days=half * 2)
        current_rows, prior_rows = [], []
        for row in rows:
            row_date = _datetime(row.get("date") or row.get("filingDate"))
            if row_date is None or row_date < prior_cutoff:
                continue
            (current_rows if row_date >= current_cutoff else prior_rows).append(row)
        if not current_rows:
            return self._result([], ["No recent Finnhub lobbying observations were available."])
        has_baseline = bool(prior_rows)
        newest = (
            max(
                (_datetime(row.get("date") or row.get("filingDate")) for row in current_rows),
                default=now,
            )
            or now
        )
        first_url = next(
            (
                _url(row.get("url") or row.get("link"))
                for row in current_rows
                if _url(row.get("url") or row.get("link"))
            ),
            None,
        )
        evidence = Evidence(
            family=self.family,
            signal=(
                "lobbying_activity_change"
                if has_baseline
                else "lobbying_activity_observation"
            ),
            direction=Direction.NEUTRAL,
            strength=min(1.0, 0.35 + len(current_rows) / 20),
            confidence=0.70,
            source_quality=FINNHUB_QUALITY,
            timestamp=newest,
            change=(
                Change(
                    description=(
                        f"Lobbying activity count changed from {len(prior_rows)} "
                        f"to {len(current_rows)}."
                    ),
                    current_value=float(len(current_rows)),
                    baseline_value=float(len(prior_rows)),
                    delta=float(len(current_rows) - len(prior_rows)),
                    unit="filings or activities",
                    comparison_window="current half vs preceding equal window",
                )
                if has_baseline
                else None
            ),
            sources=[Source(name="Finnhub lobbying", url=first_url, observed_at=newest)],
            notes="Lobbying remains neutral without an explicit provider-supported direction.",
            raw_signal=bounded_raw(current_rows),
        )
        warnings = (
            []
            if has_baseline
            else ["alternative baseline_unavailable for lobbying activity."]
        )
        return self._result([evidence], warnings)
