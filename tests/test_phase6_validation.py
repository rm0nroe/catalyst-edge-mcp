import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from catalyst_edge_mcp.adapters import StaticAdapter
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import (
    AdapterResult,
    Direction,
    Evidence,
    PolicyDecision,
    Source,
    SourceStatus,
    ToolInput,
)
from catalyst_edge_mcp.service import CatalystService
from catalyst_edge_mcp.smoke import readiness_report

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "validation" / "phase6_historical_cases.json"


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _source_name(source_id: str) -> str:
    return {
        "sec": "SEC EDGAR",
        "issuer_feed": "Reviewed issuer release",
        "gdelt": "GDELT publisher metadata",
        "bluesky": "Bluesky attention",
        "finnhub": "Finnhub social sentiment",
        "flowalgo": "flowalgo",
        "yfinance": "yfinance chain snapshot",
        "authorized_options_fixture": "Authorized options fixture",
    }.get(source_id, source_id)


def build_case(case):
    as_of = _timestamp(case["as_of"])
    adapters = []
    for adapter_data in case["adapters"]:
        family = adapter_data["family"]
        provider = adapter_data["provider"]
        evidence = []
        for item in adapter_data.get("evidence", []):
            source_id = item["source_id"]
            source_policy = item.get("source_policy")
            timestamp = _timestamp(item["timestamp"]) if item.get("timestamp") else (
                as_of - timedelta(days=1)
            )
            evidence.append(
                Evidence(
                    family=family,
                    signal=item["signal"],
                    direction=Direction(item["direction"]),
                    strength=item.get("strength", 0.9),
                    confidence=item.get("confidence", 0.9),
                    source_quality=item.get("source_quality", 1.0),
                    timestamp=timestamp,
                    sources=[
                        Source(
                            name=_source_name(source_id),
                            source_id=source_id,
                            observed_at=timestamp,
                            policy_decision=(
                                PolicyDecision(source_policy) if source_policy else None
                            ),
                        )
                    ],
                )
            )
        result = AdapterResult(
            family=family,
            provider=provider,
            evidence=evidence,
            warnings=adapter_data.get("warnings", []),
            status=(SourceStatus(adapter_data["status"]) if adapter_data.get("status") else None),
            policy_decision=(
                PolicyDecision(adapter_data["policy_decision"])
                if adapter_data.get("policy_decision")
                else None
            ),
            degraded=adapter_data.get("degraded", False),
            collected_at=as_of,
        )
        adapters.append(StaticAdapter(family, result, provider=provider))
    return as_of, adapters


async def run_case(case):
    as_of, adapters = build_case(case)
    response = await CatalystService(adapters, clock=lambda: as_of).evaluate(
        ToolInput(ticker=case["ticker"])
    )
    readiness = readiness_report(response, adapters)
    source_ids = sorted(
        {
            source.source_id
            for item in response.evidence
            for source in item.sources
            if source.source_id
        }
    )
    return response, readiness, source_ids


def _cases():
    return json.loads(FIXTURE_PATH.read_text())["cases"]


def test_PHASE6_CORPUS_HAS_20_TO_30_DATED_SANITIZED_CASES():
    fixture = json.loads(FIXTURE_PATH.read_text())

    assert 20 <= len(fixture["cases"]) <= 30
    assert "synthetic" in fixture["description"].lower()
    assert len({case["id"] for case in fixture["cases"]}) == len(fixture["cases"])
    assert all(case["as_of"].endswith("Z") for case in fixture["cases"])


@pytest.mark.asyncio
@pytest.mark.parametrize("case", _cases(), ids=lambda case: case["id"])
async def test_FX_PHASE6_HISTORICAL_PRODUCT_CASES(case):
    response, readiness, source_ids = await run_case(case)
    expected = case["expected"]

    assert response.edge.direction.value == expected["direction"]
    assert response.data_quality.missing_families == expected["missing"]
    assert response.data_quality.stale_families == expected["stale"]
    assert source_ids == expected["source_ids"]
    assert readiness["sec_provenance"] is expected["sec_provenance"]
    assert readiness["launch_ready"] is expected["launch_ready"]


@pytest.mark.asyncio
async def test_FX_SENTIMENT_MODEL_DISABLED_GETS_NO_SCORE_COVERAGE_OR_READINESS():
    case = next(item for item in _cases() if item["id"] == "23_sentiment_candidate_disabled")

    response, readiness, source_ids = await run_case(case)

    assert response.edge.score == 50
    assert "social" in response.data_quality.missing_families
    assert source_ids == ["sec"]
    assert readiness["launch_ready"] is False
