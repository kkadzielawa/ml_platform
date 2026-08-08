from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Annotated, Literal

import mlflow.sklearn
from fastapi import FastAPI, Header
from pydantic import BaseModel, ConfigDict, Field


FEATURE_COLUMNS = [
    "listing_price_usd",
    "square_feet",
    "bedrooms",
    "bathrooms",
    "home_age_years",
    "school_rating",
    "walk_score",
    "mortgage_rate_percent",
    "property_type",
    "market_temperature",
]


@dataclass(frozen=True)
class ModelSettings:
    name: str
    version: str

    @property
    def uri(self) -> str:
        return f"models:/{self.name}/{self.version}"


class HousingSaleFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_price_usd: float = Field(gt=0)
    square_feet: float = Field(gt=0)
    bedrooms: int = Field(ge=0, le=20)
    bathrooms: float = Field(ge=0, le=20)
    home_age_years: int = Field(ge=0, le=300)
    school_rating: float = Field(ge=0, le=10)
    walk_score: float = Field(ge=0, le=100)
    mortgage_rate_percent: float = Field(gt=0, le=30)
    property_type: Literal["condo", "single-family", "townhouse"]
    market_temperature: Literal["balanced", "cool", "hot"]

    def as_model_row(self) -> list[float | str]:
        return [getattr(self, column) for column in FEATURE_COLUMNS]


class PredictionResponse(BaseModel):
    request_id: str
    model_name: str
    model_version: str
    prediction: Literal[0, 1]
    prediction_label: str
    sold_within_30_days_probability: float | None


class MetadataResponse(BaseModel):
    model_name: str
    model_version: str
    model_uri: str
    feature_columns: list[str]


def create_app(
    settings: ModelSettings | None = None,
    model_loader=mlflow.sklearn.load_model,
) -> FastAPI:
    app = FastAPI(title="sklearn housing-sale baseline", version="0.1.0")
    app.state.model_settings = settings
    app.state.model_loader = model_loader
    app.state.model = None

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metadata", response_model=MetadataResponse)
    def metadata() -> MetadataResponse:
        resolved_settings = get_settings(app)
        return MetadataResponse(
            model_name=resolved_settings.name,
            model_version=resolved_settings.version,
            model_uri=resolved_settings.uri,
            feature_columns=FEATURE_COLUMNS,
        )

    @app.post("/predict", response_model=PredictionResponse)
    def predict(
        payload: HousingSaleFeatures,
        x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
    ) -> PredictionResponse:
        request_id = x_request_id or str(uuid.uuid4())
        resolved_settings = get_settings(app)
        model = load_model_once(app)
        prediction = int(model.predict([payload.as_model_row()])[0])
        probability = positive_class_probability(model, payload)
        return PredictionResponse(
            request_id=request_id,
            model_name=resolved_settings.name,
            model_version=resolved_settings.version,
            prediction=prediction,
            prediction_label=prediction_label(prediction),
            sold_within_30_days_probability=probability,
        )

    return app


def settings_from_env() -> ModelSettings:
    model_name = os.environ.get("BASELINE_MODEL_NAME", "housing-sale-baseline")
    model_version = os.environ.get("BASELINE_MODEL_VERSION")
    if not model_version:
        raise RuntimeError("BASELINE_MODEL_VERSION is required so serving uses an explicit MLflow model version")
    return ModelSettings(name=model_name, version=model_version)


def get_settings(app: FastAPI) -> ModelSettings:
    if app.state.model_settings is None:
        app.state.model_settings = settings_from_env()
    return app.state.model_settings


def load_model_once(app: FastAPI):
    if app.state.model is None:
        app.state.model = app.state.model_loader(get_settings(app).uri)
    return app.state.model


def positive_class_probability(model, payload: HousingSaleFeatures) -> float | None:
    if not hasattr(model, "predict_proba"):
        return None
    probabilities = model.predict_proba([payload.as_model_row()])
    return float(probabilities[0][1])


def prediction_label(prediction: int) -> str:
    if prediction == 1:
        return "listing sold within 30 days"
    return "listing did not sell within 30 days"


app = create_app()
