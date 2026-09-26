import os
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
import kfp
from kfp import compiler, dsl
from kfp.dsl import Artifact, Input, Output


PIPELINE_IMAGE = "docker.io/library/python:3.12.13-slim-bookworm@sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af"
PIPELINE_ROOT = "s3://ml-platform-artifacts/projects/ml-platform/artifacts/kfp/v2"


@dsl.component(base_image=PIPELINE_IMAGE)
def write_message(message: str, artifact: Output[Artifact]) -> None:
    from pathlib import Path

    Path(artifact.path).write_text(message, encoding="utf-8")


@dsl.component(base_image=PIPELINE_IMAGE)
def verify_message(
    expected_message: str,
    source: Input[Artifact],
    artifact: Output[Artifact],
) -> None:
    from pathlib import Path

    received = Path(source.path).read_text(encoding="utf-8")
    if received != expected_message:
        raise ValueError(f"artifact mismatch: expected {expected_message!r}, got {received!r}")
    Path(artifact.path).write_text(f"verified:{received}", encoding="utf-8")


@dsl.pipeline(name="study-artifact-passing", pipeline_root=PIPELINE_ROOT)
def artifact_passing_pipeline(message: str) -> None:
    written = write_message(message=message)
    verify_message(expected_message=message, source=written.outputs["artifact"])


def main() -> None:
    tracking_host = os.environ["KFP_ENDPOINT"]
    namespace = os.environ.get("KFP_NAMESPACE", "kubeflow")
    bucket = os.environ.get("KFP_ARTIFACT_BUCKET", "ml-platform-artifacts")
    prefix = os.environ.get("KFP_ARTIFACT_PREFIX", "projects/ml-platform/artifacts/kfp/")
    message = f"kfp-smoke-{uuid.uuid4()}"
    run_name = f"04-03-artifact-passing-{uuid.uuid4().hex[:8]}"

    with TemporaryDirectory(prefix="ml-platform-kfp-") as directory:
        package_path = Path(directory) / "artifact-passing.yaml"
        compiler.Compiler().compile(
            pipeline_func=artifact_passing_pipeline,
            package_path=str(package_path),
        )

        client = kfp.Client(host=tracking_host)
        result = client.create_run_from_pipeline_package(
            pipeline_file=str(package_path),
            arguments={"message": message},
            run_name=run_name,
            experiment_name="04-03-orchestrator-smoke",
            namespace=namespace,
            enable_caching=False,
        )
        run_id = result.run_id
        run = wait_for_run(client, run_id)

    parameters = run.runtime_config.parameters or {}
    if parameters.get("message") != message:
        raise AssertionError(f"KFP API did not preserve the pipeline parameter: {parameters!r}")

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["KFP_S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("AWS_DEFAULT_REGION", "garage"),
    )
    objects = s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("Contents", [])
    if not objects:
        raise AssertionError(f"no KFP artifacts found at s3://{bucket}/{prefix}")

    print(f"KFP orchestrator smoke passed: run={run_id} artifacts={len(objects)}")


def wait_for_run(client: kfp.Client, run_id: str):
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        run = client.get_run(run_id)
        if run.state == "SUCCEEDED":
            return run
        if run.state in {"FAILED", "CANCELLED", "ERROR"}:
            raise RuntimeError(f"KFP run {run_id} ended as {run.state}: {run.error}")
        time.sleep(5)
    raise TimeoutError(f"KFP run {run_id} did not finish within 600 seconds")


if __name__ == "__main__":
    main()
