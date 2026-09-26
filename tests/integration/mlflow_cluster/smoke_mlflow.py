from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient


def main() -> None:
    tracking_uri = os.environ["MLFLOW_TRACKING_URI"]
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    experiment_name = f"04-02-cluster-smoke-{uuid.uuid4()}"
    model_name = f"04-02-cluster-smoke-{uuid.uuid4()}"
    experiment_id = client.create_experiment(experiment_name)
    run_id = None
    try:
        with tempfile.TemporaryDirectory() as temporary_dir:
            artifact = Path(temporary_dir) / "smoke-artifact.txt"
            artifact.write_text("cluster MLflow artifact smoke ok\n", encoding="utf-8")
            with mlflow.start_run(experiment_id=experiment_id, run_name="tracking-artifact-registry") as run:
                run_id = run.info.run_id
                mlflow.log_metric("smoke_metric", 1.0)
                mlflow.log_param("route", "cluster")
                mlflow.log_artifact(str(artifact), artifact_path="model")

            stored = client.get_run(run_id)
            assert stored.data.metrics["smoke_metric"] == 1.0
            downloaded = client.download_artifacts(run_id, "model/smoke-artifact.txt", temporary_dir)
            assert Path(downloaded).read_text(encoding="utf-8") == "cluster MLflow artifact smoke ok\n"

        try:
            client.create_registered_model(model_name)
        except MlflowException as exc:
            if "already exists" not in str(exc).lower():
                raise
        version = client.create_model_version(
            model_name,
            source=f"{stored.info.artifact_uri}/model",
            run_id=run_id,
            description="04.02 registry smoke version",
        )
        client.set_registered_model_alias(model_name, "candidate", version.version)
        assert client.get_model_version_by_alias(model_name, "candidate").version == version.version
        print(f"MLflow cluster smoke passed: run={run_id} model={model_name} version={version.version}")
    finally:
        if run_id:
            client.delete_run(run_id)
        client.delete_experiment(experiment_id)
        try:
            client.delete_registered_model(model_name)
        except MlflowException:
            pass


if __name__ == "__main__":
    main()
