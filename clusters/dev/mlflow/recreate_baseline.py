from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient


EXPERIMENT_NAME = os.environ.get("MLFLOW_BASELINE_EXPERIMENT", "housing-sale-baseline-cluster")
MODEL_NAME = os.environ.get("MLFLOW_BASELINE_MODEL", "housing-sale-baseline-cluster")
EXPORT_PATH = Path(os.environ.get("MLFLOW_BASELINE_EXPORT", "/migration/phase-0-baseline-export.json"))


def main() -> None:
    tracking_uri = os.environ["MLFLOW_TRACKING_URI"]
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(EXPERIMENT_NAME)
    export = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    assert export["schema_version"] == "1.0.0"

    with tempfile.TemporaryDirectory() as temporary_dir:
        artifact = Path(temporary_dir) / "baseline-recreation.json"
        artifact.write_text(json.dumps(export, sort_keys=True), encoding="utf-8")
        with mlflow.start_run(experiment_id=experiment_id, run_name="phase-00-baseline-recreated") as run:
            mlflow.log_param("source_experiment", str(export["source_experiment"]))
            mlflow.log_param("source_run", str(export["source_run"]))
            mlflow.log_param("dataset_version", str(export["dataset"]))
            for name, value in export["params"].items():
                mlflow.log_param(name, str(value))
            for name, value in export["metrics"].items():
                mlflow.log_metric(name, float(value))
            mlflow.log_artifact(str(artifact), artifact_path="migration")
            run_id = run.info.run_id
            artifact_uri = run.info.artifact_uri

    try:
        client.create_registered_model(MODEL_NAME, description="Phase-0 baseline recreated on the study cluster")
    except Exception as exc:  # MLflow uses a typed exception that changed names between minor releases.
        if "already exists" not in str(exc).lower():
            raise
    try:
        version = client.create_model_version(
            MODEL_NAME,
            source=f"{artifact_uri}/migration",
            run_id=run_id,
            description="Explicit Phase-0 baseline recreation smoke version",
        )
        client.set_registered_model_alias(MODEL_NAME, "candidate", version.version)
    except Exception as exc:
        if "already exists" not in str(exc).lower():
            raise
    print(f"recreated experiment={EXPERIMENT_NAME} run={run_id} model={MODEL_NAME}")


if __name__ == "__main__":
    main()
