import json
from copy import deepcopy
from datetime import datetime

import pytest

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import Direction
from catalyst_edge_mcp.replay.contracts import build_dataset
from catalyst_edge_mcp.replay.model import (
    CLASSES,
    L2_GRID,
    ModelRow,
    extract_features,
    feature_names,
    fit,
    load_artifact,
    materialize_model_rows,
)
from tests.conftest import make_evidence
from tests.test_replay_contract import _spec


def _rows():
    rows = []
    directions = (Direction.BEARISH, Direction.NEUTRAL, Direction.BULLISH)
    for year in range(2018, 2024):
        for class_index, label in enumerate(CLASSES):
            for sample in range(2):
                evaluated_at = datetime(year, 6, 10 + class_index * 2 + sample, 16, tzinfo=UTC)
                evidence = make_evidence(
                    "filings_news",
                    f"{label}_{year}_{sample}",
                    direction=directions[class_index],
                    timestamp=evaluated_at,
                )
                rows.append(
                    ModelRow(
                        evaluation_id=f"evaluation_{year}_{label}_{sample}",
                        event_group_id=f"event_{year}_{label}_{sample}",
                        evaluated_at=evaluated_at,
                        features=extract_features([evidence], as_of=evaluated_at, lookback_days=14),
                        label=label,
                        deterministic_class=label,
                    )
                )
    return rows


def test_trained_softmax_is_deterministic_complete_and_fail_closed():
    hashes = {
        "dataset_sha256": "a" * 64,
        "config_sha256": "b" * 64,
        "code_sha256": "c" * 64,
        "exclusions_sha256": "d" * 64,
    }
    first = fit(_rows(), **hashes, provenance="synthetic_only", epochs=30)
    assert fit(_rows(), **hashes, provenance="synthetic_only", epochs=30) == first

    payload = json.loads(first)
    assert payload["method"] == "trained_softmax"
    assert payload["provenance"] == "synthetic_only"
    assert payload["classes"] == list(CLASSES)
    assert payload["selected_l2"] in L2_GRID
    assert len(payload["report"]["candidates"]) == len(L2_GRID)
    assert set(payload["report"]["baselines"]) == {
        "majority_class",
        "training_class_prior",
        "deterministic_v1",
    }
    assert payload["report"]["untouched_test_opened"] is False
    assert payload["stage_b_passed"] is False

    artifact = load_artifact(first, require_stage_b=False)
    probabilities = artifact.probabilities(_rows()[0].features)
    assert sum(probabilities) == pytest.approx(1)
    assert all(0 <= value <= 1 for value in probabilities)
    prediction = artifact.predict(_rows()[-1].features)
    assert 0 <= prediction["score"] <= 100
    assert prediction["direction"] in CLASSES
    with pytest.raises(ValueError, match="has not passed Stage B"):
        load_artifact(first)

    payload["biases"][0] += 1
    with pytest.raises(ValueError, match="ID does not match"):
        load_artifact(json.dumps(payload).encode(), require_stage_b=False)


def test_feature_contract_has_no_identity_and_rejects_future_evidence():
    names = feature_names()
    assert len(names) == 20
    assert not any(
        identity in name
        for name in names
        for identity in ("ticker", "issuer", "security", "sector", "regime")
    )
    as_of = datetime(2023, 1, 1, tzinfo=UTC)
    future = make_evidence("filings_news", "future", timestamp=datetime(2023, 1, 2, tzinfo=UTC))
    with pytest.raises(ValueError, match="future evidence"):
        extract_features([future], as_of=as_of, lookback_days=14)


def test_fit_rejects_untouched_test_rows():
    rows = _rows()
    rows.append(
        ModelRow(
            evaluation_id="untouched",
            event_group_id="untouched",
            evaluated_at=datetime(2024, 1, 10, tzinfo=UTC),
            features=rows[0].features,
            label="bearish",
            deterministic_class="bearish",
        )
    )
    with pytest.raises(ValueError, match="only frozen training and validation"):
        fit(
            rows,
            dataset_sha256="a" * 64,
            config_sha256="b" * 64,
            code_sha256="c" * 64,
            exclusions_sha256="d" * 64,
            provenance="synthetic_only",
            epochs=1,
        )


