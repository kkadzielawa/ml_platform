export POSTGRES_DB ?= ml_platform_local
export POSTGRES_USER ?= ml_platform_app
export POSTGRES_PASSWORD ?= local-dev-postgres-password
export POSTGRES_PORT ?= 5432

.PHONY: test test-versions test-contracts compose-up-postgres test-postgres
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
