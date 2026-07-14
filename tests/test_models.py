import pytest
from pydantic import ValidationError

from catalyst_edge_mcp.models import CatalystEdgeResponse, RiskMode, SourceStatus, ToolInput


def test_input_defaults_and_ticker_normalization():
    request = ToolInput(ticker=" brk.a ")

    assert request.ticker == "BRK.A"
    assert request.lookback_days == 14
    assert request.include_sources is True
    assert request.include_raw_signals is False
    assert request.risk_mode == RiskMode.RESEARCH


@pytest.mark.parametrize("ticker", ["", "123ABC", "A/B", "DROP TABLE", "A" * 13])
def test_invalid_ticker_is_rejected(ticker):
    with pytest.raises((ValidationError, ValueError)):
        ToolInput(ticker=ticker)


@pytest.mark.parametrize("lookback", [0, 91])
def test_lookback_bounds(lookback):
    with pytest.raises(ValidationError):
        ToolInput(ticker="NVDA", lookback_days=lookback)


def test_CT_FAMILY_STATUS_is_present_in_public_response_schema():
    schema = CatalystEdgeResponse.model_json_schema(mode="serialization")
    data_quality = schema["$defs"]["DataQuality"]
    family_status = schema["$defs"]["FamilyStatus"]

    assert "family_statuses" in data_quality["properties"]
    assert set(schema["$defs"]["SourceStatus"]["enum"]) == {
        status.value for status in SourceStatus
    }
    assert set(family_status["required"]) >= {"family", "available", "status", "reason"}
