from datetime import timedelta

import pytest
from pydantic import ValidationError

from catalyst_edge_mcp.adapters import StaticAdapter
from catalyst_edge_mcp.adapters.options import YFinanceOptionsAdapter, select_options_adapter
from catalyst_edge_mcp.models import AdapterResult, Direction, ToolInput
from catalyst_edge_mcp.redaction import bounded_raw, redact_raw
from catalyst_edge_mcp.scorer import CANONICAL_FAMILIES, DeterministicScorer
from catalyst_edge_mcp.service import CatalystService
from tests.conftest import AS_OF, make_evidence, make_result


def _all_family_adapters(direction=Direction.BULLISH):
    return [
        StaticAdapter(
            family,
            make_result(
                family,
                make_evidence(
                    family,
                    f"{family}_change",
                    direction=direction,
                    strength=0.9,
                    confidence=0.9,
                    source_quality=0.9,
                ),
            ),
        )
        for family in CANONICAL_FAMILIES
    ]


@pytest.mark.parametrize(
    "ticker",
    [
        "A/B",
        "A\\B",
        "NVDA--",
        "x/*y*/",
        "OR 1=1",
        "script",
        "exec",
        "union",
        "select",
        "NVDA\n",
    ],
)
def test_UT_INPUT_INVALID_TICKER(ticker):
    with pytest.raises(ValidationError):
        ToolInput(ticker=ticker)


def test_UT_INPUT_UNKNOWN_FIELDS_AND_BOUNDS():
    with pytest.raises(ValidationError):
        ToolInput.model_validate({"ticker": "NVDA", "unexpected": True})
    with pytest.raises(ValidationError):
        ToolInput(ticker="NVDA", lookback_days=91)


def test_UT_SCORE_ATTRIBUTION():
    items = [
        make_evidence("filings_news", "support", strength=0.8, confidence=0.8),
        make_evidence(
            "filings_news",
            "contradiction",
            direction=Direction.BEARISH,
            strength=0.5,
            confidence=0.8,
        ),
    ]
    result = DeterministicScorer().score(
        items,
        as_of=AS_OF,
        lookback_days=14,
        expected_families=CANONICAL_FAMILIES,
    )
    assert result.evidence[0].contribution > 0
    assert result.evidence[1].contribution < 0
    assert sum(item.contribution for item in result.evidence) == pytest.approx(
        result.family_contributions["filings_news"]
    )


def test_UT_RAW_RECURSIVE_REDACTION_AND_LIMIT():
    raw = {
        "token": "top-secret",
        "nested": {
            "Authorization": "Bearer secret",
            "safe": "x" * 20_000,
            "items": [{"user-id": "42", "value": index} for index in range(100)],
        },
    }
    redacted = redact_raw(raw)
    rendered = str(redacted).lower()
    assert "top-secret" not in rendered
    assert "bearer secret" not in rendered
    assert "user-id" not in rendered
    bounded = bounded_raw({f"field_{index}": "x" * 1_000 for index in range(50)})
    assert bounded["truncated"] is True
    assert len(str(bounded).encode()) <= 8192


