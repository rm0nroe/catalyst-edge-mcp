"""Frozen provider-neutral ``trained_softmax`` model plumbing."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import Direction, Evidence
from catalyst_edge_mcp.replay.contracts import canonical_json, canonical_jsonl, stable_id
from catalyst_edge_mcp.scorer import CANONICAL_FAMILIES, DeterministicScorer

METHOD = "trained_softmax"
CLASSES = ("bearish", "neutral", "bullish")
L2_GRID = (0.0001, 0.001, 0.01, 0.1)
SCHEMA_VERSION = 1
PROVENANCE_VALUES = {"synthetic_only", "rights_cleared_market"}


@dataclass(frozen=True, slots=True)
class ModelRow:
    evaluation_id: str
    event_group_id: str
    evaluated_at: datetime
    features: tuple[float, ...]
    label: str
    deterministic_class: str
    observation_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    artifact_id: str
    feature_names: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    weights: tuple[tuple[float, ...], ...]
    biases: tuple[float, ...]
    temperature: float
    selected_l2: float
    frozen_hashes: dict[str, str]
    report: dict[str, object]
    provenance: str
    stage_b_passed: bool
    promotion: dict[str, object] | None

    def probabilities(self, features: tuple[float, ...]) -> tuple[float, ...]:
        if len(features) != len(self.feature_names):
            raise ValueError("feature vector does not match the frozen schema")
        values = _standardize(features, self.means, self.scales)
        return _softmax(_logits(values, self.weights, self.biases), self.temperature)

    def predict(self, features: tuple[float, ...]) -> dict[str, object]:
        probabilities = self.probabilities(features)
        bearish, _, bullish = probabilities
        return {
            "score": max(0, min(100, round(50 + 50 * (bullish - bearish)))),
            "direction": CLASSES[max(range(3), key=probabilities.__getitem__)],
            "confidence": round(max(probabilities), 12),
            "probabilities": dict(zip(CLASSES, probabilities, strict=True)),
        }


def feature_names() -> tuple[str, ...]:
    return tuple(
        f"{family}.{name}"
        for family in sorted(CANONICAL_FAMILIES)
        for name in ("signal", "count", "quality", "missing")
    )


def extract_features(
    evidence: list[Evidence], *, as_of: datetime, lookback_days: int
) -> tuple[float, ...]:
    if lookback_days < 1:
        raise ValueError("lookback_days must be positive")
    if as_of.tzinfo is None or any(item.timestamp.tzinfo is None for item in evidence):
        raise ValueError("feature timestamps must include an offset")
    if any(item.timestamp > as_of for item in evidence):
        raise ValueError("feature input contains future evidence")
    output: list[float] = []
    signs = {Direction.BEARISH: -1.0, Direction.NEUTRAL: 0.0, Direction.BULLISH: 1.0}
    for family in sorted(CANONICAL_FAMILIES):
        items = [item for item in evidence if item.family == family]
        signal = 0.0
        weighted_quality = 0.0
        total_strength = 0.0
        for item in items:
            age_days = (as_of - item.timestamp).total_seconds() / 86_400
            recency = max(0.0, 1.0 - age_days / lookback_days)
            signal += (
                signs[item.direction]
                * item.strength
                * item.confidence
                * item.source_quality
                * recency
            )
            weighted_quality += item.strength * item.confidence * item.source_quality
            total_strength += item.strength
        output.extend(
            (
                max(-1.0, min(1.0, signal)),
                min(len(items), 3) / 3,
                weighted_quality / total_strength if total_strength else 0.0,
                0.0 if items else 1.0,
            )
        )
    return tuple(output)


def materialize_model_rows(data: bytes, *, lookback_days: int = 14) -> tuple[list[ModelRow], bytes]:
    """Build identity-free training rows from canonical replay records."""
    if lookback_days < 1:
        raise ValueError("lookback_days must be positive")
    records: list[dict[str, object]] = []
    try:
        for line in data.splitlines():
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("replay records must be objects")
            records.append(record)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("replay dataset is invalid JSONL") from exc
    if not records:
        raise ValueError("replay dataset is empty")
    identifiers = [str(record.get("record_id", "")) for record in records]
    if any(not identifier for identifier in identifiers) or len(set(identifiers)) != len(
        identifiers
    ):
        raise ValueError("replay records require unique IDs")

    observations = {
        str(record["record_id"]): record
        for record in records
        if record.get("record_type") == "observation"
    }
    evaluations = {
        str(record["record_id"]): record
        for record in records
        if record.get("record_type") == "evaluation"
    }
    labels = {
        str(record["evaluation_id"]): record
        for record in records
        if record.get("record_type") == "label"
    }
    excluded = {
        str(record["evaluation_id"])
        for record in records
        if record.get("record_type") == "exclusion"
    }
    scorer = DeterministicScorer()
    rows: list[ModelRow] = []
    for evaluation_id, evaluation in sorted(evaluations.items()):
        if evaluation_id in excluded:
            continue
        label = labels.get(evaluation_id)
        if label is None:
            raise ValueError(f"evaluation {evaluation_id} has no label or exclusion")
        observation_ids = tuple(sorted(str(value) for value in evaluation["observation_ids"]))
        if not observation_ids:
            raise ValueError(f"evaluation {evaluation_id} has no observations")
        try:
            selected = [observations[identifier] for identifier in observation_ids]
        except KeyError as exc:
            raise ValueError(f"evaluation {evaluation_id} references unknown observation") from exc
        evaluated_at = _model_timestamp(evaluation["evaluation_at"])
        evidence = []
        for observation in selected:
            snapshot = observation.get("evidence_snapshot")
            if not isinstance(snapshot, dict):
                raise ValueError(f"observation {observation['record_id']} lacks evidence snapshot")
            timestamp = _model_timestamp(snapshot["timestamp"])
            if timestamp > evaluated_at:
                raise ValueError(f"evaluation {evaluation_id} contains future evidence")
            evidence.append(
                Evidence(
                    family=str(snapshot["family"]),
                    signal=str(observation["record_id"]),
                    direction=Direction(str(snapshot["direction"])),
                    strength=float(snapshot["strength"]),
                    confidence=float(snapshot["confidence"]),
                    source_quality=float(snapshot["source_quality"]),
                    timestamp=timestamp,
                )
            )
        features = extract_features(evidence, as_of=evaluated_at, lookback_days=lookback_days)
        deterministic_class = scorer.score(
            evidence,
            as_of=evaluated_at,
            lookback_days=lookback_days,
            expected_families=CANONICAL_FAMILIES,
        ).edge.direction.value
        label_class = str(label["class"])
        if label_class not in CLASSES:
            raise ValueError(f"evaluation {evaluation_id} has invalid label class")
        row = ModelRow(
            evaluation_id=evaluation_id,
            event_group_id=str(evaluation["event_group_id"]),
            evaluated_at=evaluated_at,
            features=features,
            label=label_class,
            deterministic_class=deterministic_class,
            observation_ids=observation_ids,
        )
        rows.append(row)
    _validate_rows(rows)
    return rows, canonical_model_rows(rows)


def canonical_model_rows(rows: list[ModelRow]) -> bytes:
    _validate_rows(rows)
    return canonical_jsonl(
        [
            {
                "record_type": "model_row",
                "record_id": stable_id("cem", row.evaluation_id, *row.observation_ids),
                "evaluation_id": row.evaluation_id,
                "event_group_id": row.event_group_id,
                "evaluated_at": row.evaluated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "observation_ids": list(row.observation_ids),
                "features": _rounded(row.features),
                "label": row.label,
                "deterministic_class": row.deterministic_class,
            }
            for row in rows
        ]
    )


def fit(
    rows: list[ModelRow],
    *,
    dataset_sha256: str,
    config_sha256: str,
    code_sha256: str,
    exclusions_sha256: str,
    provenance: str,
    epochs: int = 400,
    learning_rate: float = 0.05,
) -> bytes:
    """Fit/select on 2018-2023 only; untouched-test rows are rejected."""
    for name, value in {
        "dataset_sha256": dataset_sha256,
        "config_sha256": config_sha256,
        "code_sha256": code_sha256,
        "exclusions_sha256": exclusions_sha256,
    }.items():
        _sha256(value, name)
    if provenance not in PROVENANCE_VALUES:
        raise ValueError("model provenance is invalid")
    if epochs < 1 or learning_rate <= 0:
        raise ValueError("training hyperparameters are invalid")
    _validate_rows(rows)
    training = sorted(
        (row for row in rows if 2018 <= _year(row) <= 2021),
        key=lambda row: (row.evaluated_at, row.evaluation_id),
    )
    validation = sorted(
        (row for row in rows if 2022 <= _year(row) <= 2023),
        key=lambda row: (row.evaluated_at, row.evaluation_id),
    )
    if len(training) + len(validation) != len(rows):
        raise ValueError("fit accepts only frozen training and validation rows")
    _require_classes(training, "training")
    _require_classes(validation, "validation")

    candidates: list[dict[str, object]] = []
    fitted: dict[float, tuple[tuple[float, ...], ...] | tuple[float, ...] | float] = {}
    for l2 in L2_GRID:
        calibration_logits: list[tuple[float, ...]] = []
        calibration_labels: list[int] = []
        walk_forward: list[tuple[int, list[tuple[float, ...]], list[ModelRow]]] = []
        for year in range(2019, 2022):
            earlier = [row for row in training if _year(row) < year]
            current = [row for row in training if _year(row) == year]
            _require_classes(earlier, f"walk-forward training before {year}")
            if not current:
                raise ValueError(f"training rows are missing walk-forward year {year}")
            means, scales, weights, biases = _fit(
                earlier, l2=l2, epochs=epochs, learning_rate=learning_rate
            )
            year_logits = [
                _logits(_standardize(row.features, means, scales), weights, biases)
                for row in current
            ]
            calibration_logits.extend(year_logits)
            calibration_labels.extend(CLASSES.index(row.label) for row in current)
            walk_forward.append((year, year_logits, current))
        temperature = _fit_temperature(calibration_logits, calibration_labels)
        means, scales, weights, biases = _fit(
            training, l2=l2, epochs=epochs, learning_rate=learning_rate
        )
        probabilities = [
            _softmax(
                _logits(_standardize(row.features, means, scales), weights, biases),
                temperature,
            )
            for row in validation
        ]
        metrics = _metrics(
            probabilities,
            [CLASSES.index(row.label) for row in validation],
            provenance=provenance,
        )
        walk_forward_report = []
        for year, year_logits, current in walk_forward:
            year_labels = [CLASSES.index(row.label) for row in current]
            calibrated = _metrics(
                [_softmax(values, temperature) for values in year_logits],
                year_labels,
                provenance=provenance,
            )
            deterministic = _metrics(
                [
                    tuple(
                        1.0 if index == CLASSES.index(row.deterministic_class) else 0.0
                        for index in range(3)
                    )
                    for row in current
                ],
                year_labels,
                probability_floor=1e-12,
                provenance=provenance,
            )
            walk_forward_report.append(
                {
                    "provenance": provenance,
                    "year": year,
                    "calibrated": calibrated,
                    "deterministic_v1": deterministic,
                    "improved": calibrated["log_loss"] < deterministic["log_loss"],
                }
            )
        candidates.append(
            {
                "provenance": provenance,
                "l2": l2,
                "temperature": temperature,
                "validation": metrics,
                "walk_forward": walk_forward_report,
                "calibration_improvement_folds": sum(
                    bool(item["improved"]) for item in walk_forward_report
                ),
            }
        )
        fitted[l2] = (means, scales, weights, biases, temperature)

    selected = min(
        candidates,
        key=lambda item: (
            item["validation"]["log_loss"],
            item["validation"]["brier"],
            -item["l2"],
        ),
    )
    selected_l2 = float(selected["l2"])
    means, scales, weights, biases, temperature = fitted[selected_l2]
    labels = [CLASSES.index(row.label) for row in validation]
    class_counts = [sum(row.label == name for row in training) for name in CLASSES]
    prior = tuple(count / len(training) for count in class_counts)
    majority = max(range(len(CLASSES)), key=class_counts.__getitem__)
    baselines = {
        "majority_class": _metrics(
            [tuple(1.0 if index == majority else 0.0 for index in range(3))] * len(validation),
            labels,
            probability_floor=1e-12,
            provenance=provenance,
        ),
        "training_class_prior": _metrics([prior] * len(validation), labels, provenance=provenance),
        "deterministic_v1": _metrics(
            [
                tuple(
                    1.0 if index == CLASSES.index(row.deterministic_class) else 0.0
                    for index in range(3)
                )
                for row in validation
            ],
            labels,
            probability_floor=1e-12,
            provenance=provenance,
        ),
    }
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "method": METHOD,
        "provenance": provenance,
        "classes": list(CLASSES),
        "feature_names": list(feature_names()),
        "means": _rounded(means),
        "scales": _rounded(scales),
        "weights": [_rounded(row) for row in weights],
        "biases": _rounded(biases),
        "temperature": round(float(temperature), 12),
        "selected_l2": selected_l2,
        "frozen_hashes": {
            "dataset_sha256": dataset_sha256,
            "config_sha256": config_sha256,
            "code_sha256": code_sha256,
            "exclusions_sha256": exclusions_sha256,
        },
        "report": {
            "provenance": provenance,
            "training_rows": len(training),
            "validation_rows": len(validation),
            "candidates": candidates,
            "baselines": baselines,
            "training_class_prior": dict(zip(CLASSES, prior, strict=True)),
            "epochs": epochs,
            "learning_rate": learning_rate,
            "untouched_test_opened": False,
        },
        "stage_b_passed": False,
        "promotion": None,
    }
    payload["artifact_id"] = _artifact_id(payload)
    return canonical_json(payload)


def load_artifact(
    data: bytes,
    *,
    require_stage_b: bool = True,
    expected_hashes: dict[str, str] | None = None,
) -> ModelArtifact:
    try:
        payload = json.loads(data)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("trained model artifact is invalid JSON") from exc
    required = {
        "schema_version",
        "artifact_id",
        "method",
        "provenance",
        "classes",
        "feature_names",
        "means",
        "scales",
        "weights",
        "biases",
        "temperature",
        "selected_l2",
        "frozen_hashes",
        "report",
        "stage_b_passed",
        "promotion",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("trained model artifact has an invalid top-level schema")
    if payload["schema_version"] != SCHEMA_VERSION or payload["method"] != METHOD:
        raise ValueError("trained model artifact schema or method is unsupported")
    if payload["provenance"] not in PROVENANCE_VALUES:
        raise ValueError("trained model artifact provenance is invalid")
    if tuple(payload["classes"]) != CLASSES or tuple(payload["feature_names"]) != feature_names():
        raise ValueError("trained model artifact class or feature schema is invalid")
    if payload["artifact_id"] != _artifact_id(
        {key: value for key, value in payload.items() if key != "artifact_id"}
    ):
        raise ValueError("trained model artifact ID does not match its contents")
    width = len(feature_names())
    means = _finite_vector(payload["means"], width, "means")
    scales = _finite_vector(payload["scales"], width, "scales")
    weights = tuple(_finite_vector(row, width, "weights") for row in payload["weights"])
    biases = _finite_vector(payload["biases"], len(CLASSES), "biases")
    if len(weights) != len(CLASSES) or any(scale < 1e-6 for scale in scales):
        raise ValueError("trained model artifact dimensions or scales are invalid")
    temperature = float(payload["temperature"])
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("trained model artifact temperature is invalid")
    selected_l2 = float(payload["selected_l2"])
    if selected_l2 not in L2_GRID:
        raise ValueError("trained model artifact regularization is invalid")
    hashes = payload["frozen_hashes"]
    if not isinstance(hashes, dict) or set(hashes) != {
        "dataset_sha256",
        "config_sha256",
        "code_sha256",
        "exclusions_sha256",
    }:
        raise ValueError("trained model artifact frozen hashes are invalid")
    for name, value in hashes.items():
        _sha256(value, name)
    if not isinstance(payload["report"], dict):
        raise ValueError("trained model artifact report is invalid")
    if not isinstance(payload["stage_b_passed"], bool):
        raise ValueError("trained model artifact Stage B status is invalid")
    promotion = payload["promotion"]
    if promotion is not None and not isinstance(promotion, dict):
        raise ValueError("trained model artifact promotion record is invalid")
    if payload["stage_b_passed"] is True and (
        payload["provenance"] != "rights_cleared_market" or promotion is None
    ):
        raise ValueError("trained model artifact lacks evidence-bound promotion")
    if payload["stage_b_passed"] is True:
        _validate_promotion(payload, promotion, hashes)
    elif promotion is not None:
        raise ValueError("trained model artifact promotion status is inconsistent")
    if payload["stage_b_passed"] is not True and require_stage_b:
        raise ValueError("trained model artifact has not passed Stage B")
    if require_stage_b and expected_hashes is None:
        raise ValueError("trained model artifact requires expected frozen hashes")
    if expected_hashes is not None and hashes != expected_hashes:
        raise ValueError("trained model artifact frozen hashes do not match")
    return ModelArtifact(
        payload["artifact_id"],
        tuple(payload["feature_names"]),
        means,
        scales,
        weights,
        biases,
        temperature,
        selected_l2,
        hashes,
        payload["report"],
        payload["provenance"],
        payload["stage_b_passed"] is True,
        promotion,
    )


def _validate_promotion(
    payload: dict[str, object], promotion: dict[str, object], hashes: dict[str, str]
) -> None:
    required = {
        "schema_version",
        "record_type",
        "record_id",
        "source_artifact_id",
        "source_artifact_sha256",
        "audit_record_id",
        "evaluation_record_id",
        "frozen_hashes",
    }
    if (
        set(promotion) != required
        or promotion.get("schema_version") != 1
        or promotion.get("record_type") != "artifact_promotion"
        or promotion.get("frozen_hashes") != hashes
    ):
        raise ValueError("trained model artifact promotion record is invalid")

    source_body = {key: value for key, value in payload.items() if key != "artifact_id"}
    source_body["stage_b_passed"] = False
    source_body["promotion"] = None
    source_artifact_id = _artifact_id(source_body)
    source_payload = {**source_body, "artifact_id": source_artifact_id}
    if (
        promotion["source_artifact_id"] != source_artifact_id
        or promotion["source_artifact_sha256"]
        != hashlib.sha256(canonical_json(source_payload)).hexdigest()
    ):
        raise ValueError("trained model artifact promotion source does not match")
    for name, prefix in (
        ("audit_record_id", "ceaudit"),
        ("evaluation_record_id", "cetv"),
    ):
        value = promotion[name]
        if not isinstance(value, str) or not value.startswith(f"{prefix}_"):
            raise ValueError("trained model artifact promotion evidence ID is invalid")
        _sha256(value.removeprefix(f"{prefix}_"), name)
    body = {key: value for key, value in promotion.items() if key != "record_id"}
    expected_id = stable_id("ceprom", hashlib.sha256(canonical_json(body)).hexdigest())
    if promotion["record_id"] != expected_id:
        raise ValueError("trained model artifact promotion record ID does not match")


def _validate_rows(rows: list[ModelRow]) -> None:
    if not rows:
        raise ValueError("model rows are empty")
    width = len(feature_names())
    groups: dict[str, set[str]] = {}
    evaluations: set[str] = set()
    for row in rows:
        if row.evaluated_at.tzinfo is None or row.evaluated_at.utcoffset() is None:
            raise ValueError("model row timestamps must include an offset")
        if not row.evaluation_id or not row.event_group_id:
            raise ValueError("model row IDs must be non-empty")
        if row.evaluation_id in evaluations:
            raise ValueError("model rows contain duplicate evaluation IDs")
        evaluations.add(row.evaluation_id)
        _finite_vector(list(row.features), width, "row features")
        if row.label not in CLASSES or row.deterministic_class not in CLASSES:
            raise ValueError("model row class is invalid")
        split = _row_split(row)
        groups.setdefault(row.event_group_id, set()).add(split)
    crossing = sorted(group for group, splits in groups.items() if len(splits) > 1)
    if crossing:
        raise ValueError(f"model event groups cross folds: {', '.join(crossing)}")


def _fit(
    rows: list[ModelRow], *, l2: float, epochs: int, learning_rate: float
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[tuple[float, ...], ...], tuple[float, ...]]:
    width = len(feature_names())
    means = tuple(sum(row.features[index] for row in rows) / len(rows) for index in range(width))
    scales = tuple(
        max(
            math.sqrt(sum((row.features[index] - means[index]) ** 2 for row in rows) / len(rows)),
            1e-6,
        )
        for index in range(width)
    )
    values = [_standardize(row.features, means, scales) for row in rows]
    labels = [CLASSES.index(row.label) for row in rows]
    weights = [[0.0] * width for _ in CLASSES]
    biases = [0.0] * len(CLASSES)
    for _ in range(epochs):
        weight_gradients = [[0.0] * width for _ in CLASSES]
        bias_gradients = [0.0] * len(CLASSES)
        for vector, label in zip(values, labels, strict=True):
            probabilities = _softmax(_logits(vector, weights, biases))
            for class_index in range(len(CLASSES)):
                error = probabilities[class_index] - (class_index == label)
                bias_gradients[class_index] += error
                for feature_index, value in enumerate(vector):
                    weight_gradients[class_index][feature_index] += error * value
        for class_index in range(len(CLASSES)):
            biases[class_index] -= learning_rate * bias_gradients[class_index] / len(rows)
            for feature_index in range(width):
                gradient = weight_gradients[class_index][feature_index] / len(rows)
                gradient += l2 * weights[class_index][feature_index]
                weights[class_index][feature_index] -= learning_rate * gradient
    return means, scales, tuple(tuple(row) for row in weights), tuple(biases)


def _fit_temperature(logits: list[tuple[float, ...]], labels: list[int]) -> float:
    log_temperature = 0.0
    for _ in range(250):
        temperature = math.exp(log_temperature)
        gradient = 0.0
        for values, label in zip(logits, labels, strict=True):
            probabilities = _softmax(values, temperature)
            expected = sum(
                probability * value
                for probability, value in zip(probabilities, values, strict=True)
            )
            gradient += (values[label] - expected) / temperature
        log_temperature -= 0.02 * gradient / len(labels)
        log_temperature = max(math.log(0.05), min(math.log(20.0), log_temperature))
    return round(math.exp(log_temperature), 12)


def _metrics(
    probabilities: list[tuple[float, ...]],
    labels: list[int],
    *,
    provenance: str,
    probability_floor: float = 1e-15,
) -> dict[str, object]:
    predictions = [max(range(3), key=row.__getitem__) for row in probabilities]
    log_loss = -sum(
        math.log(max(row[label], probability_floor))
        for row, label in zip(probabilities, labels, strict=True)
    ) / len(labels)
    brier = sum(
        sum((row[index] - (index == label)) ** 2 for index in range(3))
        for row, label in zip(probabilities, labels, strict=True)
    ) / len(labels)
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(10)]
    for row, label, prediction in zip(probabilities, labels, predictions, strict=True):
        confidence = max(row)
        bins[min(9, int(confidence * 10))].append((confidence, prediction == label))
    ece = sum(
        len(bucket)
        / len(labels)
        * abs(
            sum(confidence for confidence, _ in bucket) / len(bucket)
            - sum(correct for _, correct in bucket) / len(bucket)
        )
        for bucket in bins
        if bucket
    )
    return {
        "provenance": provenance,
        "log_loss": round(log_loss, 12),
        "brier": round(brier, 12),
        "ece": round(ece, 12),
        **_classification_metrics(predictions, labels),
    }


def _classification_metrics(predictions: list[int], labels: list[int]) -> dict[str, object]:
    confusion = [[0] * 3 for _ in range(3)]
    for actual, predicted in zip(labels, predictions, strict=True):
        confusion[actual][predicted] += 1
    return {
        "accuracy": round(
            sum(a == p for a, p in zip(labels, predictions, strict=True)) / len(labels),
            12,
        ),
        "class_counts": {name: labels.count(index) for index, name in enumerate(CLASSES)},
        "confusion_matrix": confusion,
    }


def _require_classes(rows: list[ModelRow], split: str) -> None:
    if {row.label for row in rows} != set(CLASSES):
        raise ValueError(f"{split} must contain bearish, neutral, and bullish rows")


def _year(row: ModelRow) -> int:
    return row.evaluated_at.astimezone(UTC).year


def _row_split(row: ModelRow) -> str:
    year = _year(row)
    if 2018 <= year <= 2021:
        return "training"
    if 2022 <= year <= 2023:
        return "validation"
    if 2024 <= year <= 2025:
        return "untouched_test"
    return "outside_frozen_period"


def _model_timestamp(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("model row timestamps must include an offset")
    return parsed.astimezone(UTC)


def _standardize(
    values: tuple[float, ...], means: tuple[float, ...], scales: tuple[float, ...]
) -> tuple[float, ...]:
    return tuple(
        (value - mean) / scale for value, mean, scale in zip(values, means, scales, strict=True)
    )


def _logits(values, weights, biases) -> tuple[float, ...]:
    return tuple(
        bias + sum(weight * value for weight, value in zip(row, values, strict=True))
        for row, bias in zip(weights, biases, strict=True)
    )


def _softmax(logits, temperature: float = 1.0) -> tuple[float, ...]:
    scaled = [value / temperature for value in logits]
    peak = max(scaled)
    exponentials = [math.exp(value - peak) for value in scaled]
    total = sum(exponentials)
    return tuple(value / total for value in exponentials)


def _artifact_id(payload: dict[str, object]) -> str:
    return f"mdl_{hashlib.sha256(canonical_json(payload)).hexdigest()}"


def _rounded(values) -> list[float]:
    return [round(float(value), 12) for value in values]


def _finite_vector(value: object, length: int, name: str) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"trained model artifact {name} dimensions are invalid")
    output = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in output):
        raise ValueError(f"trained model artifact {name} must be finite")
    return output


def _sha256(value: object, name: str) -> None:
    text = str(value)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
