from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import mlflow
import mlflow.sklearn
import yaml
from mlflow.tracking import MlflowClient
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml_platform.run_manifest import validate_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_MANIFEST_SCHEMA_PATH = REPO_ROOT / "contracts" / "run-manifest.schema.json"


@dataclass(frozen=True)
class TrainingResult:
    run_id: str
    mlflow_run_id: str
    accuracy: float
    minimum_accuracy: float
    registered: bool
    registered_model_name: str | None
    manifest: dict[str, Any]


def main() -> None:
    args = parse_args()
    result = train_and_log(
        config_path=args.config,
        minimum_accuracy_override=args.minimum_accuracy,
        experiment_name_override=args.experiment_name,
        model_name_override=args.model_name,
        register_model=not args.no_register,
    )
    print(json.dumps({"run_id": result.run_id, "accuracy": result.accuracy, "registered": result.registered}, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the Phase 0 sklearn housing-sale baseline.")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "examples" / "sklearn_baseline" / "config.yaml")
    parser.add_argument("--minimum-accuracy", type=float, default=None)
    parser.add_argument("--experiment-name", type=str, default=None)
    parser.add_argument("--model-name", type=str, default=None)
    parser.add_argument("--no-register", action="store_true")
    return parser.parse_args()


def train_and_log(
    config_path: Path,
    minimum_accuracy_override: float | None = None,
    experiment_name_override: str | None = None,
    model_name_override: str | None = None,
    register_model: bool = True,
) -> TrainingResult:
    started_at = utc_now()
    config = load_yaml(config_path)
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", config["mlflow"]["tracking_uri"])
    experiment_name = experiment_name_override or config["mlflow"]["experiment_name"]
    model_name = model_name_override or config["model"]["name"]
    minimum_accuracy = minimum_accuracy_override or float(config["evaluation"]["minimum_accuracy"])

    train_rows = read_csv(REPO_ROOT / config["dataset"]["train_path"])
    test_rows = read_csv(REPO_ROOT / config["dataset"]["test_path"])
    dataset_metadata = load_json(REPO_ROOT / config["dataset"]["metadata_path"])

    feature_columns = dataset_metadata["schema"]["feature_columns"]
    target_column = dataset_metadata["schema"]["target_column"]
    categorical_columns = ["property_type", "market_temperature"]
    numeric_columns = [column for column in feature_columns if column not in categorical_columns]
    x_train, y_train = split_features_target(train_rows, feature_columns, categorical_columns, target_column)
    x_test, y_test = split_features_target(test_rows, feature_columns, categorical_columns, target_column)

    model = build_model(config, feature_columns, numeric_columns, categorical_columns)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    accuracy = float(accuracy_score(y_test, predictions))
    metric_gate_passed = accuracy >= minimum_accuracy
    should_register = register_model and metric_gate_passed
    registered = False

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment_id = ensure_experiment(client, experiment_name)

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        model_path = temp_dir / "model.joblib"
        metrics_path = temp_dir / "metrics.json"
        manifest_path = temp_dir / "run_manifest.json"
        joblib.dump(model, model_path)
        model_checksum = sha256_file(model_path)

        with mlflow.start_run(experiment_id=experiment_id, run_name=config["mlflow"]["run_name"]) as active_run:
            mlflow_run_id = active_run.info.run_id
            mlflow.log_params(flatten_dict("model", config["model"]["parameters"]))
            mlflow.log_param("dataset_name", config["dataset"]["name"])
            mlflow.log_param("dataset_version", config["dataset"]["version"])
            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_metric("minimum_accuracy", minimum_accuracy)
            mlflow.log_metric("majority_baseline_accuracy", dataset_metadata["expected_baseline"]["test_accuracy"])

            metrics_payload = {
                "accuracy": accuracy,
                "minimum_accuracy": minimum_accuracy,
                "majority_baseline_accuracy": dataset_metadata["expected_baseline"]["test_accuracy"],
                "metric_gate_passed": metric_gate_passed,
                "registration_requested": should_register,
            }
            write_json(metrics_path, metrics_payload)
            mlflow.log_artifact(metrics_path)
            mlflow.log_artifact(REPO_ROOT / config["dataset"]["metadata_path"], artifact_path="dataset")

            finished_at = utc_now()
            model_artifact_uri = f"{active_run.info.artifact_uri.rstrip('/')}/model"
            manifest = build_manifest(
                config=config,
                dataset_metadata=dataset_metadata,
                started_at=started_at,
                finished_at=finished_at,
                mlflow_run_id=mlflow_run_id,
                model_name=model_name,
                model_artifact_uri=model_artifact_uri,
                model_checksum=model_checksum,
                accuracy=accuracy,
                minimum_accuracy=minimum_accuracy,
                registered=should_register,
                model_info_uri=f"runs:/{mlflow_run_id}/model",
            )
            try:
                validate_manifest(manifest, load_json(RUN_MANIFEST_SCHEMA_PATH))
            except Exception as exc:
                mlflow.set_tag("manifest.validation_status", "failed")
                mlflow.set_tag("registration.blocked_reason", "invalid-run-manifest")
                error_path = temp_dir / "manifest_validation_error.txt"
                error_path.write_text(f"{exc}\n", encoding="utf-8")
                mlflow.log_artifact(error_path)
                raise

            mlflow.set_tag("manifest.validation_status", "passed")
            write_json(manifest_path, manifest)
            mlflow.log_artifact(manifest_path)
            mlflow.log_artifact(model_path, artifact_path="model-checksum-source")

            mlflow.sklearn.log_model(
                sk_model=model,
                name="model",
                registered_model_name=model_name if should_register else None,
            )
            registered = should_register
            mlflow.set_tag("registration.status", "registered" if registered else "skipped")

    return TrainingResult(
        run_id=manifest["run_id"],
        mlflow_run_id=mlflow_run_id,
        accuracy=accuracy,
        minimum_accuracy=minimum_accuracy,
        registered=registered,
        registered_model_name=model_name if registered else None,
        manifest=manifest,
    )


def build_model(config, feature_columns, numeric_columns, categorical_columns):
    categorical_indexes = [feature_columns.index(column) for column in categorical_columns]
    numeric_indexes = [feature_columns.index(column) for column in numeric_columns]
    classifier = GradientBoostingClassifier(**config["model"]["parameters"])
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), numeric_indexes),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_indexes),
        ]
    )
    return Pipeline([("preprocess", preprocessor), ("classifier", classifier)])


