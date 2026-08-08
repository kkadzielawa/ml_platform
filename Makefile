export POSTGRES_DB ?= ml_platform_local
export POSTGRES_USER ?= ml_platform_app
export POSTGRES_PASSWORD ?= local-dev-postgres-password
export POSTGRES_PORT ?= 5432
export GARAGE_RPC_SECRET ?= 1111111111111111111111111111111111111111111111111111111111111111
export GARAGE_ADMIN_TOKEN ?= local-dev-garage-admin-token
export GARAGE_METRICS_TOKEN ?= local-dev-garage-metrics-token
export GARAGE_KEY_ID ?= GK111111111111111111111111
export GARAGE_SECRET_KEY ?= 2222222222222222222222222222222222222222222222222222222222222222
export GARAGE_BUCKET ?= ml-platform-artifacts
export GARAGE_S3_REGION ?= garage
export GARAGE_S3_ENDPOINT ?= http://127.0.0.1:3900
export GARAGE_S3_PORT ?= 3900
export GARAGE_ADMIN_PORT ?= 3903
export MLFLOW_PORT ?= 5000
export MLFLOW_TRACKING_URI ?= http://127.0.0.1:$(MLFLOW_PORT)
export PROMETHEUS_PORT ?= 19090
export PROMETHEUS_URL ?= http://127.0.0.1:$(PROMETHEUS_PORT)
export GRAFANA_PORT ?= 13000
export GRAFANA_URL ?= http://127.0.0.1:$(GRAFANA_PORT)
export GRAFANA_ADMIN_USER ?= admin
export GRAFANA_ADMIN_PASSWORD ?= local-dev-grafana-password
export BASELINE_TRAIN_IMAGE ?= ghcr.io/mlflow/mlflow:v3.13.0@sha256:a5cd51cd14b570ec4374a4dad76a8ff92b7a0a6f66904c871cee18703487d23f
export BASELINE_TRAIN_PACKAGES ?= boto3==1.43.67 pytest==8.4.2
export BASELINE_SERVE_PACKAGES ?= boto3==1.43.67 fastapi==0.115.6 httpx==0.28.1 pytest==8.4.2 uvicorn==0.32.1
export BASELINE_MODEL_NAME ?= housing-sale-baseline
export BASELINE_SERVE_PORT ?= 18080

.PHONY: test test-versions test-contracts test-baseline-data compose-up-postgres test-postgres compose-up-object-store test-object-store compose-up-mlflow test-mlflow compose-up-observability test-observability train-baseline test-baseline-training serve-baseline serve-baseline-smoke
test:
	python -m pytest

test-versions:
	python -m pytest tests/config

test-contracts:
	python -m pytest tests/contracts

test-baseline-data:
	python -m pytest tests/examples

compose-up-postgres:
	docker compose up -d postgres
	bash config/postgres/wait-for-postgres.sh

test-postgres:
	bash tests/integration/postgres/smoke.sh

compose-up-object-store:
	docker compose up -d garage
	bash config/garage/bootstrap.sh

test-object-store:
	python tests/integration/object_store/smoke_s3.py

compose-up-mlflow: compose-up-postgres compose-up-object-store
	docker compose up -d mlflow
	bash config/mlflow/wait-for-mlflow.sh

test-mlflow:
	docker compose exec -T mlflow python /opt/mlflow/tests/smoke_mlflow.py

compose-up-observability:
	docker compose up -d prometheus grafana
	bash config/prometheus/wait-for-prometheus.sh
	bash config/grafana/wait-for-grafana.sh

test-observability:
	python tests/integration/observability/smoke_observability.py

train-baseline: compose-up-mlflow
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace -e PYTHONPATH=/workspace/src -e MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT) -e MLFLOW_S3_ENDPOINT_URL="$(GARAGE_S3_ENDPOINT)" -e AWS_ACCESS_KEY_ID="$(GARAGE_KEY_ID)" -e AWS_SECRET_ACCESS_KEY="$(GARAGE_SECRET_KEY)" -e AWS_DEFAULT_REGION="$(GARAGE_S3_REGION)" -e GIT_PYTHON_REFRESH=quiet "$(BASELINE_TRAIN_IMAGE)" sh -ec 'python -c "import boto3, sklearn" || python -m pip install --no-cache-dir $(BASELINE_TRAIN_PACKAGES); python examples/sklearn_baseline/train.py --config examples/sklearn_baseline/config.yaml'

test-baseline-training: compose-up-mlflow
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace -e PYTHONPATH=/workspace/src -e RUN_BASELINE_INTEGRATION=1 -e MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT) -e MLFLOW_S3_ENDPOINT_URL="$(GARAGE_S3_ENDPOINT)" -e AWS_ACCESS_KEY_ID="$(GARAGE_KEY_ID)" -e AWS_SECRET_ACCESS_KEY="$(GARAGE_SECRET_KEY)" -e AWS_DEFAULT_REGION="$(GARAGE_S3_REGION)" -e GIT_PYTHON_REFRESH=quiet "$(BASELINE_TRAIN_IMAGE)" sh -ec 'python -c "import boto3, pytest, sklearn" || python -m pip install --no-cache-dir $(BASELINE_TRAIN_PACKAGES); python -m pytest examples/sklearn_baseline/tests'

serve-baseline: compose-up-mlflow
	@if [ -z "$(BASELINE_MODEL_VERSION)" ]; then echo "BASELINE_MODEL_VERSION is required, for example: BASELINE_MODEL_VERSION=3 make serve-baseline"; exit 2; fi
	docker compose up -d baseline-serving
	@for attempt in $$(seq 1 30); do python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$(BASELINE_SERVE_PORT)/healthz', timeout=2).read()" >/dev/null 2>&1 && exit 0; sleep 2; done; echo "baseline-serving did not become healthy"; exit 1
	@echo "Baseline serving API: http://127.0.0.1:$(BASELINE_SERVE_PORT)"
	@echo "Health: curl http://127.0.0.1:$(BASELINE_SERVE_PORT)/healthz"
	@echo "Metadata: curl http://127.0.0.1:$(BASELINE_SERVE_PORT)/metadata"

serve-baseline-smoke: train-baseline
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace -e PYTHONPATH=/workspace/src:/workspace -e RUN_BASELINE_SERVICE_INTEGRATION=1 -e BASELINE_MODEL_NAME="$(BASELINE_MODEL_NAME)" -e MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT) -e MLFLOW_S3_ENDPOINT_URL="$(GARAGE_S3_ENDPOINT)" -e AWS_ACCESS_KEY_ID="$(GARAGE_KEY_ID)" -e AWS_SECRET_ACCESS_KEY="$(GARAGE_SECRET_KEY)" -e AWS_DEFAULT_REGION="$(GARAGE_S3_REGION)" -e GIT_PYTHON_REFRESH=quiet "$(BASELINE_TRAIN_IMAGE)" sh -ec 'python -c "import boto3, fastapi, httpx, pytest, sklearn, uvicorn" || python -m pip install --no-cache-dir $(BASELINE_SERVE_PACKAGES); export BASELINE_MODEL_VERSION="$$(python -m examples.sklearn_baseline.service.resolve_model_version)"; python -m pytest examples/sklearn_baseline/tests/test_service.py'
