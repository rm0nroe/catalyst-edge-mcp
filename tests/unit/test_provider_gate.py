import asyncio

import pytest

from catalyst_edge_mcp.adapters import base


@pytest.mark.asyncio
async def test_provider_gate_enforces_two_request_starts_per_second(monkeypatch):
    now = 0.0
    starts = []
    real_sleep = asyncio.sleep

    def monotonic():
        return now

    async def sleep(delay):
        nonlocal now
        now += delay
        await real_sleep(0)

    monkeypatch.setattr(base.time, "monotonic", monotonic)
    monkeypatch.setattr(base.asyncio, "sleep", sleep)
    gate = base.ProviderGate(concurrency=2, requests_per_second=2)

    async def request():
        async with gate.request():
            starts.append(now)

    await asyncio.gather(*(request() for _ in range(3)))

    assert starts == [0.0, 0.5, 1.0]


@pytest.mark.asyncio
async def test_PT_GDELT_THROTTLE_enforces_serialized_five_second_starts(monkeypatch):
    now = 0.0
    starts = []
    active = 0
    max_active = 0
    real_sleep = asyncio.sleep

    def monotonic():
        return now

    async def sleep(delay):
        nonlocal now
        now += delay
        await real_sleep(0)

    monkeypatch.setattr(base.time, "monotonic", monotonic)
    monkeypatch.setattr(base.asyncio, "sleep", sleep)
    gate = base.ProviderGate(concurrency=1, requests_per_second=0.2)

    async def request():
        nonlocal active, max_active
        async with gate.request():
            starts.append(now)
            active += 1
            max_active = max(max_active, active)
            await real_sleep(0)
            active -= 1

    await asyncio.gather(*(request() for _ in range(3)))

    assert starts == [0.0, 5.0, 10.0]
    assert max_active == 1