def test_replay_rows_are_canonical_identity_free_and_correction_aware():
    spec = _spec()
    correction = deepcopy(spec["observations"][0])
    correction["version_sha256"] = "2" * 64
    correction["accepted_or_published_at"] = "2021-12-01T12:10:00Z"
    correction["historically_available_at"] = "2021-12-01T12:10:00Z"
    correction["evidence_snapshot"]["timestamp"] = "2021-12-01T12:10:00Z"
    spec["observations"].append(correction)
    spec["cases"][0]["observation_refs"].append(
        f"licensed_fixture:record_1:{correction['version_sha256']}"
    )
    _, dataset, _ = build_dataset(spec)
    rows, row_bytes = materialize_model_rows(dataset)
    shuffled = b"\n".join(reversed(dataset.splitlines())) + b"\n"
    assert materialize_model_rows(shuffled)[1] == row_bytes
    assert len(rows) == 1
    assert len(rows[0].observation_ids) == 1
    assert rows[0].features[1] == pytest.approx(1 / 3)
    assert b"sec_aapl" not in row_bytes
    assert b"licensed_fixture" not in row_bytes


def test_replay_rejects_future_snapshot_and_fit_rejects_materialized_test_rows():
    future = _spec()
    future["observations"][0]["evidence_snapshot"]["timestamp"] = "2021-12-02T12:00:00Z"
    with pytest.raises(ValueError, match="future evidence"):
        build_dataset(future)

    spec = _spec()
    shift = datetime(2024, 6, 1, tzinfo=UTC) - datetime(2021, 12, 1, tzinfo=UTC)
    spec["calendar"] = [
        (datetime.fromisoformat(value) + shift).isoformat() for value in spec["calendar"]
    ]
    spec["calendar"] = [
        datetime(2024, 1, day, 14, 30, tzinfo=UTC).isoformat() for day in range(2, 7)
    ] + spec["calendar"]
    for row, fields in (
        (
            spec["observations"][0],
            (
                "accepted_or_published_at",
                "historically_available_at",
                "reconstructed_at",
            ),
        ),
        (spec["cases"][0], ("evaluation_at",)),
        (spec["actions"][0], ("effective_at",)),
        (spec["terminal_outcomes"][0], ("effective_at",)),
    ):
        for field in fields:
            row[field] = (
                datetime.fromisoformat(row[field].replace("Z", "+00:00")) + shift
            ).isoformat()
    snapshot = spec["observations"][0]["evidence_snapshot"]
    snapshot["timestamp"] = (
        datetime.fromisoformat(snapshot["timestamp"].replace("Z", "+00:00")) + shift
    ).isoformat()
    for row in spec["prices"]:
        row["session_open_at"] = (
            datetime.fromisoformat(row["session_open_at"]) + shift
        ).isoformat()
    _, dataset, _ = build_dataset(spec)
    rows, _ = materialize_model_rows(dataset)
    with pytest.raises(ValueError, match="only frozen training and validation"):
        fit(
            rows,
            dataset_sha256="a" * 64,
            config_sha256="b" * 64,
            code_sha256="c" * 64,
            exclusions_sha256="d" * 64,
            provenance="synthetic_only",
            epochs=1,
        )

    rows = _rows()
    rows[0] = ModelRow(
        evaluation_id="too_early",
        event_group_id="too_early",
        evaluated_at=datetime(2017, 1, 10, tzinfo=UTC),
        features=rows[0].features,
        label="bearish",
        deterministic_class="bearish",
    )
    with pytest.raises(ValueError, match="only frozen training and validation"):
        fit(
            rows,
            dataset_sha256="a" * 64,
            config_sha256="b" * 64,
            code_sha256="c" * 64,
            exclusions_sha256="d" * 64,
            provenance="synthetic_only",
            epochs=1,
        )
