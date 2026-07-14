"""Adapter contracts and common deterministic test adapter."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

from catalyst_edge_mcp.models import AdapterResult


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

    def __init__(self, *, concurrency: int, requests_per_second: float | None = None) -> None:
        self._concurrency = concurrency
        self._loop = None
        self._semaphore = asyncio.Semaphore(concurrency)
        self._spacing = 0.0 if not requests_per_second else 1.0 / requests_per_second
        self._rate_lock = asyncio.Lock()
        self._next_start = 0.0

    def _primitives(self) -> tuple[asyncio.Semaphore, asyncio.Lock]:
        loop = asyncio.get_running_loop()
        if loop is not self._loop:
            self._loop = loop
            self._semaphore = asyncio.Semaphore(self._concurrency)
            self._rate_lock = asyncio.Lock()
            self._next_start = 0.0
        return self._semaphore, self._rate_lock

    @asynccontextmanager
    async def request(self):
        semaphore, rate_lock = self._primitives()
        async with semaphore:
            async with rate_lock:
                now = time.monotonic()
                if self._next_start > now:
                    await asyncio.sleep(self._next_start - now)
                    now = time.monotonic()
                self._next_start = now + self._spacing
            yield

    async def defer_for(self, seconds: float) -> None:
        """Move the next permitted start forward without sleeping the caller."""
        _, rate_lock = self._primitives()
        async with rate_lock:
            self._next_start = max(self._next_start, time.monotonic() + max(0.0, seconds))
