# Data Classification

This document defines the study platform's default data classes. It is a planning contract for later data, training, RAG, and agentic workflow issues; it does not create buckets or move existing artifacts.

## Classification levels

| Class | Meaning | Examples | Default retention | Logging rule |
|---|---|---|---|---|
| `public` | Approved for public documentation, demos, or redistribution. | Hand-written docs, public sample schemas, non-sensitive synthetic demo rows, public benchmark summaries. | Keep indefinitely unless superseded. | Raw values may be logged if they are already public and license-compatible. |
| `internal` | Platform-operational data that is not sensitive but is not meant as a public asset. | Run manifests, aggregate metrics, checksums, non-secret configs, generated SBOMs, e2e reports. | Keep at least 1 year for study reproducibility. | Raw values may be logged if they contain no secrets, personal data, or restricted payloads. |
| `confidential` | Data that could expose model behavior, private study decisions, proprietary inputs, or controlled datasets. | Model artifacts, experiment artifacts, curated datasets, feature sets, evaluation slices, prompt/index artifacts before review. | Keep only while needed for experiments; review after 180 days. | Prefer summaries, IDs, checksums, and schema names over raw values. |
| `restricted` | Secrets, credentials, raw personal data, regulated data, or data that could materially harm users if exposed. | Access keys, tokens, private user prompts, raw customer records, raw incident payloads, sensitive labels. | Keep for the shortest practical period; default 30 days unless a later policy narrows it. | Never log raw values. Log stable IDs, counts, hashes, redacted samples, and policy decisions only. |

## Handling expectations

- Classify each dataset, model artifact, run artifact, and derived object before a reusable workflow consumes it.
- Store the class in machine-readable metadata using `contracts/data-asset.schema.json`.
- Do not downgrade data unless a human review records why the lower class is safe.
- When several inputs are combined, the derived artifact inherits the highest input class unless a later issue implements an approved de-identification or aggregation rule.
- Restricted examples are allowed in tests only as fake fixtures and must still demonstrate redaction behavior rather than logging raw values.

## Phase 0 artifact mapping

| Phase 0 artifact | Default class | Logical prefix | Owner | Notes |
|---|---|---|---|---|
| Repository docs, ADRs, contracts, runbooks | `public` | `projects/ml-platform/docs/` | `platform-docs` | Study documentation is intended to be shareable unless a file explicitly says otherwise. |
| Synthetic housing-sale training dataset | `public` | `projects/ml-platform/datasets/housing-sale-synthetic/versions/v0001/` | `data-study` | Generated demo data with no real people or properties. |
| Synthetic housing-sale test dataset | `public` | `projects/ml-platform/datasets/housing-sale-synthetic/versions/v0001/splits/test/` | `data-study` | Same source and license posture as the training split. |
| Dataset metadata and schema summaries | `internal` | `projects/ml-platform/datasets/housing-sale-synthetic/versions/v0001/metadata/` | `data-study` | Operational metadata may mention local generation settings and validation results. |
| MLflow run manifests | `internal` | `projects/ml-platform/runs/<run-id>/manifests/` | `ml-platform-runtime` | Used for reproducibility and audit. |
| MLflow metrics and params | `internal` | `projects/ml-platform/runs/<run-id>/metrics/` | `ml-platform-runtime` | Metrics are safe by default, but must not include raw restricted payloads. |
| MLflow model artifacts | `confidential` | `projects/ml-platform/models/housing-sale-baseline/versions/<model-version>/` | `model-platform` | Treat weights and serialized model files as controlled until reviewed for release. |
| Prediction request/response examples | `confidential` | `projects/ml-platform/runs/<run-id>/serving-samples/` | `serving-platform` | Use synthetic examples only in Phase 0; future real payloads become `restricted`. |
| PostgreSQL metadata backups | `confidential` | `projects/ml-platform/backups/postgres/<backup-id>/` | `platform-ops` | May contain experiment metadata, run names, artifact URIs, and registry state. |
| Garage object storage objects | Inherit artifact class | See artifact-specific prefix | Owning component | Object storage is the backing store; individual object metadata carries the class. |
| Prometheus metrics and Grafana dashboards | `internal` | `projects/ml-platform/observability/` | `platform-ops` | Operational telemetry must not include raw restricted payloads. |
| Container image build fixture, SBOMs, scans, signatures | `internal` | `projects/ml-platform/supply-chain/build-fixture/` | `supply-chain` | Security metadata is not secret, but it is operational evidence. |
| Local credentials, tokens, access keys, and generated secret values | `restricted` | `projects/ml-platform/secrets/<secret-id>/` | `security-platform` | Do not store raw secret values in object storage or logs. Secret managers own real storage. |

## Restricted examples

Use redaction in docs, tests, logs, and run manifests:

| Do not log | Log instead |
|---|---|
| A raw access key or token | `secret_ref`, key version, rotation timestamp, and policy decision. |
| A raw email, address, or user prompt | salted hash, record ID, count, schema version, and redaction status. |
| A raw private document chunk for RAG | document ID, chunk ID, embedding model version, checksum, and access policy. |
