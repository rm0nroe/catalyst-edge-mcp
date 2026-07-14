import asyncio
import json
from pathlib import Path

import httpx
import pytest

from catalyst_edge_mcp.adapters.finnhub import FinnhubLobbyingAdapter, FinnhubSocialAdapter
from catalyst_edge_mcp.adapters.fmp import FmpInsiderAdapter, FmpNewsAdapter, FmpTechnicalAdapter
from catalyst_edge_mcp.adapters.options import CheddarFlowAdapter, FlowAlgoAdapter
from catalyst_edge_mcp.models import Direction
from tests.conftest import AS_OF

FIXTURES = Path(__file__).parents[1] / "fixtures" / "providers"


def _fixture(name):
    return json.loads((FIXTURES / name).read_text())


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_PT_FMP_NEWS_NORMALIZATION():
    def handler(request):
        assert request.url.path == "/stable/news/stock"
        assert request.url.params["symbols"] == "NVDA"
        assert request.headers["apikey"] == "test-key"
        assert "apikey" not in request.url.params
        return httpx.Response(200, json=_fixture("fmp_news.json"))

    async with _client(handler) as client:
        result = await FmpNewsAdapter("test-key", client=client, clock=lambda: AS_OF).collect(
            "NVDA", 14
        )
    assert result.evidence[0].direction == Direction.NEUTRAL
    assert str(result.evidence[0].sources[0].url).startswith("https://example.com/news/")
    assert "apiKey" not in result.evidence[0].raw_signal


@pytest.mark.asyncio
async def test_PT_FMP_INSIDER_NORMALIZATION():
    def handler(request):
        return httpx.Response(200, json=_fixture("fmp_insider.json"))

    async with _client(handler) as client:
        result = await FmpInsiderAdapter("test-key", client=client, clock=lambda: AS_OF).collect(
            "NVDA", 14
        )
    assert result.evidence[0].signal == "insider_purchase_cluster"
    assert result.evidence[0].change.baseline_value == -1000
    assert str(result.evidence[0].sources[0].url).endswith("/insider/current")


