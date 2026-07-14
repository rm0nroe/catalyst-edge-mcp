"""Financial Modeling Prep news, insider, and technical adapters."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

import httpx

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import AdapterResult, Change, Direction, Evidence, Source
from catalyst_edge_mcp.redaction import bounded_raw

FMP_BASE = "https://financialmodelingprep.com"
FMP_QUALITY = 0.85
FMP_GATE = ProviderGate(concurrency=2, requests_per_second=5)


def _datetime(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _url(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if text.startswith(("https://", "http://")) else None


class _FmpAdapter:
    provider = "fmp"

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        clock=None,
    ) -> None:
        if not api_key:
            raise ValueError("FMP_API_KEY is required")
        self.api_key = api_key
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        headers = {"apikey": self.api_key}
        async with FMP_GATE.request():
            if self._client is not None:
                response = await self._client.get(
                    f"{FMP_BASE}{path}", params=params, headers=headers
                )
            else:
                async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                    response = await client.get(
                        f"{FMP_BASE}{path}", params=params, headers=headers
                    )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, (list, dict)):
            raise ValueError("Unexpected FMP provider schema")
        return payload


class FmpNewsAdapter(_FmpAdapter):
    family = "filings_news"

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        payload = await self._get(
            "/stable/news/stock",
            {"symbols": ticker, "page": 0, "limit": 100},
        )
        if not isinstance(payload, list):
            raise ValueError("Unexpected FMP news schema")
        cutoff = self._clock_utc() - timedelta(days=lookback_days)
        evidence: list[Evidence] = []
        for row in payload:
            if not isinstance(row, dict):
                raise ValueError("Unexpected FMP news row schema")
            timestamp = _datetime(row.get("publishedDate"))
            title = str(row.get("title") or "").strip()
            if timestamp is None or timestamp < cutoff or not title:
                continue
            evidence.append(
                Evidence(
                    family=self.family,
                    signal="company_news_event",
                    direction=Direction.NEUTRAL,
                    strength=0.45,
                    confidence=0.75,
                    source_quality=FMP_QUALITY,
                    timestamp=timestamp,
                    change=Change(description=f"New company coverage: {title}"[:240]),
                    sources=[
                        Source(
                            name=str(row.get("site") or "FMP news"),
                            url=_url(row.get("url")),
                            observed_at=timestamp,
                        )
                    ],
                    notes="Direction remains neutral because headlines are not keyword-scored.",
                    raw_signal=bounded_raw(row),
                )
            )
        return self._result(evidence, "No recent FMP company news was available.")

    def _clock_utc(self) -> datetime:
        value = self._clock()
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    def _result(self, evidence: list[Evidence], empty_warning: str) -> AdapterResult:
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=[] if evidence else [empty_warning],
            collected_at=self._clock_utc(),
        )


class FmpInsiderAdapter(FmpNewsAdapter):
    family = "insider_trading"

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        payload = await self._get(
            "/stable/insider-trading/search",
            {"symbol": ticker, "page": 0, "limit": 100},
        )
        if not isinstance(payload, list):
            raise ValueError("Unexpected FMP insider schema")
        now = self._clock_utc()
        half_days = max(1, lookback_days / 2)
        current_cutoff = now - timedelta(days=half_days)
        prior_cutoff = now - timedelta(days=half_days * 2)
        metrics: dict[str, dict[str, Any]] = {
            "current": {
                "net": 0.0,
                "people": {"purchase": set(), "sale": set()},
                "unplanned_people": {"purchase": set(), "sale": set()},
                "planned": {"purchase": False, "sale": False},
                "latest": None,
                "rows": [],
            },
            "prior": {
                "net": 0.0,
                "people": {"purchase": set(), "sale": set()},
                "unplanned_people": {"purchase": set(), "sale": set()},
                "planned": {"purchase": False, "sale": False},
                "latest": None,
                "rows": [],
            },
        }
        for row in payload:
            if not isinstance(row, dict):
                raise ValueError("Unexpected FMP insider row schema")
            timestamp = _datetime(row.get("transactionDate") or row.get("filingDate"))
            if timestamp is None or timestamp < prior_cutoff:
                continue
            transaction = str(
                row.get("transactionType") or row.get("acquistionOrDisposition") or ""
            ).upper()
            if transaction not in {"P-PURCHASE", "P", "PURCHASE", "S-SALE", "S", "SALE"}:
                continue
            shares = _number(row.get("securitiesTransacted"))
            price = _number(row.get("price"))
            if shares is None or price is None or shares <= 0 or price <= 0:
                continue
            window = "current" if timestamp >= current_cutoff else "prior"
            side = "sale" if transaction.startswith("S") else "purchase"
            signed_value = shares * price * (-1 if side == "sale" else 1)
            metrics[window]["net"] += signed_value
            name = str(row.get("reportingName") or row.get("reportingOwner") or "").strip()
            if name:
                metrics[window]["people"][side].add(name)
            planned = bool(row.get("is10b51") or row.get("is10b5-1"))
            if name and not planned:
                metrics[window]["unplanned_people"][side].add(name)
            metrics[window]["planned"][side] = metrics[window]["planned"][side] or planned
            metrics[window]["latest"] = max(metrics[window]["latest"] or timestamp, timestamp)
            metrics[window]["rows"].append(row)

        current = metrics["current"]
        prior = metrics["prior"]
        if not current["rows"]:
            return self._result([], "No qualifying recent FMP open-market insider activity.")
        net = float(current["net"])
        all_people = current["people"]["purchase"] | current["people"]["sale"]
        people = len(all_people)
        direction = (
            Direction.BULLISH if net > 0 else Direction.BEARISH if net < 0 else Direction.NEUTRAL
        )
        kind = "purchase" if net > 0 else "sale" if net < 0 else "mixed"
        direction_people = len(current["people"].get(kind, set()))
        clustered = direction_people >= 2
        confidence = 0.82 if clustered else 0.65
        if direction == Direction.BEARISH:
            unplanned_clustered = len(current["unplanned_people"]["sale"]) >= 2
            if clustered and unplanned_clustered:
                confidence = 0.82
            elif current["planned"]["sale"]:
                confidence = 0.50
            else:
                confidence = 0.62
        signal = f"insider_{kind}_{'cluster' if clustered else 'activity'}"
        timestamp = current["latest"] or now
        has_baseline = bool(prior["rows"])
        source_url = next(
            (
                _url(row.get("url") or row.get("link") or row.get("filingUrl"))
                for row in current["rows"]
                if _url(row.get("url") or row.get("link") or row.get("filingUrl"))
            ),
            None,
        )
        evidence = Evidence(
            family=self.family,
            signal=signal,
            direction=direction,
            strength=min(1.0, 0.45 + 0.15 * (direction_people or people)),
            confidence=confidence,
            source_quality=FMP_QUALITY,
            timestamp=timestamp,
            change=(
                Change(
                    description=(
                        f"Net reported open-market insider value was {net:,.0f} across {people} "
                        f"distinct insider{'s' if people != 1 else ''} versus "
                        f"{float(prior['net']):,.0f}."
                    )[:240],
                    current_value=net,
                    baseline_value=float(prior["net"]),
                    delta=net - float(prior["net"]),
                    unit="USD reported value",
                    comparison_window="current half vs preceding equal window",
                )
                if has_baseline
                else None
            ),
            sources=[
                Source(name="FMP insider filings", url=source_url, observed_at=timestamp)
            ],
            notes="Disposition evidence receives lower confidence, especially when marked planned.",
            raw_signal=bounded_raw(current["rows"]),
        )
        result = self._result([evidence], "No qualifying FMP insider activity.")
        if not has_baseline:
            result.warnings.append("insider_trading baseline_unavailable for the prior window.")
        return result


class FmpTechnicalAdapter(FmpNewsAdapter):
    family = "technical"

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        requests = (("rsi", 14), ("sma", 20), ("ema", 12), ("ema", 26))
        row_limit = max(5, min(100, lookback_days + 2))
        now = self._clock_utc()
        start = (now - timedelta(days=max(40, lookback_days * 2))).date().isoformat()
        end = now.date().isoformat()

        async def fetch(indicator: str, period: int):
            payload = await self._get(
                f"/stable/technical-indicators/{indicator}",
                {
                    "symbol": ticker,
                    "periodLength": period,
                    "timeframe": "1day",
                    "from": start,
                    "to": end,
                },
            )
            if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
                raise ValueError("Unexpected FMP technical schema")
            return (indicator, period), payload[:row_limit]

        series = dict(await asyncio.gather(*(fetch(*request) for request in requests)))

        evidence: list[Evidence] = []
        evidence.extend(self._rsi_transition(series[("rsi", 14)]))
        evidence.extend(self._price_transition(series[("sma", 20)], "sma", 20))
        evidence.extend(self._ema_transition(series[("ema", 12)], series[("ema", 26)]))
        return self._result(
            evidence, "No FMP technical threshold or crossover transition occurred."
        )

    def _rsi_transition(self, rows: list[dict[str, Any]]) -> list[Evidence]:
        pair = self._latest_pair(rows, "rsi")
        if pair is None:
            return []
        current, prior, timestamp = pair
        if prior < 30 <= current:
            direction, signal = Direction.BULLISH, "rsi_recovered_30"
        elif prior <= 70 < current:
            direction, signal = Direction.BEARISH, "rsi_crossed_70"
        elif prior > 70 >= current:
            direction, signal = Direction.BEARISH, "rsi_fell_below_70"
        elif prior >= 30 > current:
            direction, signal = Direction.BEARISH, "rsi_fell_below_30"
        else:
            return []
        return [self._technical_evidence(signal, direction, current, prior, "RSI-14", timestamp)]

    def _price_transition(
        self, rows: list[dict[str, Any]], field: str, period: int
    ) -> list[Evidence]:
        if len(rows) < 2:
            return []
        current, prior = rows[0], rows[1]
        current_price, prior_price = _number(current.get("close")), _number(prior.get("close"))
        current_avg, prior_avg = _number(current.get(field)), _number(prior.get(field))
        timestamp = _datetime(current.get("date"))
        if None in {current_price, prior_price, current_avg, prior_avg, timestamp}:
            return []
        if prior_price <= prior_avg and current_price > current_avg:
            direction, signal = Direction.BULLISH, f"price_crossed_above_sma_{period}"
        elif prior_price >= prior_avg and current_price < current_avg:
            direction, signal = Direction.BEARISH, f"price_crossed_below_sma_{period}"
        else:
            return []
        return [
            self._technical_evidence(
                signal, direction, current_price, prior_price, f"close vs SMA-{period}", timestamp
            )
        ]

    def _ema_transition(
        self, short_rows: list[dict[str, Any]], long_rows: list[dict[str, Any]]
    ) -> list[Evidence]:
        short = {str(row.get("date")): _number(row.get("ema")) for row in short_rows}
        long = {str(row.get("date")): _number(row.get("ema")) for row in long_rows}
        dates = sorted(set(short) & set(long), reverse=True)
        if len(dates) < 2:
            return []
        now_date, prior_date = dates[:2]
        current_short, prior_short = short[now_date], short[prior_date]
        current_long, prior_long = long[now_date], long[prior_date]
        timestamp = _datetime(now_date)
        if None in {current_short, prior_short, current_long, prior_long, timestamp}:
            return []
        if prior_short <= prior_long and current_short > current_long:
            direction, signal = Direction.BULLISH, "ema_12_crossed_above_26"
        elif prior_short >= prior_long and current_short < current_long:
            direction, signal = Direction.BEARISH, "ema_12_crossed_below_26"
        else:
            return []
        return [
            self._technical_evidence(
                signal,
                direction,
                current_short - current_long,
                prior_short - prior_long,
                "EMA spread",
                timestamp,
            )
        ]

    @staticmethod
    def _latest_pair(
        rows: list[dict[str, Any]], field: str
    ) -> tuple[float, float, datetime] | None:
        if len(rows) < 2:
            return None
        current, prior = _number(rows[0].get(field)), _number(rows[1].get(field))
        timestamp = _datetime(rows[0].get("date"))
        return (
            None
            if current is None or prior is None or timestamp is None
            else (current, prior, timestamp)
        )

    def _technical_evidence(
        self,
        signal: str,
        direction: Direction,
        current: float,
        prior: float,
        unit: str,
        timestamp: datetime,
    ) -> Evidence:
        return Evidence(
            family=self.family,
            signal=signal,
            direction=direction,
            strength=0.65,
            confidence=0.75,
            source_quality=FMP_QUALITY,
            timestamp=timestamp,
            change=Change(
                description=f"{unit} transitioned from {prior:.2f} to {current:.2f}.",
                current_value=current,
                baseline_value=prior,
                delta=current - prior,
                unit=unit,
                comparison_window="latest daily value vs prior daily value",
            ),
            sources=[Source(name="FMP technical indicator", observed_at=timestamp)],
            raw_signal=bounded_raw({"current": current, "prior": prior, "indicator": unit}),
        )
