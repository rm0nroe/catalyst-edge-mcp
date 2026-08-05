"""Specialist options-flow adapters and degraded yfinance chain activity."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import httpx

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.adapters.fmp import _datetime, _number, _url
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import AdapterResult, Change, Direction, Evidence, Source
from catalyst_edge_mcp.redaction import bounded_raw

OPTIONS_QUALITY = 0.85
YFINANCE_QUALITY = 0.45
FLOWALGO_GATE = ProviderGate(name="flowalgo", concurrency=1)
CHEDDARFLOW_GATE = ProviderGate(name="cheddarflow", concurrency=1)
YFINANCE_GATE = ProviderGate(name="yfinance", concurrency=1)


class _TrueFlowAdapter:
    family = "options_flow"
    quality = OPTIONS_QUALITY
    base_url: str

    def __init__(
        self, api_key: str, *, client: httpx.AsyncClient | None = None, clock=None
    ) -> None:
        if not api_key:
            raise ValueError(f"{self.provider} API key is required")
        self.api_key = api_key
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    def _now(self) -> datetime:
        value = self._clock()
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    async def _request(self, ticker: str, lookback_days: int) -> Any:
        raise NotImplementedError

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        payload = await self._request(ticker, lookback_days)
        rows = (
            payload.get("data", payload.get("results", payload))
            if isinstance(payload, dict)
            else payload
        )
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Unexpected {self.provider} options schema")
        now = self._now()
        half = max(1, lookback_days / 2)
        current_cutoff = now - timedelta(days=half)
        prior_cutoff = now - timedelta(days=half * 2)
        buckets = {
            "current": {"call": 0.0, "put": 0.0, "volume": 0.0, "oi": 0.0, "large": 0.0},
            "prior": {"call": 0.0, "put": 0.0, "volume": 0.0, "oi": 0.0, "large": 0.0},
        }
        accepted: list[dict[str, Any]] = []
        current_rows: list[dict[str, Any]] = []
        newest: datetime | None = None
        for row in rows:
            timestamp = _datetime(row.get("timestamp") or row.get("time") or row.get("date"))
            if timestamp is None or timestamp < prior_cutoff:
                continue
            symbol = str(row.get("symbol") or row.get("ticker") or ticker).upper()
            if symbol != ticker:
                continue
            window = "current" if timestamp >= current_cutoff else "prior"
            premium = abs(_number(row.get("premium") or row.get("total_premium")) or 0.0)
            side = str(
                row.get("type") or row.get("call_put") or row.get("option_type") or ""
            ).lower()
            if "call" in side or side == "c":
                buckets[window]["call"] += premium
            elif "put" in side or side == "p":
                buckets[window]["put"] += premium
            buckets[window]["volume"] += _number(row.get("volume") or row.get("size")) or 0.0
            buckets[window]["oi"] += (
                _number(row.get("open_interest") or row.get("openInterest")) or 0.0
            )
            trade_type = str(row.get("trade_type") or row.get("type_label") or "").lower()
            if "sweep" in trade_type or "block" in trade_type:
                buckets[window]["large"] += 1
            newest = max(newest or timestamp, timestamp)
            accepted.append(row)
            if window == "current":
                current_rows.append(row)
        current, prior = buckets["current"], buckets["prior"]
        current_directional = current["call"] - current["put"]
        prior_directional = prior["call"] - prior["put"]
        if not accepted or current["call"] + current["put"] <= 0:
            return self._result(
                [], [f"No recent {self.provider} directional options flow was available."]
            )
        has_baseline = prior["call"] + prior["put"] > 0
        delta = current_directional - prior_directional if has_baseline else current_directional
        call_delta = current["call"] - prior["call"]
        put_delta = current["put"] - prior["put"]
        current_volume_oi = (
            current["volume"] / current["oi"] if current["oi"] > 0 else None
        )
        prior_volume_oi = prior["volume"] / prior["oi"] if prior["oi"] > 0 else None
        ratio_description = (
            "Volume/open-interest ratio was unavailable."
            if current_volume_oi is None or prior_volume_oi is None
            else (
                "Volume/open-interest ratio changed from "
                f"{prior_volume_oi:.2f} to {current_volume_oi:.2f}."
            )
        )
        directional_change = delta if has_baseline else current_directional
        direction = (
            Direction.BULLISH
            if directional_change > 0
            else Direction.BEARISH
            if directional_change < 0
            else Direction.NEUTRAL
        )
        signal = self._flow_signal(
            has_baseline=has_baseline,
            direction=direction,
            current_directional=current_directional,
            call_delta=call_delta,
            put_delta=put_delta,
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
            strength=min(
                1.0,
                abs(directional_change)
                / max(
                    1.0,
                    current["call"] + current["put"],
                    prior["call"] + prior["put"] if has_baseline else 0.0,
                ),
            ),
            confidence=0.78,
            source_quality=self.quality,
            timestamp=timestamp,
            change=(
                Change(
                    description=(
                        f"Directional options premium changed from {prior_directional:,.0f} "
                        f"to {current_directional:,.0f}. Sweep/block count changed from "
                        f"{int(prior['large'])} to {int(current['large'])}. {ratio_description}"
                    ),
                    current_value=current_directional,
                    baseline_value=prior_directional,
                    delta=delta,
                    unit="USD directional premium",
                    comparison_window="current half vs preceding equal window",
                )
                if has_baseline
                else None
            ),
            sources=[Source(name=self.provider, url=source_url, observed_at=timestamp)],
            raw_signal=bounded_raw(accepted),
        )
        warnings = (
            []
            if has_baseline
            else [f"options_flow baseline_unavailable from {self.provider}."]
        )
        return self._result([evidence], warnings)

    @staticmethod
    def _flow_signal(
        *,
        has_baseline: bool,
        direction: Direction,
        current_directional: float,
        call_delta: float,
        put_delta: float,
    ) -> str:
        if not has_baseline:
            if current_directional > 0:
                return "call_dominant_flow_observation"
            if current_directional < 0:
                return "put_dominant_flow_observation"
            return "balanced_flow_observation"
        if direction == Direction.NEUTRAL:
            return "directional_flow_unchanged"
        if direction == Direction.BULLISH:
            return (
                "call_flow_increase"
                if max(call_delta, 0.0) >= max(-put_delta, 0.0)
                else "put_flow_decrease"
            )
        return (
            "put_flow_increase"
            if max(put_delta, 0.0) >= max(-call_delta, 0.0)
            else "call_flow_decrease"
        )

    def _result(self, evidence: list[Evidence], warnings: list[str]) -> AdapterResult:
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=warnings,
            collected_at=self._now(),
        )


class FlowAlgoAdapter(_TrueFlowAdapter):
    provider = "flowalgo"

    async def _request(self, ticker: str, lookback_days: int) -> Any:
        params = {"symbol": ticker, "timeframe": f"{lookback_days}d", "limit": 500}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with FLOWALGO_GATE.request():
            if self._client is not None:
                response = await self._client.get(
                    "https://api.flowalgo.com/v1/flow", params=params, headers=headers
                )
            else:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    response = await client.get(
                        "https://api.flowalgo.com/v1/flow", params=params, headers=headers
                    )
        response.raise_for_status()
        return response.json()


class CheddarFlowAdapter(_TrueFlowAdapter):
    provider = "cheddarflow"

    async def _request(self, ticker: str, lookback_days: int) -> Any:
        params = {"hours": min(2160, lookback_days * 24)}
        headers = {"X-API-Key": self.api_key}
        url = f"https://api.cheddarflow.com/v1/options/flow/{ticker}"
        async with CHEDDARFLOW_GATE.request():
            if self._client is not None:
                response = await self._client.get(url, params=params, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


class YFinanceOptionsAdapter:
    """Nearest-expiration chain snapshot; never represented as transaction flow."""

    family = "options_flow"
    provider = "yfinance"

    def __init__(
        self,
        *,
        chain_loader: Callable[[str], tuple[str, Any, Any]] | None = None,
        clock=None,
        selection_warning: str | None = None,
    ) -> None:
        self._chain_loader = chain_loader or self._load_chain
        self._clock = clock or (lambda: datetime.now(UTC))
        self.selection_warning = selection_warning

    def _now(self) -> datetime:
        value = self._clock()
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _load_chain(ticker: str) -> tuple[str, Any, Any]:
        import yfinance as yf

        security = yf.Ticker(ticker)
        expirations = security.options
        if not expirations:
            raise ValueError("No yfinance option expirations")
        expiration = expirations[0]
        chain = security.option_chain(expiration)
        return expiration, chain.calls, chain.puts

    @staticmethod
    def _sum_column(table: Any, name: str) -> float:
        if isinstance(table, list):
            return sum(_number(row.get(name)) or 0.0 for row in table if isinstance(row, dict))
        if hasattr(table, "__getitem__"):
            column = table[name]
            if hasattr(column, "fillna"):
                column = column.fillna(0)
            if hasattr(column, "sum"):
                return float(column.sum())
        return 0.0

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        del lookback_days
        async with YFINANCE_GATE.request():
            expiration, calls, puts = await asyncio.to_thread(self._chain_loader, ticker)
        call_volume = self._sum_column(calls, "volume")
        put_volume = self._sum_column(puts, "volume")
        call_oi = self._sum_column(calls, "openInterest")
        put_oi = self._sum_column(puts, "openInterest")
        now = self._now()
        warnings = [
            "yfinance provides degraded options-chain activity; transaction flow is unavailable."
        ]
        if self.selection_warning:
            warnings.insert(0, self.selection_warning)
        if call_volume + put_volume <= 0:
            warnings.append("No yfinance chain volume was available for the nearest expiration.")
            return AdapterResult(
                family=self.family,
                provider=self.provider,
                warnings=warnings,
                degraded=True,
                collected_at=now,
            )
        ratio = call_volume / max(1.0, put_volume)
        direction = (
            Direction.BULLISH
            if ratio >= 1.5
            else Direction.BEARISH
            if ratio <= 0.67
            else Direction.NEUTRAL
        )
        signal = (
            "call_activity_increase"
            if direction == Direction.BULLISH
            else "put_activity_increase"
            if direction == Direction.BEARISH
            else "balanced_chain_activity"
        )
        evidence = Evidence(
            family=self.family,
            signal=signal,
            direction=direction,
            strength=min(1.0, abs(call_volume - put_volume) / max(1.0, call_volume + put_volume)),
            confidence=0.45,
            source_quality=YFINANCE_QUALITY,
            timestamp=now,
            change=Change(
                description=(
                    f"Nearest-expiration call volume was {call_volume:.0f} versus put volume "
                    f"of {put_volume:.0f} (ratio {ratio:.2f})."
                ),
                current_value=call_volume,
                baseline_value=put_volume,
                delta=call_volume - put_volume,
                unit="chain contracts",
                comparison_window=f"call vs put snapshot for {expiration}",
            ),
            sources=[Source(name="yfinance chain snapshot", observed_at=now)],
            notes="Snapshot activity is not transaction-level options flow.",
            raw_signal=bounded_raw(
                {
                    "expiration": expiration,
                    "call_volume": call_volume,
                    "put_volume": put_volume,
                    "call_open_interest": call_oi,
                    "put_open_interest": put_oi,
                }
            ),
        )
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=[evidence],
            warnings=warnings,
            degraded=True,
            collected_at=now,
        )


def select_options_adapter(
    provider: str,
    *,
    flowalgo_api_key: str | None,
    cheddarflow_api_key: str | None,
) -> _TrueFlowAdapter | YFinanceOptionsAdapter:
    if provider not in {"auto", "flowalgo", "cheddarflow", "yfinance"}:
        raise ValueError(
            "CATALYST_EDGE_OPTIONS_PROVIDER must be auto, flowalgo, cheddarflow, or yfinance"
        )
    if provider == "auto":
        if flowalgo_api_key:
            return FlowAlgoAdapter(flowalgo_api_key)
        if cheddarflow_api_key:
            return CheddarFlowAdapter(cheddarflow_api_key)
        return YFinanceOptionsAdapter()
    if provider == "flowalgo" and flowalgo_api_key:
        return FlowAlgoAdapter(flowalgo_api_key)
    if provider == "cheddarflow" and cheddarflow_api_key:
        return CheddarFlowAdapter(cheddarflow_api_key)
    if provider == "yfinance":
        return YFinanceOptionsAdapter()
    return YFinanceOptionsAdapter(
        selection_warning=(
            f"Explicit {provider} selection was unavailable; using degraded yfinance activity."
        )
    )
