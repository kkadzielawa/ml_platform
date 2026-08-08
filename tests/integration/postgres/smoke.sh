#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

docker compose exec -T \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  postgres \
  psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" <<'SQL'
CREATE TABLE IF NOT EXISTS ml_platform.postgres_smoke_test (
    id integer PRIMARY KEY,
    note text NOT NULL
);

INSERT INTO ml_platform.postgres_smoke_test (id, note)
VALUES (1, 'postgres smoke ok')
ON CONFLICT (id) DO UPDATE SET note = EXCLUDED.note;

SELECT note FROM ml_platform.postgres_smoke_test WHERE id = 1;

DROP TABLE ml_platform.postgres_smoke_test;
SQL
