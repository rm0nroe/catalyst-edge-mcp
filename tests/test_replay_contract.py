import json
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.replay.build import replay_bundle, write_bundle
from catalyst_edge_mcp.replay.contracts import (
    build_dataset,
    observation_ids,
)


def _spec():
    sessions = [
        datetime(2021, 12, 1, 14, 30, tzinfo=UTC) + timedelta(days=index) for index in range(10)
    ]
    observation = {
        "source_id": "licensed_fixture",
        "security_id": "sec_aapl",
        "stable_record_id": "record_1",
        "version_sha256": "a" * 64,
        "event_group_id": "event_1",
        "accepted_or_published_at": "2021-12-01T12:00:00Z",
        "historically_available_at": "2021-12-01T12:05:00Z",
        "reconstructed_at": "2026-08-07T12:00:00Z",
        "availability_proof_type": "provider_point_in_time_record",
        "availability_proof_reference": "fixture:record_1",
        "evidence_snapshot": {
            "family": "filings_news",
            "direction": "bullish",
            "strength": 0.8,
            "confidence": 0.75,
            "source_quality": 0.9,
            "timestamp": "2021-12-01T12:00:00Z",
        },
    }
    spec = {
        "schema_version": 1,
        "provenance": "rights_cleared_market",
        "code_sha256": "b" * 64,
        "config_sha256": "c" * 64,
        "rights": [
            {
                "source_id": "licensed_fixture",
                "agreement_id": "fixture_agreement",
                "training_allowed": True,
                "artifact_distribution_allowed": True,
                "aggregate_reporting_allowed": True,
                "post_termination_artifact_allowed": True,
                "raw_deletion_required": True,
                "rights_text_sha256": "d" * 64,
            }
        ],
        "calendar": [session.isoformat() for session in sessions],
        "observations": [observation],
        "cases": [],
        "prices": [],
        "actions": [
            {
                "source_id": "licensed_fixture",
                "security_id": "sec_aapl",
                "stable_record_id": "action_1",
                "version_sha256": "e" * 64,
                "effective_at": sessions[2].isoformat(),
                "action_type": "split",
                "ratio": "4.0000000000",
            }
        ],
        "terminal_outcomes": [
            {
                "source_id": "licensed_fixture",
                "security_id": "sec_aapl",
                "stable_record_id": "terminal_1",
                "version_sha256": "1" * 64,
                "effective_at": sessions[3].isoformat(),
                "status": "acquired",
                "total_return_factor": "1.0500000000",
            }
        ],
    }
    evaluation_at = datetime(2021, 12, 1, 13, 0, tzinfo=UTC)
    spec["cases"] = [
        {
            "security_id": "sec_aapl",
            "event_group_id": "event_1",
            "evaluation_at": evaluation_at.isoformat(),
            "observation_refs": [f"licensed_fixture:record_1:{'a' * 64}"],
        }
    ]
    for security_id, entry, exit_value in (("sec_aapl", "1", "1.05"), ("SPY", "1", "1.01")):
        for index, session in enumerate(sessions[:5]):
            factor = entry if index == 0 else exit_value if index == 4 else "1"
            spec["prices"].append(
                {
                    "source_id": "licensed_fixture",
                    "security_id": security_id,
                    "stable_record_id": f"{security_id}_{index}",
                    "version_sha256": "f" * 64,
                    "session_open_at": session.isoformat(),
                    "open_total_return_factor": entry if index == 0 else factor,
                    "close_total_return_factor": factor,
                }
            )
    return spec


def test_replay_build_is_deterministic_rights_gated_and_byte_reproducible(tmp_path):
    spec = _spec()
    version, first, manifest = build_dataset(spec)
    reversed_spec = deepcopy(spec)
    for key in (
        "rights",
        "calendar",
        "observations",
        "cases",
        "prices",
        "actions",
        "terminal_outcomes",
    ):
        reversed_spec[key].reverse()
    assert build_dataset(reversed_spec) == (version, first, manifest)
    label = next(
        json.loads(line) for line in first.splitlines() if b'"record_type":"label"' in line
    )
    assert label["class"] == "bullish"
    assert label["spy_relative_total_return"] == "0.0400000000"
    assert label["terminal_status"] == "acquired"
    assert observation_ids(spec["observations"][0])[1] in first.decode()
    for record_type in ("action", "price", "rights", "terminal_outcome"):
        assert f'"record_type":"{record_type}"' in first.decode()

    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    assert write_bundle(spec_path, tmp_path)["dataset_version"] == version
    assert replay_bundle(version, tmp_path) == manifest

    spec["rights"][0]["artifact_distribution_allowed"] = False
    with pytest.raises(ValueError, match="lacks required model/replay rights"):
        build_dataset(spec)

    crossing = _spec()
    crossing["cases"].append(
        {
            **crossing["cases"][0],
            "evaluation_at": "2024-01-02T13:00:00+00:00",
        }
    )
    with pytest.raises(ValueError, match="event groups cross folds"):
        build_dataset(crossing)

    duplicate = _spec()
    duplicate["actions"].append(deepcopy(duplicate["actions"][0]))
    with pytest.raises(ValueError, match="duplicate identities"):
        build_dataset(duplicate)

    embargoed = _spec()
    shift = timedelta(days=33)
    embargoed["calendar"] = [
        (datetime.fromisoformat(value) + shift).isoformat() for value in embargoed["calendar"]
    ]
    for row, fields in (
        (embargoed["observations"][0], ("accepted_or_published_at", "historically_available_at")),
        (embargoed["cases"][0], ("evaluation_at",)),
        (embargoed["actions"][0], ("effective_at",)),
        (embargoed["terminal_outcomes"][0], ("effective_at",)),
    ):
        for field in fields:
            row[field] = (
                datetime.fromisoformat(row[field].replace("Z", "+00:00")) + shift
            ).isoformat()
    for row in embargoed["prices"]:
        row["session_open_at"] = (
            datetime.fromisoformat(row["session_open_at"]) + shift
        ).isoformat()
    _, embargoed_bytes, _ = build_dataset(embargoed)
    assert '"reason":"fold_embargo"' in embargoed_bytes.decode()
