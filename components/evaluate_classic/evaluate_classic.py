"""Evaluate a candidate classic model against a fixed baseline.

The component deliberately keeps the gate independent from MLflow, model
registration, and deployment.  It consumes immutable local artifacts and
publishes one aggregate JSON report before returning or raising for the gate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_RUN_ID = re.compile(r"^run-\d{8}t\d{6}z-[0-9a-f]{8}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

EVALUATION_GATE_FAILURE_EXIT_CODE = 42


class EvaluationError(ValueError):
    """Raised when an evaluation declaration or artifact is invalid."""


class EvaluationGateFailure(RuntimeError):
    """Raised after a failed evaluation report has been durably published."""

    exit_code = EVALUATION_GATE_FAILURE_EXIT_CODE


@dataclass(frozen=True)
class EvaluationThresholds:
    """Versioned, explicit acceptance thresholds for a classic model."""

    version: str = "evaluation-thresholds/v1"
    minimum_accuracy: float = 0.67
    minimum_improvement: float = 0.10
    maximum_brier_score: float = 0.25
    maximum_latency_p95_ms: float = 100.0
    minimum_slice_accuracy: float | None = None

    def validate(self) -> None:
        if not self.version or any(character.isspace() for character in self.version):
            raise EvaluationError("threshold version must be a non-empty identifier")
        for name, value in (
            ("minimum_accuracy", self.minimum_accuracy),
            ("minimum_improvement", self.minimum_improvement),
        ):
            if not 0.0 <= value <= 1.0:
                raise EvaluationError(f"{name} must be between 0 and 1")
        if not 0.0 <= self.maximum_brier_score <= 1.0:
            raise EvaluationError("maximum_brier_score must be between 0 and 1")
        if self.maximum_latency_p95_ms <= 0:
            raise EvaluationError("maximum_latency_p95_ms must be positive")
        if self.minimum_slice_accuracy is not None and not 0.0 <= self.minimum_slice_accuracy <= 1.0:
            raise EvaluationError("minimum_slice_accuracy must be between 0 and 1")

    def as_dict(self) -> dict[str, float | str | None]:
        return {
            "version": self.version,
            "minimum_accuracy": self.minimum_accuracy,
            "minimum_improvement": self.minimum_improvement,
            "maximum_brier_score": self.maximum_brier_score,
            "maximum_latency_p95_ms": self.maximum_latency_p95_ms,
            "minimum_slice_accuracy": self.minimum_slice_accuracy,
        }


@dataclass(frozen=True)
class EvaluationRequest:
    """Immutable inputs and identity for one offline evaluation."""

    run_id: str
    test_path: Path
    metadata_path: Path
    candidate_model_path: Path
    report_path: Path
    dataset_name: str
    dataset_version: str
    dataset_revision: str
    model_name: str
    model_version: str
    code_version: str
    baseline_model_path: Path | None = None
    thresholds: EvaluationThresholds = field(default_factory=EvaluationThresholds)
    slice_columns: tuple[str, ...] = ("property_type", "market_temperature")
    latency_samples: int = 30
    latency_warmup: int = 5

    def validate(self) -> None:
        if not _RUN_ID.fullmatch(self.run_id):
            raise EvaluationError("run_id must match run-YYYYMMDDtHHMMSSz-<8 lowercase hex>")
        for name, path in {
            "test_path": self.test_path,
            "metadata_path": self.metadata_path,
            "candidate_model_path": self.candidate_model_path,
        }.items():
            if not Path(path).is_file():
                raise EvaluationError(f"{name} does not exist: {path}")
        if self.baseline_model_path is not None and not Path(self.baseline_model_path).is_file():
            raise EvaluationError(f"baseline_model_path does not exist: {self.baseline_model_path}")
        for name, value in {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "dataset_revision": self.dataset_revision,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "code_version": self.code_version,
        }.items():
            if not value or any(character.isspace() for character in value):
                raise EvaluationError(f"{name} must be a non-empty identifier without whitespace")
        if not self.slice_columns:
            raise EvaluationError("at least one slice column is required")
        if any(not column or any(character.isspace() for character in column) for column in self.slice_columns):
            raise EvaluationError("slice column names must be non-empty and contain no whitespace")
        if self.latency_samples < 1 or self.latency_warmup < 0:
            raise EvaluationError("latency sample counts must be non-negative, with at least one sample")
        if Path(self.report_path).exists():
            raise EvaluationError(f"report already exists: {self.report_path}")
        self.thresholds.validate()


@dataclass(frozen=True)
class EvaluationResult:
    """Published aggregate evidence and gate outcome."""

    success: bool
    report: dict[str, Any]
    report_path: Path


def run_evaluation_component(
    request: EvaluationRequest,
    *,
    model_loader: Callable[[Path], Any] | None = None,
) -> EvaluationResult:
    """Evaluate, publish evidence, and raise only after a failed gate.

    ``model_loader`` is injectable for dependency-free tests.  Production use
    defaults to joblib and therefore imports it only when evaluation runs.
    """

    request.validate()
    rows, metadata = _load_test_rows(Path(request.test_path), Path(request.metadata_path))
    if not rows:
        raise EvaluationError("test dataset contains no rows")
    feature_columns = _required_list(metadata, "schema", "feature_columns")
    target_column = _required_string(metadata, "schema", "target_column")
    for column in request.slice_columns:
        if column not in feature_columns and column not in rows[0]:
            raise EvaluationError(f"slice column is not present in test dataset: {column}")
    x_rows, y_true = _features_and_targets(rows, feature_columns, target_column)
    candidate = (model_loader or _load_joblib_model)(Path(request.candidate_model_path))
    baseline = (
        (model_loader or _load_joblib_model)(Path(request.baseline_model_path))
        if request.baseline_model_path is not None
        else None
    )

    candidate_predictions = _predict(candidate, x_rows)
    baseline_predictions = (
        _predict(baseline, x_rows)
        if baseline is not None
        else _majority_predictions(metadata, len(y_true))
    )
    candidate_probabilities = _positive_probabilities(candidate, x_rows)
    baseline_probabilities = (
        _positive_probabilities(baseline, x_rows)
        if baseline is not None
        else _majority_probabilities(metadata, len(y_true))
    )

    candidate_accuracy = _accuracy(y_true, candidate_predictions)
    baseline_accuracy = _accuracy(y_true, baseline_predictions)
    improvement = candidate_accuracy - baseline_accuracy
    candidate_brier = _brier_score(y_true, candidate_probabilities)
    baseline_brier = _brier_score(y_true, baseline_probabilities)
    slices = _evaluate_slices(
        rows,
        y_true,
        candidate_predictions,
        baseline_predictions,
        request.slice_columns,
        request.thresholds,
    )
    latency = _measure_latency(
        candidate,
        x_rows[0],
        request.latency_warmup,
        request.latency_samples,
        request.thresholds.maximum_latency_p95_ms,
    )

    checks = [
        _check("candidate_accuracy", candidate_accuracy, ">=", request.thresholds.minimum_accuracy, candidate_accuracy >= request.thresholds.minimum_accuracy),
        _check("improvement_over_baseline", improvement, ">=", request.thresholds.minimum_improvement, improvement >= request.thresholds.minimum_improvement),
        _check(
            "candidate_brier_score",
            candidate_brier,
            "<=",
            request.thresholds.maximum_brier_score,
            candidate_brier is not None and candidate_brier <= request.thresholds.maximum_brier_score,
        ),
        _check("latency_p95_ms", latency["p95_ms"], "<=", request.thresholds.maximum_latency_p95_ms, latency["passed"]),
    ]
    if request.thresholds.minimum_slice_accuracy is not None:
        checks.append(
            _check(
                "minimum_slice_accuracy",
                min(item["candidate_accuracy"] for item in slices),
                ">=",
                request.thresholds.minimum_slice_accuracy,
                all(item["candidate_accuracy"] >= request.thresholds.minimum_slice_accuracy for item in slices),
            )
        )
    failures = [check["name"] for check in checks if not check["passed"]]
    candidate_checksum = _sha256_file(Path(request.candidate_model_path))
    if not _SHA256.fullmatch(candidate_checksum):
        raise AssertionError("internal checksum format error")
    report = {
        "schema_version": "1.0.0",
        "component": "offline-evaluation",
        "evaluation_id": f"{request.run_id}-evaluation",
        "run_id": request.run_id,
        "status": "passed" if not failures else "failed",
        "decision": "pass" if not failures else "fail",
        "dataset": {
            "name": request.dataset_name,
            "version": request.dataset_version,
            "revision": request.dataset_revision,
            "test_rows": len(rows),
            "test_csv_sha256": _sha256_file(Path(request.test_path)),
            "metadata_sha256": _sha256_file(Path(request.metadata_path)),
        },
        "model": {
            "candidate": {
                "name": request.model_name,
                "version": request.model_version,
                "artifact_sha256": candidate_checksum,
            },
            "baseline": {
                "type": "artifact" if baseline is not None else "majority-class",
                "version": "artifact" if baseline is not None else "metadata.expected_baseline",
                "artifact_sha256": _sha256_file(Path(request.baseline_model_path)) if baseline is not None else None,
            },
        },
        "code": {"version": request.code_version},
        "thresholds": request.thresholds.as_dict(),
        "metrics": {
            "candidate_accuracy": candidate_accuracy,
            "baseline_accuracy": baseline_accuracy,
            "improvement": improvement,
            "candidate_brier_score": candidate_brier,
            "baseline_brier_score": baseline_brier,
        },
        "slices": slices,
        "latency": latency,
        "checks": checks,
        "failures": failures,
    }
    published_path = write_evaluation_report(report, Path(request.report_path))
    result = EvaluationResult(success=not failures, report=report, report_path=published_path)
    if failures:
        raise EvaluationGateFailure(
            f"evaluation gate failed ({', '.join(failures)}); report published at {published_path}"
        )
    return result


def write_evaluation_report(report: Mapping[str, Any], report_path: Path) -> Path:
    """Atomically publish a report containing aggregate evidence only."""

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=report_path.parent,
            prefix=f".{report_path.name}.",
            suffix=".partial",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            json.dump(report, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        Path(temporary_path).replace(report_path)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
    return report_path


def _load_test_rows(test_path: Path, metadata_path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    try:
        rows = _read_csv(test_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as error:
        raise EvaluationError("test or metadata artifact is not readable JSON/CSV") from error
    if not isinstance(metadata, dict):
        raise EvaluationError("metadata artifact must contain an object")
    return rows, metadata


def _features_and_targets(
    rows: Sequence[Mapping[str, str]], feature_columns: Sequence[str], target_column: str
) -> tuple[list[list[Any]], list[int]]:
    missing = [column for column in [*feature_columns, target_column] if column not in rows[0]]
    if missing:
        raise EvaluationError(f"test dataset is missing columns: {', '.join(missing)}")
    categorical = {"property_type", "market_temperature"}
    features: list[list[Any]] = []
    targets: list[int] = []
    for row in rows:
        try:
            features.append([
                row[column] if column in categorical else float(row[column])
                for column in feature_columns
            ])
            targets.append(int(row[target_column]))
        except (KeyError, TypeError, ValueError) as error:
            raise EvaluationError("test dataset contains a malformed feature or target") from error
    return features, targets


def _predict(model: Any, rows: Sequence[Sequence[Any]]) -> list[int]:
    if model is None or not hasattr(model, "predict"):
        raise EvaluationError("candidate model must provide predict()")
    try:
        predictions = model.predict(rows)
        return [int(value) for value in predictions]
    except (TypeError, ValueError, AttributeError) as error:
        raise EvaluationError("candidate model could not predict the fixed test data") from error


def _positive_probabilities(model: Any, rows: Sequence[Sequence[Any]]) -> list[float] | None:
    if model is None or not hasattr(model, "predict_proba"):
        return None
    try:
        probabilities = model.predict_proba(rows)
        classes = list(getattr(model, "classes_", [0, 1]))
        positive_index = classes.index(1) if 1 in classes else len(classes) - 1
        values = [float(row[positive_index]) for row in probabilities]
    except (TypeError, ValueError, AttributeError, IndexError) as error:
        raise EvaluationError("model predict_proba() returned an invalid result") from error
    if any(not 0.0 <= value <= 1.0 for value in values):
        raise EvaluationError("model probabilities must be between 0 and 1")
    return values


def _majority_class(metadata: Mapping[str, Any]) -> int:
    try:
        return int(metadata["expected_baseline"]["train_majority_class"])
    except (KeyError, TypeError, ValueError) as error:
        raise EvaluationError("metadata.expected_baseline.train_majority_class is required") from error


def _majority_predictions(metadata: Mapping[str, Any], count: int) -> list[int]:
    return [_majority_class(metadata)] * count


def _majority_probabilities(metadata: Mapping[str, Any], count: int) -> list[float]:
    return [float(_majority_class(metadata))] * count


def _accuracy(actual: Sequence[int], predicted: Sequence[int]) -> float:
    if len(actual) != len(predicted) or not actual:
        raise EvaluationError("prediction count does not match the test dataset")
    return sum(left == right for left, right in zip(actual, predicted, strict=True)) / len(actual)


def _brier_score(actual: Sequence[int], probabilities: Sequence[float] | None) -> float | None:
    if probabilities is None:
        return None
    if len(actual) != len(probabilities):
        raise EvaluationError("probability count does not match the test dataset")
    return sum((probability - target) ** 2 for target, probability in zip(actual, probabilities, strict=True)) / len(actual)


def _evaluate_slices(
    rows: Sequence[Mapping[str, str]],
    actual: Sequence[int],
    candidate: Sequence[int],
    baseline: Sequence[int],
    slice_columns: Sequence[str],
    thresholds: EvaluationThresholds,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for column in slice_columns:
        groups: dict[str, list[int]] = {}
        for index, row in enumerate(rows):
            groups.setdefault(str(row[column]), []).append(index)
        for value in sorted(groups):
            indexes = groups[value]
            candidate_accuracy = _accuracy([actual[i] for i in indexes], [candidate[i] for i in indexes])
            baseline_accuracy = _accuracy([actual[i] for i in indexes], [baseline[i] for i in indexes])
            minimum = thresholds.minimum_slice_accuracy
            results.append(
                {
                    "column": column,
                    "value": value,
                    "rows": len(indexes),
                    "candidate_accuracy": candidate_accuracy,
                    "baseline_accuracy": baseline_accuracy,
                    "improvement": candidate_accuracy - baseline_accuracy,
                    "passed": minimum is None or candidate_accuracy >= minimum,
                }
            )
    return results


def _measure_latency(model: Any, row: Sequence[Any], warmup: int, samples: int, threshold: float) -> dict[str, Any]:
    if not hasattr(model, "predict"):
        raise EvaluationError("candidate model must provide predict() for latency measurement")
    for _ in range(warmup):
        model.predict([row])
    durations: list[float] = []
    for _ in range(samples):
        started = time.perf_counter_ns()
        model.predict([row])
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    ordered = sorted(durations)
    p95_index = min(len(ordered) - 1, max(0, math.ceil(0.95 * len(ordered)) - 1))
    p50_index = min(len(ordered) - 1, max(0, math.ceil(0.50 * len(ordered)) - 1))
    p95 = ordered[p95_index]
    return {
        "fixture": "single-row-candidate-predict",
        "warmup_samples": warmup,
        "samples": samples,
        "p50_ms": ordered[p50_index],
        "p95_ms": p95,
        "max_ms": ordered[-1],
        "threshold_p95_ms": threshold,
        "passed": p95 <= threshold,
    }


def _check(name: str, observed: float | None, operator: str, threshold: float, passed: bool) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "operator": operator,
        "threshold": threshold,
        "passed": passed,
    }


def _required_list(payload: Mapping[str, Any], section: str, key: str) -> list[str]:
    try:
        value = payload[section][key]
    except (KeyError, TypeError) as error:
        raise EvaluationError(f"metadata.{section}.{key} is required") from error
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise EvaluationError(f"metadata.{section}.{key} must be a non-empty string list")
    return value


def _required_string(payload: Mapping[str, Any], section: str, key: str) -> str:
    try:
        value = payload[section][key]
    except (KeyError, TypeError) as error:
        raise EvaluationError(f"metadata.{section}.{key} is required") from error
    if not isinstance(value, str) or not value:
        raise EvaluationError(f"metadata.{section}.{key} must be a non-empty string")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _load_joblib_model(path: Path) -> Any:
    try:
        import joblib
    except ImportError as error:
        raise EvaluationError("joblib is required to load a candidate model") from error
    return joblib.load(path)


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def main(argv: list[str] | None = None) -> int:
    """Evaluate a joblib model against the fixed CSV test fixture."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--candidate-model", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--code-version", required=True)
    parser.add_argument("--minimum-accuracy", type=float, default=0.67)
    parser.add_argument("--minimum-improvement", type=float, default=0.10)
    parser.add_argument("--maximum-brier-score", type=float, default=0.25)
    parser.add_argument("--maximum-latency-p95-ms", type=float, default=100.0)
    arguments = parser.parse_args(argv)
    request = EvaluationRequest(
        run_id=arguments.run_id,
        test_path=arguments.test,
        metadata_path=arguments.metadata,
        candidate_model_path=arguments.candidate_model,
        report_path=arguments.report,
        dataset_name=arguments.dataset_name,
        dataset_version=arguments.dataset_version,
        dataset_revision=arguments.dataset_revision,
        model_name=arguments.model_name,
        model_version=arguments.model_version,
        code_version=arguments.code_version,
        thresholds=EvaluationThresholds(
            minimum_accuracy=arguments.minimum_accuracy,
            minimum_improvement=arguments.minimum_improvement,
            maximum_brier_score=arguments.maximum_brier_score,
            maximum_latency_p95_ms=arguments.maximum_latency_p95_ms,
        ),
    )
    try:
        run_evaluation_component(request)
    except EvaluationGateFailure as error:
        print(str(error))
        return error.exit_code
    return 0
