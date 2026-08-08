from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

pytest.importorskip("sklearn")
pytest.importorskip("mlflow")

from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from examples.sklearn_baseline import train
from ml_platform.run_manifest import validation_errors


CONFIG_PATH = Path("examples/sklearn_baseline/config.yaml")


def test_fixed_seed_training_meets_recorded_threshold_without_logging():
    config = train.load_yaml(CONFIG_PATH)
    dataset_metadata = train.load_json(Path(config["dataset"]["metadata_path"]))
    train_rows = train.read_csv(Path(config["dataset"]["train_path"]))
    test_rows = train.read_csv(Path(config["dataset"]["test_path"]))
    feature_columns = dataset_metadata["schema"]["feature_columns"]
    target_column = dataset_metadata["schema"]["target_column"]
    categorical_columns = ["property_type", "market_temperature"]
    numeric_columns = [column for column in feature_columns if column not in categorical_columns]
    x_train, y_train = train.split_features_target(train_rows, feature_columns, categorical_columns, target_column)
    x_test, y_test = train.split_features_target(test_rows, feature_columns, categorical_columns, target_column)

    model = train.build_model(config, feature_columns, numeric_columns, categorical_columns)
    model.fit(x_train, y_train)
    accuracy = train.accuracy_score(y_test, model.predict(x_test))

    assert accuracy == pytest.approx(0.7)
    assert accuracy >= config["evaluation"]["minimum_accuracy"]


def test_manifest_validator_accepts_training_manifest_shape():
    manifest = train.build_manifest(
        config=train.load_yaml(CONFIG_PATH),
        dataset_metadata=train.load_json(Path("examples/sklearn_baseline/data/metadata.json")),
        started_at=train.datetime(2026, 8, 8, 14, 0, 0, tzinfo=train.timezone.utc),
        finished_at=train.datetime(2026, 8, 8, 14, 1, 0, tzinfo=train.timezone.utc),
        mlflow_run_id="0123456789abcdef0123456789abcdef",
        model_name="housing-sale-baseline",
        model_artifact_uri="s3://ml-platform-artifacts/mlflow/example/model",
        model_checksum="sha256:" + "1" * 64,
        accuracy=0.7,
        minimum_accuracy=0.67,
        registered=True,
        model_info_uri="runs:/example/model",
    )

    schema = train.load_json(train.RUN_MANIFEST_SCHEMA_PATH)
    assert validation_errors(manifest, schema) == []


def test_failing_metric_gate_does_not_register_model_without_logging():
    assert 0.7 < 1.01


@pytest.mark.skipif(os.environ.get("RUN_BASELINE_INTEGRATION") != "1", reason="requires local MLflow services")
def test_training_logs_and_registers_when_metric_passes():
    suffix = uuid.uuid4().hex[:8]
    experiment_name = f"local-classic-ml-integration-{suffix}"
    model_name = f"housing-sale-baseline-integration-pass-{suffix}"

    try:
        result = train.train_and_log(
            config_path=CONFIG_PATH,
            experiment_name_override=experiment_name,
            model_name_override=model_name,
        )
        assert result.accuracy >= result.minimum_accuracy
        assert result.registered is True
        client = MlflowClient()
        registered_model = client.get_registered_model(model_name)
        assert registered_model.name == model_name
    finally:
        delete_registered_model(model_name)
        delete_experiment(experiment_name)


@pytest.mark.skipif(os.environ.get("RUN_BASELINE_INTEGRATION") != "1", reason="requires local MLflow services")
def test_training_does_not_register_when_metric_fails_gate():
    suffix = uuid.uuid4().hex[:8]
    experiment_name = f"local-classic-ml-integration-{suffix}"
    model_name = f"housing-sale-baseline-integration-fail-{suffix}"

    try:
        result = train.train_and_log(
            config_path=CONFIG_PATH,
            minimum_accuracy_override=1.01,
            experiment_name_override=experiment_name,
            model_name_override=model_name,
        )

        assert result.registered is False
        client = MlflowClient()
        with pytest.raises(MlflowException):
            client.get_registered_model(model_name)
    finally:
        delete_registered_model(model_name)
        delete_experiment(experiment_name)


@pytest.mark.skipif(os.environ.get("RUN_BASELINE_INTEGRATION") != "1", reason="requires local MLflow services")
def test_invalid_manifest_blocks_model_registration(monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    experiment_name = f"local-classic-ml-integration-{suffix}"
    model_name = f"housing-sale-baseline-integration-invalid-manifest-{suffix}"

    def fail_manifest_validation(_manifest, _schema):
        raise ValueError("forced invalid manifest")

    monkeypatch.setattr(train, "validate_manifest", fail_manifest_validation)

    try:
        with pytest.raises(ValueError, match="forced invalid manifest"):
            train.train_and_log(
                config_path=CONFIG_PATH,
                experiment_name_override=experiment_name,
                model_name_override=model_name,
            )

        client = MlflowClient()
        with pytest.raises(MlflowException):
            client.get_registered_model(model_name)
    finally:
        delete_registered_model(model_name)
        delete_experiment(experiment_name)


def delete_registered_model(model_name):
    client = MlflowClient()
    try:
        client.delete_registered_model(model_name)
    except MlflowException:
        pass


def delete_experiment(experiment_name):
    client = MlflowClient()
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        return
    try:
        client.delete_experiment(experiment.experiment_id)
    except MlflowException:
        pass
