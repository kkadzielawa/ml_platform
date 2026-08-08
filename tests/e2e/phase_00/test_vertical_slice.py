from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PHASE_00_E2E") != "1",
    reason="requires local Phase 0 services and is run by make e2e-phase-00",
)


VALID_PAYLOAD = {
    "listing_price_usd": 425000,
    "square_feet": 1850,
    "bedrooms": 3,
    "bathrooms": 2.5,
    "home_age_years": 18,
    "school_rating": 8.2,
    "walk_score": 72,
    "mortgage_rate_percent": 6.4,
    "property_type": "single-family",
    "market_temperature": "balanced",
}


def test_phase_zero_vertical_slice():
    pytest.importorskip("fastapi")
    pytest.importorskip("mlflow")
    pytest.importorskip("sklearn")

    from fastapi.testclient import TestClient
    from mlflow.exceptions import MlflowException
    from mlflow.tracking import MlflowClient

    from examples.sklearn_baseline import train
    from examples.sklearn_baseline.service.app import ModelSettings, create_app

    suffix = uuid.uuid4().hex[:10]
    experiment_name = f"phase-00-e2e-{suffix}"
    model_name = f"phase-00-e2e-baseline-{suffix}"
    failing_model_name = f"phase-00-e2e-failing-gate-{suffix}"
    client = MlflowClient()
    summary = {}

    try:
        first_result = train.train_and_log(
            config_path=Path("examples/sklearn_baseline/config.yaml"),
            experiment_name_override=experiment_name,
            model_name_override=model_name,
        )
        second_result = train.train_and_log(
            config_path=Path("examples/sklearn_baseline/config.yaml"),
            experiment_name_override=experiment_name,
            model_name_override=model_name,
        )

        assert first_result.run_id != second_result.run_id
        assert first_result.mlflow_run_id != second_result.mlflow_run_id
        assert first_result.accuracy >= first_result.minimum_accuracy
        assert second_result.accuracy >= second_result.minimum_accuracy
        assert first_result.registered is True
        assert second_result.registered is True

        registered_versions = sorted(
            client.search_model_versions(f"name = '{model_name}'"),
            key=lambda version: int(version.version),
        )
        assert len(registered_versions) == 2
        served_version = registered_versions[-1].version

        app = create_app(settings=ModelSettings(name=model_name, version=served_version))
        service = TestClient(app)
        metadata_response = service.get("/metadata")
        assert metadata_response.status_code == 200
        assert metadata_response.json()["model_uri"] == f"models:/{model_name}/{served_version}"

        prediction_response = service.post(
            "/predict",
            json=VALID_PAYLOAD,
            headers={"X-Request-ID": f"phase-00-e2e-{suffix}"},
        )
        assert prediction_response.status_code == 200
        prediction_payload = prediction_response.json()
        assert prediction_payload["request_id"] == f"phase-00-e2e-{suffix}"
        assert prediction_payload["model_name"] == model_name
        assert prediction_payload["model_version"] == served_version
        assert prediction_payload["prediction"] in (0, 1)
        assert 0 <= prediction_payload["sold_within_30_days_probability"] <= 1

        bad_payload = VALID_PAYLOAD | {"listing_price_usd": -100, "property_type": "castle"}
        bad_response = service.post("/predict", json=bad_payload)
        assert 400 <= bad_response.status_code < 500
        assert "Traceback" not in bad_response.text

        failed_gate_result = train.train_and_log(
            config_path=Path("examples/sklearn_baseline/config.yaml"),
            minimum_accuracy_override=1.01,
            experiment_name_override=experiment_name,
            model_name_override=failing_model_name,
        )
        assert failed_gate_result.registered is False
        with pytest.raises(MlflowException):
            client.get_registered_model(failing_model_name)

        summary = {
            "experiment_name": experiment_name,
            "successful_run_ids": [first_result.run_id, second_result.run_id],
            "successful_mlflow_run_ids": [first_result.mlflow_run_id, second_result.mlflow_run_id],
            "served_model": {"name": model_name, "version": served_version},
            "prediction": prediction_payload,
            "failed_gate_run_id": failed_gate_result.run_id,
            "cleanup": "registered models and active experiment deleted in finally block",
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
    finally:
        delete_registered_model(client, model_name)
        delete_registered_model(client, failing_model_name)
        delete_experiment(client, experiment_name)


def delete_registered_model(client, model_name: str) -> None:
    from mlflow.exceptions import MlflowException

    try:
        client.delete_registered_model(model_name)
    except MlflowException:
        pass


def delete_experiment(client, experiment_name: str) -> None:
    from mlflow.exceptions import MlflowException

    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        return
    try:
        client.delete_experiment(experiment.experiment_id)
    except MlflowException:
        pass

