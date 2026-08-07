"""Reproduce the provider-neutral replay-contract validation in technical specification §17.9."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "tests"
    / "fixtures"
    / "validation"
    / "real_catalyst_cases.json"
)


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _observation_key(case: dict[str, Any]) -> str:
    identity = "\x1f".join(("sec", f"CIK{case['cik']}", case["accession"]))
    return f"cek_{hashlib.sha256(identity.encode()).hexdigest()}"


def _observation_id(case: dict[str, Any]) -> str:
    version_identity = "\x1f".join((_observation_key(case), case["accession"]))
    return f"ceo_{hashlib.sha256(version_identity.encode()).hexdigest()}"


def _eligible(record: dict[str, str], evaluation_at: datetime) -> bool:
    accepted = datetime.fromisoformat(
        record["accepted_or_published_at"].replace("Z", "+00:00")
    )
    available = datetime.fromisoformat(
        record["historically_available_at"].replace("Z", "+00:00")
    )
    return max(accepted, available) <= evaluation_at


def canonical_bytes(cases: list[dict[str, Any]]) -> bytes:
    records = [
        {
            "accepted_or_published_at": _timestamp(case["accepted_at"]),
            "availability_proof_type": "sec_acceptance",
            "event_type": case["expected_event_type"],
            "historically_available_at": _timestamp(case["accepted_at"]),
            "issuer_cik": f"CIK{case['cik']}",
            "observation_id": _observation_id(case),
            "observation_key": _observation_key(case),
            "ticker": case["ticker"],
        }
        for case in cases
    ]
    records.sort(key=lambda item: item["observation_id"])
    lines = (
        json.dumps(
            record,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        for record in records
    )
    return ("\n".join(lines) + "\n").encode()


def validate() -> dict[str, object]:
    cases = json.loads(FIXTURE_PATH.read_text())["cases"]
    first = canonical_bytes(cases)
    second = canonical_bytes(list(reversed(cases)))
    visibility_checks = 0
    normalized_records = [json.loads(line) for line in first.decode().splitlines()]
    for record in normalized_records:
        accepted = datetime.fromisoformat(
            record["accepted_or_published_at"].replace("Z", "+00:00")
        )
        assert not _eligible(record, accepted - timedelta(microseconds=1))
        assert _eligible(record, accepted)
        visibility_checks += 2
    observation_ids = {_observation_id(case) for case in cases}
    assert len(observation_ids) == len(cases)
    assert first == second
    return {
        "canonical_sha256": hashlib.sha256(first).hexdigest(),
        "order_independent_bytes": True,
        "serialized_bytes": len(first),
        "target_cases": len(cases),
        "ticker_cik_pairs": len({(case["ticker"], case["cik"]) for case in cases}),
        "unique_observation_ids": len(observation_ids),
        "visibility_boundary_assertions": visibility_checks,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
