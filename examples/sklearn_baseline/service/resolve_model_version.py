from __future__ import annotations

import os

from mlflow.tracking import MlflowClient


def latest_registered_version(model_name: str) -> str:
    versions = MlflowClient().search_model_versions(f"name = '{model_name}'")
    if not versions:
        raise RuntimeError(f"no registered MLflow model versions found for {model_name!r}")
    return str(max(int(version.version) for version in versions))


def main() -> None:
    model_name = os.environ.get("BASELINE_MODEL_NAME", "housing-sale-baseline")
    print(latest_registered_version(model_name))


if __name__ == "__main__":
    main()

