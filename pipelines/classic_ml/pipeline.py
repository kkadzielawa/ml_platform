"""Compile the end-to-end classic ML pipeline without executing it.

The graph is authored for standalone Kubeflow Pipelines (KFP v2), while the
portable stage order remains inspectable without installing the KFP SDK. KFP
is imported only by ``build_pipeline`` or ``compile_pipeline``; importing this
module never submits a run or contacts a service.
"""

import argparse
import os
from pathlib import Path
from typing import Any


CLASSIC_PIPELINE_NAME = "classic-ml-study"
PIPELINE_ROOT = os.environ.get(
    "CLASSIC_PIPELINE_ROOT",
    "s3://ml-platform-artifacts/projects/ml-platform/artifacts/kfp/v2/classic-ml",
)
COMPONENT_IMAGE = os.environ.get(
    "CLASSIC_COMPONENT_IMAGE",
    "docker.io/library/python:3.12.13-slim-bookworm@sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af",
)

PIPELINE_PARAMETERS = (
    "run_id",
    "mlflow_run_id",
    "dataset_repository",
    "dataset_reference",
    "dataset_path",
    "dataset_name",
    "dataset_version",
    "validation_suite_path",
    "dataset_revision",
    "tracking_uri",
    "experiment_name",
    "run_name",
    "model_name",
    "model_version",
    "code_version",
    "license_record_path",
    "model_source_uri",
    "evaluation_sha256",
)

PIPELINE_STAGES = (
    "snapshot",
    "validate",
    "transform",
    "train",
    "evaluate",
    "register",
)

PIPELINE_EDGES = (
    ("snapshot", "validate"),
    ("validate", "transform"),
    ("transform", "train"),
    ("train", "evaluate"),
    ("evaluate", "register"),
)


def pipeline_spec() -> dict[str, Any]:
    """Return the orchestrator-neutral graph contract used by tests and docs."""

    return {
        "name": CLASSIC_PIPELINE_NAME,
        "root": PIPELINE_ROOT,
        "image": COMPONENT_IMAGE,
        "parameters": list(PIPELINE_PARAMETERS),
        "stages": list(PIPELINE_STAGES),
        "edges": [list(edge) for edge in PIPELINE_EDGES],
        "behavior": {
            "cache": False,
            "registration_requires_passing_evaluation": True,
            "run_on_import": False,
        },
    }