def build_manifest(
    config,
    dataset_metadata,
    started_at,
    finished_at,
    mlflow_run_id,
    model_name,
    model_artifact_uri,
    model_checksum,
    accuracy,
    minimum_accuracy,
    registered,
    model_info_uri,
):
    run_id = make_run_id(finished_at)
    train_path = REPO_ROOT / config["dataset"]["train_path"]
    test_path = REPO_ROOT / config["dataset"]["test_path"]
    source_image = config["runtime"]["source_image"]
    commit = git_commit()
    dataset_uri = f"file://{(REPO_ROOT / 'examples' / 'sklearn_baseline' / 'data').resolve()}"
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "owner": config["owner"],
        "project": config["project"],
        "environment": config["environment"],
        "parent_run_id": None,
        "timestamps": {
            "started_at": format_timestamp(started_at),
            "finished_at": format_timestamp(finished_at),
        },
        "correlation": {
            "trace_id": secrets.token_hex(16),
            "correlation_id": config["mlflow"]["experiment_name"],
        },
        "code": {
            "repository": "https://github.com/kkadzielawa/ml_platform",
            "commit": commit,
            "dirty_worktree": dirty_worktree(),
            "dependency_lockfile_hash": sha256_file(REPO_ROOT / config["runtime"]["dependency_lockfile_path"]),
        },
        "images": {
            "source": image_ref(source_image),
            "output": {
                "repository": "docker.io/local/housing-sale-baseline",
                "tag": config["model"]["version"],
                "digest": model_checksum,
                "sbom": f"{model_artifact_uri}/sbom-placeholder.spdx.json",
                "signature": f"{model_artifact_uri}/signature-placeholder.sig",
            },
        },
        "artifacts": {
            "inputs": [
                dataset_artifact(dataset_metadata["dataset"]["name"], dataset_uri, train_path, commit, "train"),
                dataset_artifact(dataset_metadata["dataset"]["name"], dataset_uri, test_path, commit, "test"),
            ],
            "outputs": [
                {
                    "name": model_name,
                    "kind": "model",
                    "uri": model_artifact_uri,
                    "checksum": model_checksum,
                    "schema_ref": "https://example.local/ml-platform-study/contracts/model-artifact.schema.json",
                    "data_revision": {"type": "object-version", "id": mlflow_run_id},
                }
            ],
        },
        "model": {
            "name": model_name,
            "version": config["model"]["version"],
            "license": config["model"]["license"],
            "tokenizer": None,
            "embedding_model": None,
            "prompt_version": None,
            "index_version": None,
        },
        "reproducibility": {
            "hardware": {"cpu": "local-cpu", "memory_gib": local_memory_gib(), "gpu": None},
            "driver_runtime_versions": driver_runtime_versions(),
            "random_seeds": {"python": config["runtime"]["random_seed"], "model": config["model"]["parameters"]["random_state"]},
        },
        "parameters": config["model"]["parameters"],
        "metrics": {"accuracy": accuracy, "minimum_accuracy": minimum_accuracy},
        "evaluation_results": [
            {
                "name": "heldout-accuracy",
                "metric": "accuracy",
                "value": accuracy,
                "unit": "ratio",
                "threshold": f">={minimum_accuracy}",
                "passed": accuracy >= minimum_accuracy,
            }
        ],
        "policy_decisions": [
            {
                "name": "registration-gate",
                "decision": "allow" if registered else "deny",
                "reason": "accuracy met registration threshold" if registered else "accuracy did not meet registration threshold",
            }
        ],
        "approval": {"required": False, "approved_by": None, "approved_at": None},
        "lineage_events": [
            {
                "event_type": "trained",
                "event_time": format_timestamp(finished_at),
                "source": dataset_uri,
                "target": model_artifact_uri,
            }
        ],
        "retention": config["retention"],
    }


