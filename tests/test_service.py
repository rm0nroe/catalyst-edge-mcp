import asyncio
from dataclasses import dataclass
from datetime import timedelta

import httpx
import pytest

from catalyst_edge_mcp.adapters import StaticAdapter
from catalyst_edge_mcp.models import (
    AdapterResult,
    Direction,
    EvidenceContext,
    ReasonCode,
    ReasonScope,
    RiskMode,
    SourceStatus,
    ToolInput,
)
from catalyst_edge_mcp.reason_records import scoped_reason
from catalyst_edge_mcp.service import CatalystService
from tests.conftest import AS_OF, make_evidence, make_result


@dataclass
class FailingAdapter:
    family: str

    async def collect(self, ticker, lookback_days):
        raise RuntimeError("vendor secret that must not leak")


@dataclass
class SlowAdapter:
    family: str

    async def collect(self, ticker, lookback_days):
        await asyncio.sleep(0.1)
        return AdapterResult(family=self.family)


@dataclass
class ExceptionAdapter:
    family: str
    exception: Exception
    provider: str = "typed"

    async def collect(self, ticker, lookback_days):
        raise self.exception


@dataclass
class TickerScopedAdapter:
    family: str = "filings_news"
    provider: str = "fund_fixture"
    called: bool = False

    def supports(self, ticker):
        return ticker == "QQQ"

    async def collect(self, ticker, lookback_days):
        self.called = True
        return AdapterResult(family=self.family, provider=self.provider)


@pytest.mark.asyncio
async def test_all_success_fixture_has_complete_coverage(fixed_clock):
    adapters = [
        StaticAdapter(
            "filings_news",
            make_result("filings_news", make_evidence("filings_news", "material_8k")),
        ),
        StaticAdapter(
            "insider_trading",
            make_result("insider_trading", make_evidence("insider_trading", "cluster_activity")),
        ),
        StaticAdapter(
            "options_flow",
            make_result("options_flow", make_evidence("options_flow", "unusual_activity")),
        ),
        StaticAdapter(
            "technical",
            make_result("technical", make_evidence("technical", "ema_crossover")),
        ),
        StaticAdapter(
            "social",
            make_result("social", make_evidence("social", "sentiment_change")),
        ),
    ]
    response = await CatalystService(adapters, clock=fixed_clock).evaluate(ToolInput(ticker="nvda"))

    assert response.ticker == "NVDA"
    assert response.data_quality.coverage == "complete"
    assert response.data_quality.missing_families == []
    assert response.edge.direction == Direction.BULLISH
    assert len(response.evidence) == 5
    assert str(response.evidence[0].sources[0].url).startswith("https://example.com/")


@pytest.mark.asyncio
async def test_partial_collector_failure_is_redacted(fixed_clock):
    adapters = [
        StaticAdapter(
            "filings_news",
            make_result("filings_news", make_evidence("filings_news", "material_8k")),
        ),
        FailingAdapter("insider_trading"),
    ]
    response = await CatalystService(adapters, clock=fixed_clock).evaluate(ToolInput(ticker="NVDA"))

    assert response.data_quality.coverage == "partial"
    assert response.data_quality.missing_families == [
        "insider_trading",
        "options_flow",
        "social",
        "technical",
    ]
    warnings = " ".join(response.data_quality.warnings)
    assert "RuntimeError" in warnings
    assert "vendor secret" not in warnings