def build_pipeline():
    """Build and return the KFP pipeline function, without submitting a run."""

    try:
        from kfp import dsl
        from kfp.dsl import Artifact, Input, Output
    except ImportError as error:
        raise RuntimeError(
            "KFP SDK is required only to compile this pipeline; install the pinned "
            "pipeline toolchain from config/versions.yaml"
        ) from error

    @dsl.container_component
    def snapshot_component(
        repository: str,
        reference: str,
        dataset_path: str,
        snapshot_manifest: Output[Artifact],
    ):
        return dsl.ContainerSpec(
            image=COMPONENT_IMAGE,
            command=["python", "-m", "components.snapshot"],
            args=[
                "--repository",
                repository,
                "--reference",
                reference,
                "--dataset-path",
                dataset_path,
                "--output",
                snapshot_manifest.path,
            ],
        )

    @dsl.container_component
    def validate_component(
        snapshot_manifest: Input[Artifact],
        dataset_path: str,
        suite_path: str,
        validation_report: Output[Artifact],
    ):
        return dsl.ContainerSpec(
            image=COMPONENT_IMAGE,
            command=["python", "-m", "components.validate"],
            args=[
                "--snapshot",
                snapshot_manifest.path,
                "--dataset",
                dataset_path,
                "--suite",
                suite_path,
                "--report",
                validation_report.path,
            ],
        )

    @dsl.container_component
    def transform_component(
        run_id: str,
        train_path: str,
        test_path: str,
        output_root: Output[Artifact],
    ):
        return dsl.ContainerSpec(
            image=COMPONENT_IMAGE,
            command=["python", "-m", "components.transform"],
            args=[
                "--run-id",
                run_id,
                "--train",
                train_path,
                "--test",
                test_path,
                "--output-root",
                output_root.path,
            ],
        )

    @dsl.container_component
    def train_component(
        run_id: str,
        transformed_dataset: Input[Artifact],
        metadata_path: str,
        dataset_revision: str,
        tracking_uri: str,
        experiment_name: str,
        run_name: str,
        model_name: str,
        output_dir: Output[Artifact],
    ):
        return dsl.ContainerSpec(
            image=COMPONENT_IMAGE,
            command=["python", "-m", "components.train_classic"],
            args=[
                "--run-id",
                run_id,
                "--train",
                f"{transformed_dataset.path}/{run_id}/curated/train.csv",
                "--test",
                f"{transformed_dataset.path}/{run_id}/curated/test.csv",
                "--metadata",
                metadata_path,
                "--dataset-revision",
                dataset_revision,
                "--output-dir",
                output_dir.path,
                "--tracking-uri",
                tracking_uri,
                "--experiment-name",
                experiment_name,
                "--run-name",
                run_name,
                "--model-name",
                model_name,
            ],
        )

    @dsl.container_component
    def evaluate_component(
        run_id: str,
        transformed_dataset: Input[Artifact],
        training_output: Input[Artifact],
        metadata_path: str,
        report: Output[Artifact],
        dataset_name: str,
        dataset_version: str,
        dataset_revision: str,
        model_name: str,
        model_version: str,
        code_version: str,
    ):
        return dsl.ContainerSpec(
            image=COMPONENT_IMAGE,
            command=["python", "-m", "components.evaluate_classic"],
            args=[
                "--run-id",
                run_id,
                "--test",
                f"{transformed_dataset.path}/{run_id}/curated/test.csv",
                "--metadata",
                metadata_path,
                "--candidate-model",
                f"{training_output.path}/model.joblib",
                "--report",
                report.path,
                "--dataset-name",
                dataset_name,
                "--dataset-version",
                dataset_version,
                "--dataset-revision",
                dataset_revision,
                "--model-name",
                model_name,
                "--model-version",
                model_version,
                "--code-version",
                code_version,
            ],
        )

    @dsl.container_component
    def register_component(
        run_id: str,
        mlflow_run_id: str,
        model_name: str,
        model_version: str,
        model_source_uri: str,
        evaluation: Input[Artifact],
        evaluation_sha256: str,
        training_output: Input[Artifact],
        license_record_path: str,
    ):
        return dsl.ContainerSpec(
            image=COMPONENT_IMAGE,
            command=["python", "-m", "components.register_model"],
            args=[
                "--run-id",
                run_id,
                "--mlflow-run-id",
                mlflow_run_id,
                "--model-name",
                model_name,
                "--model-version",
                model_version,
                "--model-source",
                model_source_uri,
                "--evaluation",
                evaluation.path,
                "--evaluation-sha256",
                evaluation_sha256,
                "--run-manifest",
                f"{training_output.path}/run-manifest.json",
                "--signature",
                f"{training_output.path}/signature.json",
                "--license-record",
                license_record_path,
            ],
        )

    @dsl.pipeline(name=CLASSIC_PIPELINE_NAME, pipeline_root=PIPELINE_ROOT)
    def classic_ml_pipeline(
        run_id: str,
        mlflow_run_id: str,
        dataset_repository: str,
        dataset_reference: str,
        dataset_path: str,
        dataset_name: str,
        dataset_version: str,
        validation_suite_path: str,
        dataset_revision: str,
        tracking_uri: str,
        experiment_name: str,
        run_name: str,
        model_name: str,
        model_version: str,
        code_version: str,
        license_record_path: str,
        model_source_uri: str,
        evaluation_sha256: str,
    ) -> None:
        snapshot = snapshot_component(
            repository=dataset_repository,
            reference=dataset_reference,
            dataset_path=dataset_path,
        )
        validation = validate_component(
            snapshot_manifest=snapshot.outputs["snapshot_manifest"],
            dataset_path=dataset_path,
            suite_path=validation_suite_path,
        )
        transform = transform_component(
                run_id=run_id,
                train_path=f"{dataset_path}/train.csv",
                test_path=f"{dataset_path}/test.csv",
        )
        transform.after(validation)
        train = train_component(
            run_id=run_id,
            transformed_dataset=transform.outputs["output_root"],
            metadata_path=f"{dataset_path}/metadata.json",
            dataset_revision=dataset_revision,
            tracking_uri=tracking_uri,
            experiment_name=experiment_name,
            run_name=run_name,
            model_name=model_name,
        )
        evaluate = evaluate_component(
            run_id=run_id,
            transformed_dataset=transform.outputs["output_root"],
            training_output=train.outputs["output_dir"],
            metadata_path=f"{dataset_path}/metadata.json",
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            dataset_revision=dataset_revision,
            model_name=model_name,
            model_version=model_version,
            code_version=code_version,
        )
        register = register_component(
            run_id=run_id,
            mlflow_run_id=mlflow_run_id,
            model_name=model_name,
            model_version=model_version,
            model_source_uri=model_source_uri,
            evaluation=evaluate.outputs["report"],
            evaluation_sha256=evaluation_sha256,
            training_output=train.outputs["output_dir"],
            license_record_path=license_record_path,
        )
        register.after(evaluate)
        for task in (snapshot, validation, transform, train, evaluate, register):
            task.set_caching_options(False)

    return classic_ml_pipeline


def compile_pipeline(output_path: Path) -> Path:
    """Compile the graph to a KFP package; never submit or execute it."""

    try:
        from kfp import compiler
    except ImportError as error:
        raise RuntimeError(
            "KFP SDK is required only to compile this pipeline; install the pinned "
            "pipeline toolchain from config/versions.yaml"
        ) from error
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    compiler.Compiler().compile(
        pipeline_func=build_pipeline(),
        package_path=str(output_path),
    )
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    compile_pipeline(arguments.output)
    print(f"compiled classic ML pipeline to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