@pytest.mark.asyncio
async def test_fmp_insider_zero_transacted_shares_do_not_fall_back_to_holdings():
    payload = [
        {
            "transactionDate": "2026-07-11",
            "transactionType": "P-PURCHASE",
            "securitiesTransacted": 0,
            "securitiesOwned": 10_000,
            "price": 100,
            "reportingName": "Current Insider",
        },
        {
            "transactionDate": "2026-07-03",
            "transactionType": "P-PURCHASE",
            "securitiesTransacted": 10,
            "securitiesOwned": 20_000,
            "price": 100,
            "reportingName": "Prior Insider",
        },
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FmpInsiderAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence == []
    assert any("No qualifying recent" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_fmp_insider_preserves_current_evidence_without_baseline():
    payload = [
        {
            "transactionDate": "2026-07-11",
            "transactionType": "P-PURCHASE",
            "securitiesTransacted": 10,
            "price": 100,
            "reportingName": "Current Insider",
        }
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FmpInsiderAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].direction == Direction.BULLISH
    assert result.evidence[0].change is None
    assert any("baseline_unavailable" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_fmp_insider_ignores_zero_value_rows_before_cluster_and_planned_state():
    payload = [
        {
            "transactionDate": "2026-07-11",
            "transactionType": "S-SALE",
            "securitiesTransacted": 10,
            "price": 100,
            "reportingName": "Real Seller",
        },
        {
            "transactionDate": "2026-07-10",
            "transactionType": "S-SALE",
            "securitiesTransacted": 0,
            "price": 100,
            "reportingName": "Zero Seller",
            "is10b51": True,
        },
        {
            "transactionDate": "2026-07-09",
            "transactionType": "S-SALE",
            "securitiesTransacted": 5,
            "price": 0,
            "reportingName": "Zero Value Seller",
            "is10b51": True,
        },
        {
            "transactionDate": "2026-07-03",
            "transactionType": "S-SALE",
            "securitiesTransacted": 5,
            "price": 100,
            "reportingName": "Prior Seller",
        },
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FmpInsiderAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    evidence = result.evidence[0]
    assert evidence.signal == "insider_sale_activity"
    assert evidence.confidence == 0.62
    assert len(evidence.raw_signal) == 1


@pytest.mark.asyncio
async def test_fmp_insider_cluster_requires_two_people_in_the_net_direction():
    payload = [
        {
            "transactionDate": "2026-07-11",
            "transactionType": "P-PURCHASE",
            "securitiesTransacted": 20,
            "price": 100,
            "reportingName": "Buyer",
        },
        {
            "transactionDate": "2026-07-10",
            "transactionType": "S-SALE",
            "securitiesTransacted": 10,
            "price": 100,
            "reportingName": "Seller",
        },
        {
            "transactionDate": "2026-07-03",
            "transactionType": "P-PURCHASE",
            "securitiesTransacted": 5,
            "price": 100,
            "reportingName": "Prior Buyer",
        },
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FmpInsiderAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].signal == "insider_purchase_activity"


@pytest.mark.asyncio
async def test_fmp_unplanned_sale_cluster_keeps_cluster_confidence():
    payload = [
        {
            "transactionDate": "2026-07-11",
            "transactionType": "S-SALE",
            "securitiesTransacted": 10,
            "price": 100,
            "reportingName": "Seller One",
        },
        {
            "transactionDate": "2026-07-10",
            "transactionType": "S-SALE",
            "securitiesTransacted": 10,
            "price": 100,
            "reportingName": "Seller Two",
        },
        {
            "transactionDate": "2026-07-09",
            "transactionType": "P-PURCHASE",
            "securitiesTransacted": 1,
            "price": 100,
            "reportingName": "Planned Buyer",
            "is10b51": True,
        },
        {
            "transactionDate": "2026-07-08",
            "transactionType": "S-SALE",
            "securitiesTransacted": 1,
            "price": 100,
            "reportingName": "Planned Seller",
            "is10b51": True,
        },
        {
            "transactionDate": "2026-07-03",
            "transactionType": "S-SALE",
            "securitiesTransacted": 5,
            "price": 100,
            "reportingName": "Prior Seller",
        },
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FmpInsiderAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    evidence = result.evidence[0]
    assert evidence.signal == "insider_sale_cluster"
    assert evidence.confidence == 0.82


@pytest.mark.asyncio
async def test_PT_FMP_TECHNICAL_NORMALIZATION():
    def handler(request):
        kind = request.url.path.rsplit("/", 1)[-1]
        period = int(request.url.params["periodLength"])
        assert request.url.params["timeframe"] == "1day"
        assert request.url.params["from"] == "2026-06-02"
        assert request.url.params["to"] == "2026-07-12"
        assert request.headers["apikey"] == "test-key"
        assert "apikey" not in request.url.params
        return httpx.Response(200, json=_fixture("fmp_technical.json")[f"{kind}_{period}"])

    async with _client(handler) as client:
        result = await FmpTechnicalAdapter("test-key", client=client, clock=lambda: AS_OF).collect(
            "NVDA", 14
        )
    assert {item.signal for item in result.evidence} >= {
        "rsi_recovered_30",
        "price_crossed_above_sma_20",
        "ema_12_crossed_above_26",
    }


@pytest.mark.asyncio
async def test_fmp_technical_fetches_indicators_concurrently(monkeypatch):
    adapter = FmpTechnicalAdapter("test-key", clock=lambda: AS_OF)
    active = 0
    max_active = 0

    async def fake_get(path, params):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)
        active -= 1
        indicator = path.rsplit("/", 1)[-1]
        return _fixture("fmp_technical.json")[f"{indicator}_{params['periodLength']}"]

    monkeypatch.setattr(adapter, "_get", fake_get)

    await adapter.collect("NVDA", 14)

    assert max_active > 1


@pytest.mark.asyncio
async def test_PT_FINNHUB_SOCIAL_AND_LOBBYING_NORMALIZATION():
    def handler(request):
        assert request.headers["X-Finnhub-Token"] == "test-key"
        assert "token" not in request.url.params
        if request.url.path.endswith("social-sentiment"):
            return httpx.Response(200, json=_fixture("finnhub_social.json"))
        return httpx.Response(200, json=_fixture("finnhub_lobbying.json"))

    async with _client(handler) as client:
        social = await FinnhubSocialAdapter("test-key", client=client, clock=lambda: AS_OF).collect(
            "NVDA", 14
        )
        lobbying = await FinnhubLobbyingAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)
    assert social.evidence[0].direction == Direction.BULLISH
    assert str(social.evidence[0].sources[0].url).endswith("/social/current")
    assert lobbying.evidence[0].direction == Direction.NEUTRAL


@pytest.mark.asyncio
async def test_finnhub_social_preserves_current_evidence_without_baseline():
    payload = {
        "reddit": [
            {
                "atTime": "2026-07-11T12:00:00+00:00",
                "mention": 100,
                "score": 0.4,
            }
        ],
        "twitter": [],
    }

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FinnhubSocialAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].direction == Direction.NEUTRAL
    assert result.evidence[0].change is None
    assert any("baseline_unavailable" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_finnhub_social_zero_mentions_have_zero_sentiment_weight():
    payload = {
        "reddit": [
            {
                "atTime": "2026-07-11T12:00:00+00:00",
                "mention": 100,
                "score": 0.2,
            },
            {
                "atTime": "2026-07-10T12:00:00+00:00",
                "mention": 0,
                "score": 100,
            },
            {
                "atTime": "2026-07-03T12:00:00+00:00",
                "mention": 100,
                "score": -0.5,
            },
        ],
        "twitter": [],
    }

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FinnhubSocialAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert "sentiment changed by +0.700" in result.evidence[0].change.description


@pytest.mark.asyncio
async def test_finnhub_social_clamps_sentiment_and_prefers_current_source():
    payload = {
        "reddit": [
            {
                "atTime": "2026-07-03T12:00:00+00:00",
                "mention": 100,
                "score": 0,
                "url": "https://example.com/social/prior-first",
            },
            {
                "atTime": "2026-07-11T12:00:00+00:00",
                "mention": 100,
                "score": 100,
                "url": "https://example.com/social/current-second",
            },
        ],
        "twitter": [],
    }

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FinnhubSocialAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    evidence = result.evidence[0]
    assert "sentiment changed by +1.000" in evidence.change.description
    assert str(evidence.sources[0].url).endswith("/current-second")


@pytest.mark.asyncio
async def test_finnhub_lobbying_preserves_current_evidence_without_baseline():
    payload = {"data": [{"date": "2026-07-11", "url": "https://example.com/lobbying"}]}

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FinnhubLobbyingAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].signal == "lobbying_activity_observation"
    assert result.evidence[0].change is None
    assert any("baseline_unavailable" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_finnhub_lobbying_uses_exact_datetime_window_boundary():
    payload = {
        "data": [
            {"date": "2026-07-06", "url": "https://example.com/lobbying/current"},
            {"date": "2026-07-05", "url": "https://example.com/lobbying/boundary-prior"},
        ]
    }

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FinnhubLobbyingAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].change.current_value == 1
    assert result.evidence[0].change.baseline_value == 1


@pytest.mark.asyncio
async def test_PT_FLOWALGO_NORMALIZATION():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(200, json=_fixture("flowalgo.json"))

    async with _client(handler) as client:
        result = await FlowAlgoAdapter("test-key", client=client, clock=lambda: AS_OF).collect(
            "NVDA", 14
        )
    assert result.evidence[0].direction == Direction.BULLISH
    assert result.evidence[0].change.delta == 1500
    assert "ratio changed from 0.25 to 0.50" in result.evidence[0].change.description
    assert str(result.evidence[0].sources[0].url).endswith("/flowalgo/current")


@pytest.mark.asyncio
async def test_true_flow_preserves_current_evidence_without_baseline():
    payload = [
        {
            "timestamp": "2026-07-11T12:00:00+00:00",
            "symbol": "NVDA",
            "type": "call",
            "premium": 1_000,
        }
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FlowAlgoAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].direction == Direction.BULLISH
    assert result.evidence[0].signal == "call_dominant_flow_observation"
    assert result.evidence[0].change is None
    assert any("baseline_unavailable" in warning for warning in result.warnings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current_side", "current_premium", "prior_side", "prior_premium", "direction", "signal"),
    [
        ("call", 500, "call", 1_000, Direction.BEARISH, "call_flow_decrease"),
        ("put", 500, "put", 1_000, Direction.BULLISH, "put_flow_decrease"),
        ("call", 500, "put", 500, Direction.BULLISH, "call_flow_increase"),
        ("put", 500, "call", 500, Direction.BEARISH, "put_flow_increase"),
    ],
)
async def test_true_flow_direction_tracks_change_from_provider_baseline(
    current_side,
    current_premium,
    prior_side,
    prior_premium,
    direction,
    signal,
):
    payload = [
        {
            "timestamp": "2026-07-11T12:00:00+00:00",
            "symbol": "NVDA",
            "type": current_side,
            "premium": current_premium,
        },
        {
            "timestamp": "2026-07-03T12:00:00+00:00",
            "symbol": "NVDA",
            "type": prior_side,
            "premium": prior_premium,
        },
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FlowAlgoAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].direction == direction
    assert result.evidence[0].signal == signal


@pytest.mark.asyncio
async def test_true_flow_unchanged_directional_premium_is_not_called_balanced():
    payload = [
        {
            "timestamp": "2026-07-11T12:00:00+00:00",
            "symbol": "NVDA",
            "type": "call",
            "premium": 500,
        },
        {
            "timestamp": "2026-07-03T12:00:00+00:00",
            "symbol": "NVDA",
            "type": "call",
            "premium": 500,
        },
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FlowAlgoAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    assert result.evidence[0].direction == Direction.NEUTRAL
    assert result.evidence[0].signal == "directional_flow_unchanged"
    assert result.evidence[0].strength == 0


@pytest.mark.asyncio
async def test_true_flow_strength_and_large_trade_count_follow_baseline_change():
    payload = [
        {
            "timestamp": "2026-07-11T12:00:00+00:00",
            "symbol": "NVDA",
            "type": "call",
            "premium": 500,
            "volume": 100,
            "open_interest": 200,
            "trade_type": "sweep",
        },
        {
            "timestamp": "2026-07-10T12:00:00+00:00",
            "symbol": "NVDA",
            "type": "call",
            "premium": 0,
            "trade_type": "block",
        },
        {
            "timestamp": "2026-07-03T12:00:00+00:00",
            "symbol": "NVDA",
            "type": "call",
            "premium": 510,
            "volume": 50,
            "open_interest": 200,
            "trade_type": "sweep",
        },
    ]

    async with _client(lambda request: httpx.Response(200, json=payload)) as client:
        result = await FlowAlgoAdapter(
            "test-key", client=client, clock=lambda: AS_OF
        ).collect("NVDA", 14)

    evidence = result.evidence[0]
    assert evidence.direction == Direction.BEARISH
    assert evidence.signal == "call_flow_decrease"
    assert evidence.strength == pytest.approx(10 / 510)
    assert "Sweep/block count changed from 1 to 2" in evidence.change.description


@pytest.mark.asyncio
async def test_PT_CHEDDARFLOW_NORMALIZATION():
    def handler(request):
        assert request.headers["X-API-Key"] == "test-key"
        return httpx.Response(200, json=_fixture("cheddarflow.json"))

    async with _client(handler) as client:
        result = await CheddarFlowAdapter("test-key", client=client, clock=lambda: AS_OF).collect(
            "NVDA", 14
        )
    assert result.evidence[0].direction == Direction.BEARISH


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 429])
async def test_PT_PROVIDER_AUTH_AND_RATE_LIMIT_FAIL_CLOSED(status):
    async with _client(lambda request: httpx.Response(status, json={"error": "secret"})) as client:
        adapter = FmpNewsAdapter("test-key", client=client, clock=lambda: AS_OF)
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.collect("NVDA", 14)


@pytest.mark.asyncio
async def test_PT_PROVIDER_MALFORMED_SCHEMA_FAILS_CLOSED():
    async with _client(lambda request: httpx.Response(200, json={"unknown": []})) as client:
        with pytest.raises(ValueError, match="schema"):
            await FmpNewsAdapter("test-key", client=client, clock=lambda: AS_OF).collect("NVDA", 14)
