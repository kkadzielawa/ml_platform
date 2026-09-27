from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from components.evaluate_classic import (
    EVALUATION_GATE_FAILURE_EXIT_CODE,
    EvaluationError,
    EvaluationGateFailure,
    EvaluationRequest,
    EvaluationThresholds,
    run_evaluation_component,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DATA = REPO_ROOT / "examples/sklearn_baseline/data"
TEST_PATH = BASELINE_DATA / "test.csv"
METADATA_PATH = BASELINE_DATA / "metadata.json"
RUN_ID = "run-20260927t140000z-00000001"


class LookupModel:
    """Tiny dependency-free model double with the sklearn prediction surface."""

    classes_ = [0, 1]

    def __init__(self, labels: dict[tuple[object, ...], int]) -> None:
        self.labels = labels

    def predict(self, rows: list[list[object]]) -> list[int]:
        return [self.labels[tuple(row)] for row in rows]

    def predict_proba(self, rows: list[list[object]]) -> list[list[float]]:
        return [[0.01, 0.99] if self.labels[tuple(row)] else [0.99, 0.01] for row in rows]


class BadModel:
    classes_ = [0, 1]

    def predict(self, rows: list[list[object]]) -> list[int]:
        return [0 for _ in rows]

    def predict_proba(self, rows: list[list[object]]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in rows]


def request(tmp_path: Path) -> EvaluationRequest:
    candidate = tmp_path / "candidate.joblib"
    candidate.write_bytes(b"candidate-artifact")
    return EvaluationRequest(
        run_id=RUN_ID,
        test_path=TEST_PATH,
        metadata_path=METADATA_PATH,
        candidate_model_path=candidate,
        report_path=tmp_path / "evaluation.json",
        dataset_name="synthetic-housing-sale-classifier",
        dataset_version="v0001",
        dataset_revision="lakefs-commit-c0ffee1234567890",
        model_name="housing-sale-candidate",
        model_version="0.1.0",
        code_version="git:0123456789abcdef0123456789abcdef01234567",
    )


def fixture_model() -> LookupModel:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    feature_columns = metadata["schema"]["feature_columns"]
    target_column = metadata["schema"]["target_column"]
    categorical = {"property_type", "market_temperature"}
    with TEST_PATH.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    labels = {
        tuple(row[column] if column in categorical else float(row[column]) for column in feature_columns): int(row[target_column])
        for row in rows
    }
    return LookupModel(labels)


def test_invalid_request_fails_before_report_publication(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.joblib"
    candidate.write_bytes(b"candidate-artifact")
    invalid = EvaluationRequest(
        **{
            **request(tmp_path).__dict__,
            "test_path": tmp_path / "missing.csv",
        }
    )

    with pytest.raises(EvaluationError, match="test_path does not exist"):
        run_evaluation_component(invalid)

    assert not invalid.report_path.exists()
    assert not (tmp_path / "missing.csv").exists()


def test_seeded_bad_candidate_fails_gate_but_publishes_evidence(tmp_path: Path) -> None:
    evaluation_request = request(tmp_path)

    with pytest.raises(EvaluationGateFailure) as raised:
        run_evaluation_component(evaluation_request, model_loader=lambda _: BadModel())

    assert raised.value.exit_code == EVALUATION_GATE_FAILURE_EXIT_CODE
    report = json.loads(evaluation_request.report_path.read_text(encoding="utf-8"))
    assert report["decision"] == "fail"
    assert report["status"] == "failed"
    assert "candidate_accuracy" in report["failures"]
    assert "improvement_over_baseline" in report["failures"]
    assert report["dataset"]["revision"] == "lakefs-commit-c0ffee1234567890"
    assert report["model"]["candidate"]["version"] == "0.1.0"
    assert report["thresholds"]["version"] == "evaluation-thresholds/v1"
    assert "listing-0001" not in evaluation_request.report_path.read_text(encoding="utf-8")


def test_candidate_passes_with_slices_calibration_and_latency_evidence(tmp_path: Path) -> None:
    evaluation_request = request(tmp_path)
    result = run_evaluation_component(evaluation_request, model_loader=lambda _: fixture_model())

    assert result.success is True
    assert result.report["decision"] == "pass"
    assert result.report["metrics"]["candidate_accuracy"] == pytest.approx(1.0)
    assert result.report["metrics"]["improvement"] > 0.1
    assert result.report["metrics"]["candidate_brier_score"] < 0.25
    assert result.report["latency"]["fixture"] == "single-row-candidate-predict"
    assert result.report["latency"]["samples"] == 30
    assert {item["column"] for item in result.report["slices"]} == {
        "property_type",
        "market_temperature",
    }
    assert all(item["passed"] for item in result.report["checks"])


def test_evaluation_contract_is_versioned_and_matches_report_shape() -> None:
    contract = json.loads((REPO_ROOT / "contracts/evaluation.schema.json").read_text(encoding="utf-8"))

    assert contract["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert contract["properties"]["schema_version"]["const"] == "1.0.0"
    assert set(contract["required"]) >= {
        "dataset",
        "model",
        "code",
        "thresholds",
        "metrics",
        "slices",
        "latency",
        "checks",
        "failures",
    }
