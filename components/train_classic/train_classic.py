"""Train the classic sklearn baseline and log artifacts to MLflow without registering."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_RUN_ID = re.compile(r"^run-\d{8}t\d{6}z-[0-9a-f]{8}$")


class TrainingError(ValueError):
    """Raised when training inputs or configuration are invalid."""


@dataclass(frozen=True)
class TrainingRequest:
    """Immutable training inputs and MLflow destination."""

    run_id: str
    train_path: Path
    test_path: Path
    metadata_path: Path
    dataset_revision: str
    output_dir: Path
    tracking_uri: str
    experiment_name: str
    run_name: str
    model_name: str
    model_parameters: Mapping[str, Any] = field(
        default_factory=lambda: {
            "n_estimators": 80,
            "max_depth": 1,
            "learning_rate": 0.08,
            "random_state": 20260808,
        }
    )
    minimum_accuracy: float = 0.67

    def validate(self) -> None:
        if not _RUN_ID.fullmatch(self.run_id):
            raise TrainingError("run_id must match run-YYYYMMDDtHHMMSSz-<8 lowercase hex>")
        for name, path in {
            "train_path": self.train_path,
            "test_path": self.test_path,
            "metadata_path": self.metadata_path,
        }.items():
            if not Path(path).is_file():
                raise TrainingError(f"{name} does not exist: {path}")
        if not self.dataset_revision or any(character.isspace() for character in self.dataset_revision):
            raise TrainingError("dataset_revision must be a non-empty immutable identifier")
        if not self.tracking_uri or any(character.isspace() for character in self.tracking_uri):
            raise TrainingError("tracking_uri must be a non-empty URI")
        if not self.experiment_name or not self.run_name or not self.model_name:
            raise TrainingError("experiment, run, and model names must be non-empty")
        if not 0.0 <= self.minimum_accuracy <= 1.0:
            raise TrainingError("minimum_accuracy must be between 0 and 1")
        try:
            json.dumps(self.model_parameters, sort_keys=True)
        except (TypeError, ValueError) as error:
            raise TrainingError("model_parameters must be JSON-serializable") from error
        if Path(self.output_dir).exists():
            raise TrainingError(f"output directory already exists: {self.output_dir}")


@dataclass(frozen=True)
class ModelFit:
    """In-memory result of deterministic model fitting."""

    model: Any
    accuracy: float
    feature_columns: list[str]
    x_test: list[list[Any]]
    dataset_metadata: dict[str, Any]


@dataclass(frozen=True)
class TrainingResult:
    """Published model artifacts and MLflow run identity."""

    run_id: str
    mlflow_run_id: str
    accuracy: float
    minimum_accuracy: float
    model_uri: str
    output_dir: Path
    manifest_path: Path
    registered: bool = False


def fit_baseline_model(request: TrainingRequest) -> ModelFit:
    """Fit the fixed-seed sklearn baseline from immutable input files."""

    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    train_rows = _read_csv(Path(request.train_path))
    test_rows = _read_csv(Path(request.test_path))
    dataset_metadata = json.loads(Path(request.metadata_path).read_text(encoding="utf-8"))
    feature_columns = dataset_metadata["schema"]["feature_columns"]
    target_column = dataset_metadata["schema"]["target_column"]
    categorical_columns = ["property_type", "market_temperature"]
    numeric_columns = [column for column in feature_columns if column not in categorical_columns]
    x_train, y_train = _split_features_target(train_rows, feature_columns, categorical_columns, target_column)
    x_test, y_test = _split_features_target(test_rows, feature_columns, categorical_columns, target_column)
    categorical_indexes = [feature_columns.index(column) for column in categorical_columns]
    numeric_indexes = [feature_columns.index(column) for column in numeric_columns]
    model = Pipeline(
        [
            (
                "preprocess",
                ColumnTransformer(
                    transformers=[
                        ("numeric", StandardScaler(), numeric_indexes),
                        ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_indexes),
                    ]
                ),
            ),
            ("classifier", GradientBoostingClassifier(**dict(request.model_parameters))),
        ]
    )
    model.fit(x_train, y_train)
    accuracy = float(accuracy_score(y_test, model.predict(x_test)))
    return ModelFit(
        model=model,
        accuracy=accuracy,
        feature_columns=feature_columns,
        x_test=x_test,
        dataset_metadata=dataset_metadata,
    )


def run_training_component(request: TrainingRequest) -> TrainingResult:
    """Fit, publish artifacts to MLflow, and write a local run manifest.

    This component intentionally never supplies ``registered_model_name`` to
    MLflow. Registration is owned by the later model-registration component.
    """

    request.validate()
    output_dir = Path(request.output_dir).resolve()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        fit = fit_baseline_model(request)
        metric_gate_passed = fit.accuracy >= request.minimum_accuracy
        model_path = staging_dir / "model.joblib"
        metrics_path = staging_dir / "metrics.json"
        signature_path = staging_dir / "signature.json"
        manifest_path = staging_dir / "run-manifest.json"

        import joblib

        joblib.dump(fit.model, model_path)
        metrics = {
            "accuracy": fit.accuracy,
            "minimum_accuracy": request.minimum_accuracy,
            "metric_gate_passed": metric_gate_passed,
            "registered": False,
        }
        _write_json(metrics_path, metrics)

        mlflow = _load_mlflow()
        mlflow.set_tracking_uri(request.tracking_uri)
        client = mlflow.tracking.MlflowClient(tracking_uri=request.tracking_uri)
        experiment_id = _ensure_experiment(client, request.experiment_name)
        with mlflow.start_run(experiment_id=experiment_id, run_name=request.run_name) as active_run:
            mlflow_run_id = active_run.info.run_id
            mlflow.log_params({f"model.{key}": value for key, value in request.model_parameters.items()})
            mlflow.log_param("dataset_revision", request.dataset_revision)
            mlflow.log_metric("accuracy", fit.accuracy)
            mlflow.log_metric("minimum_accuracy", request.minimum_accuracy)
            mlflow.log_artifact(metrics_path)

            signature = mlflow.models.infer_signature(fit.x_test, fit.model.predict(fit.x_test))
            _write_json(signature_path, signature.to_dict())
            mlflow.log_artifact(signature_path)
            mlflow.log_artifact(model_path, artifact_path="model-source")
            mlflow.sklearn.log_model(
                sk_model=fit.model,
                name="model",
                signature=signature,
                input_example=fit.x_test[:1],
            )
            model_uri = f"runs:/{mlflow_run_id}/model"
            manifest = _build_manifest(
                request=request,
                fit=fit,
                mlflow_run_id=mlflow_run_id,
                model_uri=model_uri,
                model_checksum=_sha256_file(model_path),
                signature_path=signature_path,
                metrics=metrics,
            )
            _write_json(manifest_path, manifest)
            mlflow.log_artifact(manifest_path)
            mlflow.set_tag("registration.status", "not-requested")

        staging_dir.replace(output_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    return TrainingResult(
        run_id=request.run_id,
        mlflow_run_id=mlflow_run_id,
        accuracy=fit.accuracy,
        minimum_accuracy=request.minimum_accuracy,
        model_uri=model_uri,
        output_dir=output_dir,
        manifest_path=output_dir / "run-manifest.json",
        registered=False,
    )


def _build_manifest(
    *,
    request: TrainingRequest,
    fit: ModelFit,
    mlflow_run_id: str,
    model_uri: str,
    model_checksum: str,
    signature_path: Path,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "component-training/1.0",
        "component": "train-classic",
        "status": "completed",
        "run_id": request.run_id,
        "mlflow_run_id": mlflow_run_id,
        "dataset": {
            "train_path": Path(request.train_path).resolve().as_uri(),
            "test_path": Path(request.test_path).resolve().as_uri(),
            "metadata_path": Path(request.metadata_path).resolve().as_uri(),
            "revision": request.dataset_revision,
        },
        "model": {
            "name": request.model_name,
            "uri": model_uri,
            "local_artifact": "model.joblib",
            "checksum": model_checksum,
            "signature": signature_path.name,
        },
        "metrics": metrics,
        "registered": False,
    }


def _load_mlflow():
    import mlflow

    return mlflow


def _ensure_experiment(client, experiment_name: str) -> str:
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment:
        return experiment.experiment_id
    return client.create_experiment(experiment_name)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _split_features_target(
    rows: list[dict[str, str]],
    feature_columns: list[str],
    categorical_columns: list[str],
    target_column: str,
) -> tuple[list[list[Any]], list[int]]:
    features = [
        [row[column] if column in categorical_columns else float(row[column]) for column in feature_columns]
        for row in rows
    ]
    targets = [int(row[target_column]) for row in rows]
    return features, targets


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def main(argv: list[str] | None = None) -> int:
    """Train from immutable local artifacts and log to configured MLflow."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tracking-uri", default=os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    parser.add_argument("--experiment-name", default="local-classic-ml")
    parser.add_argument("--run-name", default="housing-sale-baseline-component")
    parser.add_argument("--model-name", default="housing-sale-baseline")
    parser.add_argument("--minimum-accuracy", type=float, default=0.67)
    arguments = parser.parse_args(argv)
    run_training_component(
        TrainingRequest(
            run_id=arguments.run_id,
            train_path=arguments.train,
            test_path=arguments.test,
            metadata_path=arguments.metadata,
            dataset_revision=arguments.dataset_revision,
            output_dir=arguments.output_dir,
            tracking_uri=arguments.tracking_uri,
            experiment_name=arguments.experiment_name,
            run_name=arguments.run_name,
            model_name=arguments.model_name,
            minimum_accuracy=arguments.minimum_accuracy,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