def dataset_artifact(dataset_name, dataset_uri, path, commit, split_name):
    return {
        "name": f"{dataset_name}-{split_name}",
        "kind": "dataset",
        "uri": f"{dataset_uri}/{path.name}",
        "checksum": sha256_file(path),
        "schema_ref": "https://example.local/ml-platform-study/contracts/sklearn-baseline-dataset.schema.json",
        "data_revision": {"type": "git-commit", "id": commit},
    }


def image_ref(image):
    return {
        "repository": image["repository"],
        "tag": image["tag"],
        "digest": image["digest"],
        "sbom": f"s3://ml-platform-artifacts/sbom/{image['repository'].replace('/', '-')}-{image['tag']}.spdx.json",
        "signature": f"s3://ml-platform-artifacts/signatures/{image['repository'].replace('/', '-')}-{image['tag']}.sig",
    }


def split_features_target(rows, feature_columns, categorical_columns, target_column):
    features = []
    targets = []
    for row in rows:
        features.append([row[column] if column in categorical_columns else float(row[column]) for column in feature_columns])
        targets.append(int(row[target_column]))
    return features, targets


def ensure_experiment(client, experiment_name):
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment:
        return experiment.experiment_id
    return client.create_experiment(experiment_name)


def load_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def flatten_dict(prefix, values):
    return {f"{prefix}.{key}": value for key, value in values.items()}


def sha256_file(path):
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def make_run_id(timestamp):
    return f"run-{timestamp.strftime('%Y%m%d')}t{timestamp.strftime('%H%M%S')}z-{secrets.token_hex(4)}"


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def format_timestamp(timestamp):
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def git_commit():
    git_dir = REPO_ROOT / ".git"
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref_path = git_dir / head.removeprefix("ref: ")
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip()
    if len(head) == 40:
        return head
    return "0" * 40


def dirty_worktree():
    try:
        result = subprocess.run(["git", "status", "--short"], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return True
    return bool(result.stdout.strip())


def driver_runtime_versions():
    import mlflow as mlflow_package
    import numpy
    import sklearn

    return {
        "python": sys.version.split()[0],
        "mlflow": mlflow_package.__version__,
        "numpy": numpy.__version__,
        "scikit-learn": sklearn.__version__,
    }


def local_memory_gib():
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return 0
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            kib = int(line.split()[1])
            return round(kib / 1024 / 1024, 2)
    return 0


if __name__ == "__main__":
    main()
