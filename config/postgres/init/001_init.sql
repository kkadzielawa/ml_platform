CREATE SCHEMA IF NOT EXISTS ml_platform;

CREATE TABLE IF NOT EXISTS ml_platform.schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO ml_platform.schema_migrations (version)
VALUES ('00.10')
ON CONFLICT (version) DO NOTHING;
