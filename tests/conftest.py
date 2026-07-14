from datetime import datetime

import pytest

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import AdapterResult, Direction, Evidence, Source

AS_OF = datetime(2026, 7, 12, 16, 0, tzinfo=UTC)


@pytest.fixture
def fixed_clock():
    return lambda: AS_OF


def make_evidence(
    family: str,
    signal: str,
    *,
    direction: Direction = Direction.BULLISH,
    strength: float = 0.8,
    confidence: float = 0.75,
    source_quality: float = 0.9,
    timestamp: datetime = AS_OF,
    raw_signal=None,
) -> Evidence:
    return Evidence(
        family=family,
        signal=signal,
        direction=direction,
        strength=strength,
        confidence=confidence,
        source_quality=source_quality,
        timestamp=timestamp,
        sources=[
            Source(
                name=f"{family}_fixture",
                url=f"https://example.com/{family}/{signal}",
                observed_at=timestamp,
            )
        ],
        notes=f"Normalized {signal} evidence.",
        raw_signal=raw_signal,
    )


def make_result(family: str, *evidence: Evidence) -> AdapterResult:
    return AdapterResult(family=family, evidence=list(evidence))
