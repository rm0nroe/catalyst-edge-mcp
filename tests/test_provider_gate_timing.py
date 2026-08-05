"""Timing instrumentation for ProviderGate.

The catalyst scan aborts because SEC adapters exceed an 8s budget. These tests
pin the measurement that tells us whether that budget is consumed by gate
admission (semaphore + rate spacing) or by actual network I/O.
"""

from __future__ import annotations

import asyncio

import pytest

from catalyst_edge_mcp.adapters.base import (
    ProviderGate,
    gate_timings,
    reset_gate_timings,
)


@pytest.fixture(autouse=True)
def _clean_timings():
    reset_gate_timings()
    yield
    reset_gate_timings()


async def test_admission_wait_accumulates_under_rate_limiting():
    """Rate spacing is charged to admission wait, not to the body."""
    gate = ProviderGate(name="t_rate", concurrency=1, requests_per_second=10)  # 0.1s spacing

    async def once():
        async with gate.request():
            pass

    await asyncio.gather(*(once() for _ in range(3)))

    stats = gate_timings()["t_rate"]
    assert stats.requests == 3
    # 1st admits immediately, 2nd waits ~0.1s, 3rd ~0.2s => ~0.3s total.
    assert stats.admission_wait_s >= 0.15
    assert stats.max_admission_wait_s >= 0.1
    # Bodies are empty; their time must not be folded into admission wait.
    assert stats.body_s < 0.05


async def test_body_time_recorded_separately_without_contention():
    """A slow body with an idle gate reports body time, not admission wait."""
    gate = ProviderGate(name="t_body", concurrency=4)

    async with gate.request():
        await asyncio.sleep(0.1)

    stats = gate_timings()["t_body"]
    assert stats.requests == 1
    assert stats.body_s >= 0.1
    assert stats.admission_wait_s < 0.05


async def test_cancelled_body_still_records_admission_wait():
    """The timed-out population is the one under study, so it must be measured.

    service.py wraps adapter.collect() in asyncio.wait_for(timeout=8). When that
    fires, the body is cancelled mid-flight. If instrumentation only recorded on
    clean exit, every timed-out request -- the exact thing we are investigating --
    would be invisible.
    """
    gate = ProviderGate(name="t_cancel", concurrency=1, requests_per_second=10)

    async def blocker():
        async with gate.request():
            await asyncio.sleep(5)

    async def victim():
        async with gate.request():
            await asyncio.sleep(5)

    block = asyncio.create_task(blocker())
    await asyncio.sleep(0.05)  # let blocker take the only slot

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(victim(), timeout=0.3)

    block.cancel()
    with pytest.raises(asyncio.CancelledError):
        await block

    stats = gate_timings()["t_cancel"]
    # Both the blocker and the victim must appear.
    assert stats.requests == 2
    # The victim died queueing, so it is charged entirely as admission wait and
    # counted as never admitted -- the direct signature of gate exhaustion.
    assert stats.never_admitted == 1
    assert stats.max_admission_wait_s >= 0.2


async def test_gate_timings_snapshot_is_isolated():
    """Callers must not be able to mutate recorded stats through the snapshot."""
    gate = ProviderGate(name="t_snap", concurrency=1)
    async with gate.request():
        pass

    snapshot = gate_timings()
    snapshot["t_snap"].requests = 999

    assert gate_timings()["t_snap"].requests == 1
