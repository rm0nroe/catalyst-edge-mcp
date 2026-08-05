"""Adapter contracts and common deterministic test adapter."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from typing import Protocol

from catalyst_edge_mcp.models import AdapterResult


@dataclass(slots=True)
class GateTiming:
    """Running totals for one gate. Aggregates only, so memory stays O(1)."""

    name: str
    requests: int = 0
    admission_wait_s: float = 0.0
    body_s: float = 0.0
    max_admission_wait_s: float = 0.0
    # Requests cancelled before the gate ever admitted them. A high count is the
    # direct signature of admission exhaustion: the caller's whole budget was
    # spent queueing and it never reached the network.
    never_admitted: int = 0


_GATE_TIMINGS: dict[str, GateTiming] = {}


def gate_timings() -> dict[str, GateTiming]:
    """Snapshot of per-gate timings. Copies, so callers cannot corrupt totals."""
    return {name: replace(timing) for name, timing in _GATE_TIMINGS.items()}


def reset_gate_timings() -> None:
    _GATE_TIMINGS.clear()


class CatalystSignalAdapter(Protocol):
    family: str
    provider: str

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult: ...


@dataclass(slots=True)
class StaticAdapter:
    family: str
    result: AdapterResult
    provider: str = "fixture"

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        del ticker, lookback_days
        result = self.result.model_copy(deep=True)
        if result.provider == "unknown":
            result.provider = self.provider
        return result


class ProviderGate:
    """Process-local concurrency and start-rate gate; it never retries a request."""

    def __init__(
        self,
        *,
        concurrency: int,
        requests_per_second: float | None = None,
        name: str = "unnamed",
    ) -> None:
        self._name = name
        self._concurrency = concurrency
        self._loop = None
        self._semaphore = asyncio.Semaphore(concurrency)
        self._spacing = 0.0 if not requests_per_second else 1.0 / requests_per_second
        self._rate_lock = asyncio.Lock()
        self._next_start = 0.0

    @property
    def requests_per_second(self) -> float:
        """Configured start rate; 0.0 means unthrottled."""
        return 0.0 if self._spacing == 0 else 1.0 / self._spacing

    def _primitives(self) -> tuple[asyncio.Semaphore, asyncio.Lock]:
        loop = asyncio.get_running_loop()
        if loop is not self._loop:
            self._loop = loop
            self._semaphore = asyncio.Semaphore(self._concurrency)
            self._rate_lock = asyncio.Lock()
            self._next_start = 0.0
        return self._semaphore, self._rate_lock

    def _record(self, admission_wait_s: float, body_s: float, *, admitted: bool) -> None:
        timing = _GATE_TIMINGS.get(self._name)
        if timing is None:
            timing = _GATE_TIMINGS[self._name] = GateTiming(name=self._name)
        timing.requests += 1
        timing.admission_wait_s += admission_wait_s
        timing.body_s += body_s
        timing.max_admission_wait_s = max(timing.max_admission_wait_s, admission_wait_s)
        if not admitted:
            timing.never_admitted += 1

    @asynccontextmanager
    async def request(self):
        semaphore, rate_lock = self._primitives()
        requested_at = time.monotonic()
        admitted_at: float | None = None
        # The `finally` must sit outside the semaphore acquisition, not inside it.
        # The service cancels adapter.collect() at its 8s deadline, and a saturated
        # gate cancels callers while they are still queued for the semaphore -- those
        # never enter the body at all. Recording only admitted requests would hide
        # exactly the population this instrumentation exists to measure.
        try:
            async with semaphore:
                async with rate_lock:
                    now = time.monotonic()
                    if self._next_start > now:
                        await asyncio.sleep(self._next_start - now)
                        now = time.monotonic()
                    self._next_start = now + self._spacing
                admitted_at = time.monotonic()
                yield
        finally:
            ended_at = time.monotonic()
            if admitted_at is None:
                # Died queueing: the entire elapsed time was admission wait.
                self._record(ended_at - requested_at, 0.0, admitted=False)
            else:
                self._record(admitted_at - requested_at, ended_at - admitted_at, admitted=True)

    async def defer_for(self, seconds: float) -> None:
        """Move the next permitted start forward without sleeping the caller."""
        _, rate_lock = self._primitives()
        async with rate_lock:
            self._next_start = max(self._next_start, time.monotonic() + max(0.0, seconds))
