from __future__ import annotations

import os

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("mlflow")

from fastapi.testclient import TestClient

from examples.sklearn_baseline.service.app import ModelSettings, create_app


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


class DummyModel:
    def predict(self, rows):
        assert len(rows) == 1
        assert rows[0][-2:] == ["single-family", "balanced"]
        return [1]

    def predict_proba(self, rows):
        assert len(rows) == 1
        return [[0.31, 0.69]]


def test_health_endpoint():
    client = TestClient(fake_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metadata_endpoint_includes_explicit_model_version():
    client = TestClient(fake_app(model_version="7"))

    response = client.get("/metadata")

    assert response.status_code == 200
    assert response.json()["model_name"] == "housing-sale-baseline-test"
    assert response.json()["model_version"] == "7"
    assert response.json()["model_uri"] == "models:/housing-sale-baseline-test/7"
    assert "listing_price_usd" in response.json()["feature_columns"]


def test_valid_prediction_includes_request_id_and_model_version():
    client = TestClient(fake_app(model_version="3"))

    response = client.post("/predict", json=VALID_PAYLOAD, headers={"X-Request-ID": "request-123"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "request-123"
    assert payload["model_name"] == "housing-sale-baseline-test"
    assert payload["model_version"] == "3"
    assert payload["prediction"] == 1
    assert payload["prediction_label"] == "listing sold within 30 days"
    assert payload["sold_within_30_days_probability"] == pytest.approx(0.69)


def test_invalid_payload_returns_4xx_without_stack_trace():
    client = TestClient(fake_app())
    invalid_payload = VALID_PAYLOAD | {"listing_price_usd": -1, "property_type": "castle"}

    response = client.post("/predict", json=invalid_payload)

    assert 400 <= response.status_code < 500
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text


@pytest.mark.skipif(
    os.environ.get("RUN_BASELINE_SERVICE_INTEGRATION") != "1",
    reason="requires local MLflow services and a registered baseline model version",
)
def test_service_loads_registered_mlflow_model_version():
    app = create_app()
    client = TestClient(app)

    response = client.post("/predict", json=VALID_PAYLOAD, headers={"X-Request-ID": "integration-request"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "integration-request"
    assert payload["model_name"] == os.environ.get("BASELINE_MODEL_NAME", "housing-sale-baseline")
    assert payload["model_version"] == os.environ["BASELINE_MODEL_VERSION"]
    assert payload["prediction"] in (0, 1)


def fake_app(model_version: str = "1"):
    return create_app(
        settings=ModelSettings(name="housing-sale-baseline-test", version=model_version),
        model_loader=lambda _uri: DummyModel(),
    )

