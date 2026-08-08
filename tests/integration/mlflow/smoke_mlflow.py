import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import boto3
import mlflow
from mlflow.tracking import MlflowClient


def main():
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    experiment_id = None
    run_id = None
    artifact_uri = None

    try:
        experiment_name = f"00-12-smoke-{uuid.uuid4()}"
        experiment_id = client.create_experiment(experiment_name)

        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as download_dir:
            artifact_file = Path(source_dir) / "smoke-artifact.txt"
            artifact_file.write_text("mlflow smoke artifact ok\n", encoding="utf-8")

            with mlflow.start_run(experiment_id=experiment_id, run_name="smoke") as run:
                run_id = run.info.run_id
                mlflow.log_metric("smoke_metric", 1.0)
                mlflow.log_artifact(str(artifact_file))

            stored_run = client.get_run(run_id)
            artifact_uri = stored_run.info.artifact_uri
            assert stored_run.data.metrics["smoke_metric"] == 1.0
            assert artifact_uri.startswith("s3://"), artifact_uri

            downloaded_path = client.download_artifacts(run_id, artifact_file.name, download_dir)
            downloaded_text = Path(downloaded_path).read_text(encoding="utf-8")
            assert downloaded_text == "mlflow smoke artifact ok\n"
    finally:
        if artifact_uri:
            delete_s3_artifacts(artifact_uri)
        if run_id:
            client.delete_run(run_id)
        if experiment_id:
            client.delete_experiment(experiment_id)


def delete_s3_artifacts(artifact_uri):
    parsed = urlparse(artifact_uri)
    if parsed.scheme != "s3":
        return

    prefix = parsed.path.lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"],
        region_name=os.environ.get("AWS_DEFAULT_REGION", "garage"),
    )
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=parsed.netloc, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if objects:
            s3.delete_objects(Bucket=parsed.netloc, Delete={"Objects": objects})


if __name__ == "__main__":
    main()