@pytest.mark.asyncio
async def test_UT_QUALITY_CANONICAL_UNCONFIGURED_AND_LOW_CONFIDENCE(fixed_clock):
    evidence = make_evidence("social", "weak", confidence=0.40)
    response = await CatalystService(
        [StaticAdapter("social", make_result("social", evidence))], clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA"))
    assert response.data_quality.coverage == "partial"
    assert set(response.data_quality.missing_families) == set(CANONICAL_FAMILIES) - {"social"}
    assert any("social contains evidence" in warning for warning in response.data_quality.warnings)
    assert any("Overall confidence" in warning for warning in response.data_quality.warnings)


@pytest.mark.asyncio
async def test_UT_COMPACTNESS_RETAINS_CONTRADICTION(fixed_clock):
    items = [
        make_evidence("filings_news", f"bull_{index}", strength=1 - index / 20)
        for index in range(5)
    ]
    items.append(
        make_evidence(
            "filings_news",
            "bearish_counterpoint",
            direction=Direction.BEARISH,
            strength=0.1,
        )
    )
    response = await CatalystService(
        [StaticAdapter("filings_news", make_result("filings_news", *items))],
        clock=fixed_clock,
    ).evaluate(ToolInput(ticker="NVDA"))
    assert len(response.evidence) == 3
    assert any(item.direction == Direction.BEARISH for item in response.evidence)


def test_global_compaction_retains_contradiction_after_fifteen_item_cap():
    items = []
    for index in range(16):
        item = make_evidence(f"family_{index}", f"bull_{index}")
        item.contribution = float(20 - index)
        items.append(item)
    contradiction = make_evidence(
        "contradiction_family",
        "sole_bearish_counterpoint",
        direction=Direction.BEARISH,
    )
    contradiction.contribution = -0.01
    items.append(contradiction)

    compact = CatalystService._compact(items)

    assert len(compact) == 15
    assert contradiction in compact


@pytest.mark.asyncio
async def test_evaluate_retains_global_contradiction_after_fifteen_item_cap(fixed_clock):
    adapters = []
    for index in range(16):
        family = f"family_{index}"
        item = make_evidence(family, f"bull_{index}", strength=1.0)
        adapters.append(StaticAdapter(family, make_result(family, item)))
    contradiction = make_evidence(
        "contradiction_family",
        "sole_bearish_counterpoint",
        direction=Direction.BEARISH,
        strength=0.01,
    )
    adapters.append(
        StaticAdapter(
            "contradiction_family",
            make_result("contradiction_family", contradiction),
        )
    )

    response = await CatalystService(adapters, clock=fixed_clock).evaluate(
        ToolInput(ticker="NVDA")
    )

    assert len(response.evidence) == 15
    assert any(item.signal == "sole_bearish_counterpoint" for item in response.evidence)


@pytest.mark.asyncio
async def test_FX_STALE_OPTIONS(fixed_clock):
    stale = make_evidence("options_flow", "old", timestamp=AS_OF - timedelta(days=30))
    response = await CatalystService(
        [StaticAdapter("options_flow", make_result("options_flow", stale))],
        clock=fixed_clock,
    ).evaluate(ToolInput(ticker="NVDA", lookback_days=14))
    assert "options_flow" in response.data_quality.stale_families
    assert "options_flow" in response.data_quality.missing_families


@pytest.mark.asyncio
async def test_UT_DEGRADED_YFINANCE_FALLBACK(fixed_clock):
    adapter = YFinanceOptionsAdapter(
        chain_loader=lambda ticker: (
            "2026-07-17",
            [{"volume": 200, "openInterest": 500}],
            [{"volume": 50, "openInterest": 300}],
        ),
        clock=fixed_clock,
    )
    result = await adapter.collect("NVDA", 14)
    assert result.degraded is True
    assert result.evidence[0].confidence == 0.45
    assert result.evidence[0].direction == Direction.BULLISH
    assert "transaction flow is unavailable" in " ".join(result.warnings)


def test_UT_OPTIONS_PROVIDER_SELECTION():
    assert (
        select_options_adapter("auto", flowalgo_api_key="key", cheddarflow_api_key="other").provider
        == "flowalgo"
    )
    fallback = select_options_adapter(
        "cheddarflow", flowalgo_api_key=None, cheddarflow_api_key=None
    )
    assert fallback.provider == "yfinance"
    assert "unavailable" in fallback.selection_warning


@pytest.mark.asyncio
async def test_UT_PARTIAL_FAILURE_IS_SANITIZED(fixed_clock):
    class SecretFailure:
        family = "technical"
        provider = "fixture-provider"

        async def collect(self, ticker, lookback_days):
            raise RuntimeError("api_key=must-never-appear")

    response = await CatalystService([SecretFailure()], clock=fixed_clock).evaluate(
        ToolInput(ticker="NVDA")
    )
    warnings = " ".join(response.data_quality.warnings)
    assert "RuntimeError" in warnings
    assert "must-never-appear" not in warnings


@pytest.mark.asyncio
async def test_FX_NO_DATA(fixed_clock):
    response = await CatalystService(clock=fixed_clock).evaluate(ToolInput(ticker="NVDA"))
    assert response.edge.score == 50
    assert response.edge.confidence == 0
    assert response.data_quality.coverage == "none"
    assert set(response.data_quality.missing_families) == set(CANONICAL_FAMILIES)


@pytest.mark.asyncio
async def test_FX_STRONG_BULLISH(fixed_clock):
    response = await CatalystService(_all_family_adapters(), clock=fixed_clock).evaluate(
        ToolInput(ticker="NVDA")
    )
    assert response.data_quality.coverage == "complete"
    assert response.edge.direction == Direction.BULLISH
    assert response.edge.confidence >= 0.70


@pytest.mark.asyncio
async def test_FX_WEAK_SOCIAL(fixed_clock):
    weak = make_evidence("social", "attention", strength=0.2, confidence=0.4)
    response = await CatalystService(
        [StaticAdapter("social", make_result("social", weak))], clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA"))
    assert response.edge.direction == Direction.NEUTRAL
    assert response.edge.confidence < 0.5


@pytest.mark.asyncio
async def test_FX_BEARISH_FILING_NEWS(fixed_clock):
    bearish = make_evidence(
        "filings_news",
        "adverse_filing",
        direction=Direction.BEARISH,
        strength=1,
        confidence=1,
        source_quality=1,
    )
    response = await CatalystService(
        [StaticAdapter("filings_news", make_result("filings_news", bearish))],
        clock=fixed_clock,
    ).evaluate(ToolInput(ticker="NVDA"))
    assert response.edge.direction == Direction.BEARISH


@pytest.mark.asyncio
async def test_FX_MISSING_INSIDER(fixed_clock):
    adapters = [
        adapter for adapter in _all_family_adapters() if adapter.family != "insider_trading"
    ]
    response = await CatalystService(adapters, clock=fixed_clock).evaluate(ToolInput(ticker="NVDA"))
    assert response.data_quality.missing_families == ["insider_trading"]


@pytest.mark.asyncio
async def test_UT_TIMEOUT(fixed_clock):
    class Slow:
        family = "technical"
        provider = "slow"

        async def collect(self, ticker, lookback_days):
            import asyncio

            await asyncio.sleep(1)
            return AdapterResult(family=self.family, provider=self.provider)

    response = await CatalystService(
        [Slow()], adapter_timeout_seconds=0.001, clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA"))
    assert any("timed out" in warning for warning in response.data_quality.warnings)


@pytest.mark.asyncio
async def test_UT_PROVENANCE(fixed_clock):
    item = make_evidence("social", "change", raw_signal={"token": "secret", "value": 1})
    service = CatalystService(
        [StaticAdapter("social", make_result("social", item))], clock=fixed_clock
    )
    suppressed = await service.evaluate(ToolInput(ticker="NVDA", include_sources=False))
    raw = await service.evaluate(ToolInput(ticker="NVDA", include_raw_signals=True))
    assert suppressed.evidence[0].sources == []
    assert suppressed.evidence[0].source_count == 0
    assert raw.evidence[0].raw_signal == {"value": 1}


@pytest.mark.asyncio
async def test_UT_RAW_DEFAULT(fixed_clock):
    item = make_evidence("social", "change", raw_signal={"value": 1})
    service = CatalystService(
        [StaticAdapter("social", make_result("social", item))], clock=fixed_clock
    )

    response = await service.evaluate(ToolInput(ticker="NVDA"))

    assert response.evidence[0].raw_signal is None


@pytest.mark.asyncio
@pytest.mark.parametrize("risk_mode", ["research", "alert_triage", "thesis_review"])
async def test_UT_LANGUAGE_ALL_MODES(fixed_clock, risk_mode):
    response = await CatalystService(_all_family_adapters(), clock=fixed_clock).evaluate(
        ToolInput(ticker="NVDA", risk_mode=risk_mode)
    )
    generated = (response.summary.model_dump_json() + " " + " ".join(response.next_checks)).lower()
    for prohibited in ("buy", "sell", "guaranteed", "alpha", "expected return"):
        assert prohibited not in generated