@pytest.mark.asyncio
async def test_collector_timeout_is_partial(fixed_clock):
    response = await CatalystService(
        [SlowAdapter("social")], adapter_timeout_seconds=0.01, clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA"))

    assert response.data_quality.coverage == "none"
    assert response.data_quality.missing_families == [
        "filings_news",
        "insider_trading",
        "options_flow",
        "social",
        "technical",
    ]
    assert "social provider SlowAdapter timed out." in response.data_quality.warnings


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "expected_status"),
    [
        (
            httpx.HTTPStatusError(
                "limited",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(
                    429, request=httpx.Request("GET", "https://example.com")
                ),
            ),
            SourceStatus.RATE_LIMITED,
        ),
        (
            httpx.HTTPStatusError(
                "forbidden",
                request=httpx.Request("GET", "https://example.com"),
                response=httpx.Response(
                    403, request=httpx.Request("GET", "https://example.com")
                ),
            ),
            SourceStatus.PERMISSION_REQUIRED,
        ),
        (ValueError("raw response body must not leak"), SourceStatus.SCHEMA_ERROR),
        (httpx.ReadTimeout("slow"), SourceStatus.TIMEOUT),
    ],
)
async def test_provider_failures_map_to_typed_statuses(
    fixed_clock, exception, expected_status
):
    response = await CatalystService(
        [ExceptionAdapter("social", exception)], clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA"))

    status = next(
        item.status for item in response.data_quality.family_statuses if item.family == "social"
    )
    assert status == expected_status
    assert "raw response body" not in " ".join(response.data_quality.warnings)


@pytest.mark.asyncio
async def test_stale_evidence_is_excluded(fixed_clock):
    old = make_evidence(
        "options_flow",
        "old_activity",
        timestamp=AS_OF - timedelta(days=15),
    )
    response = await CatalystService(
        [StaticAdapter("options_flow", make_result("options_flow", old))], clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA", lookback_days=14))

    assert response.evidence == []
    assert response.data_quality.coverage == "none"
    assert response.data_quality.stale_families == ["options_flow"]
    assert response.data_quality.missing_families == [
        "filings_news",
        "insider_trading",
        "options_flow",
        "social",
        "technical",
    ]


@pytest.mark.asyncio
async def test_no_adapter_response_is_explicit(fixed_clock):
    response = await CatalystService(clock=fixed_clock).evaluate(ToolInput(ticker="NVDA"))

    assert response.edge.score == 50
    assert response.data_quality.coverage == "none"
    assert "No live evidence adapters are configured." in response.data_quality.warnings
    assert response.next_checks[0] == (
        "Retry with lookback_days=30 to check a wider filing window."
    )
    assert not any("the observation" in check for check in response.next_checks)


@pytest.mark.asyncio
async def test_custom_expected_family_uses_generic_provider_description(fixed_clock):
    response = await CatalystService(
        clock=fixed_clock,
        expected_families=frozenset({"alternative"}),
    ).evaluate(ToolInput(ticker="NVDA"))

    assert response.data_quality.missing_families == ["alternative"]
    assert any(
        "alternative is unconfigured; expected a configured provider" in warning
        for warning in response.data_quality.warnings
    )


@pytest.mark.asyncio
async def test_scoped_reasons_retain_all_codes_in_deterministic_display_order(fixed_clock):
    discovery = make_evidence("filings_news", "publisher_link")
    discovery.context = EvidenceContext(
        event_type="publisher_coverage",
        event_label="Publisher coverage discovery",
        novelty="new_coverage",
        materiality="discovery_only",
        why_it_matters="Discovery metadata requires primary-source verification.",
    )
    supplied = [
        scoped_reason(
            ReasonCode.ENTITY_REJECTED,
            ReasonScope.CANDIDATE,
            "candidate_rejected",
            source_id="gdelt",
            family="filings_news",
            observed_at=AS_OF,
        ),
        scoped_reason(
            ReasonCode.EVALUATED_NOT_MATERIAL,
            ReasonScope.CANDIDATE,
            "candidate_reviewed",
            source_id="issuer_feed",
            family="filings_news",
            observed_at=AS_OF,
        ),
    ]
    adapters = [
        StaticAdapter(
            "filings_news",
            AdapterResult(
                family="filings_news",
                provider="gdelt",
                evidence=[discovery],
                reason_records=supplied,
                collected_at=AS_OF,
            ),
            provider="gdelt",
        ),
        StaticAdapter(
            "social",
            AdapterResult(
                family="social",
                provider="bluesky",
                status=SourceStatus.NO_OBSERVATIONS,
                collected_at=AS_OF,
            ),
            provider="bluesky",
        ),
        ExceptionAdapter("insider_trading", RuntimeError("unavailable"), provider="sec"),
    ]

    response = await CatalystService(
        adapters,
        clock=fixed_clock,
        expected_families=frozenset(
            {"filings_news", "social", "technical", "insider_trading"}
        ),
    ).evaluate(ToolInput(ticker="NVDA"))

    assert [item.code for item in response.data_quality.reason_records] == [
        ReasonCode.SOURCE_UNAVAILABLE,
        ReasonCode.SOURCE_UNSUPPORTED,
        ReasonCode.ENTITY_REJECTED,
        ReasonCode.OBSERVED_NONE,
        ReasonCode.DISCOVERY_ONLY,
        ReasonCode.EVALUATED_NOT_MATERIAL,
    ]
    assert len({item.reason_id for item in response.data_quality.reason_records}) == 6
    assert response.data_quality.reason_record_count == 6
    assert response.data_quality.reason_records_truncated is False


@pytest.mark.asyncio
async def test_sources_and_raw_signals_are_optional(fixed_clock):
    evidence = make_evidence(
        "social", "attention_change", raw_signal={"mentions": 125, "account": "redacted"}
    )
    service = CatalystService(
        [StaticAdapter("social", make_result("social", evidence))], clock=fixed_clock
    )

    default = await service.evaluate(ToolInput(ticker="NVDA", include_sources=False))
    included = await service.evaluate(ToolInput(ticker="NVDA", include_raw_signals=True))

    assert default.evidence[0].sources == []
    assert default.evidence[0].source_count == 0
    assert default.evidence[0].raw_signal is None
    assert included.evidence[0].raw_signal == {"mentions": 125, "account": "redacted"}


@pytest.mark.asyncio
async def test_unsupported_status_retains_source_unsupported_reason(fixed_clock):
    adapter = StaticAdapter(
        "filings_news",
        AdapterResult(
            family="filings_news",
            provider="sec_funds",
            status=SourceStatus.UNSUPPORTED,
            collected_at=AS_OF,
        ),
        provider="sec_funds",
    )

    response = await CatalystService(
        [adapter],
        clock=fixed_clock,
        expected_families=frozenset({"filings_news"}),
    ).evaluate(ToolInput(ticker="SPY"))

    assert response.data_quality.family_statuses[0].status == SourceStatus.UNSUPPORTED
    assert [reason.code for reason in response.data_quality.reason_records] == [
        ReasonCode.SOURCE_UNSUPPORTED
    ]


@pytest.mark.asyncio
async def test_ticker_scoped_adapter_is_not_called_outside_its_registry(fixed_clock):
    adapter = TickerScopedAdapter()

    await CatalystService(
        [adapter],
        clock=fixed_clock,
        expected_families=frozenset({"filings_news"}),
    ).evaluate(ToolInput(ticker="NVDA"))

    assert adapter.called is False


@pytest.mark.asyncio
@pytest.mark.parametrize("risk_mode", list(RiskMode))
async def test_generated_summary_avoids_transaction_instruction_language(fixed_clock, risk_mode):
    evidence = make_evidence("filings_news", "material_contract")
    response = await CatalystService(
        [StaticAdapter("filings_news", make_result("filings_news", evidence))], clock=fixed_clock
    ).evaluate(ToolInput(ticker="NVDA", risk_mode=risk_mode))
    summary = response.summary.model_dump_json().lower()

    for prohibited in ("buy", "sell", "should purchase", "guaranteed return"):
        assert prohibited not in summary
