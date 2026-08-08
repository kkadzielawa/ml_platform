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

.PHONY: test test-versions test-contracts compose-up-postgres test-postgres compose-up-object-store test-object-store compose-up-mlflow test-mlflow
test:
	python -m pytest

test-versions:
	python -m pytest tests/config

test-contracts:
	python -m pytest tests/contracts

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
