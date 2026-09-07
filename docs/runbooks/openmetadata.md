# OpenMetadata runbook

Issue `03.10` introduces OpenMetadata OSS as the local metadata catalog.

## Purpose

OpenMetadata is where the platform can search and explain data assets. In this study setup it catalogs the baseline housing-sale dataset, owner, schema, quality result, and lineage from raw CSV inputs to curated Parquet output.

## Local deployment shape

The local route uses:

- OpenMetadata server from the pinned upstream Helm chart;
- CloudNativePG PostgreSQL for OpenMetadata metadata;
- single-node OpenSearch from the OpenMetadata dependencies chart;
- Keycloak OIDC as the interactive identity provider;
- no Airflow, broad source connectors, or enterprise-only features.

## Local commands

```bash
make apply-openmetadata
make test-openmetadata
```

After deployment, keep both port-forwards running while using browser SSO. OpenMetadata uses
the first address for the UI and the second address as the browser-facing Keycloak authority:

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-data svc/openmetadata 8585:8585
```

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-system svc/keycloak 18081:8080
```

Then open:

```text
http://127.0.0.1:8585
```

Choose the Keycloak sign-in option. The study user is `admin` with the value of
`OPENMETADATA_ADMIN_PASSWORD` (the default is `local-dev-openmetadata-admin-password`).
The Keycloak bootstrap-admin password is for the Keycloak administration console and is a
different credential.

The browser and the OpenMetadata server are on different networks: the browser can reach the
local Keycloak port-forward, while the server must reach the Kubernetes Service. The
`openmetadata-oidc-discovery-adapter` is a small internal reverse proxy that preserves the
browser-facing authorization URL and rewrites only OIDC back-channel endpoints for the server.
`make apply-openmetadata` waits for it and synchronizes the persisted OpenMetadata OIDC setting.
If an earlier deployment used a different OIDC route, rerun `make apply-openmetadata`; it restarts
OpenMetadata only when the persisted setting needs to change.

## Catalog seed

The seed payload lives in:

```text
clusters/dev/openmetadata/catalog-seed-configmap.yaml
```

It describes:

- owner: `platform-learners`;
- service: `ml-platform-lakefs`;
- database/repository: `housing-sale-ingestion`;
- schema: `curated`;
- table: `housing-sale-features-v0001`;
- quality suite: `housing_sale_features_quality`;
- lineage inputs: raw train/test CSVs;
- lineage output: curated Parquet dataset.

## API registration

`make apply-openmetadata` runs two stdlib-only registration scripts after the services are available:

- `clusters/dev/openmetadata/register_openmetadata_oidc.py` registers the local OpenMetadata OIDC client and admin user in Keycloak.
- `clusters/dev/openmetadata/sync_oidc_configuration.py` makes the persisted OpenMetadata OIDC authority and discovery URL match the local browser and cluster routes.
- `clusters/dev/openmetadata/register_baseline_metadata.py` seeds the baseline catalog assets into OpenMetadata.

For local study use, the baseline metadata script can open temporary port-forwards to Keycloak and OpenMetadata, request a local admin token, and register the seed payload without you manually copying a token.

To run the seed step directly:

```bash
OPENMETADATA_ADMIN_PASSWORD=local-dev-openmetadata-admin-password \
python clusters/dev/openmetadata/register_baseline_metadata.py
```

You can also bypass the local Keycloak flow by providing an explicit OpenMetadata API URL and JWT token:

```bash
OPENMETADATA_URL=http://127.0.0.1:8585/api
OPENMETADATA_JWT_TOKEN=<token>
```

Do not commit personal, bot, or copied UI tokens.

## Notes

OpenMetadata is heavier than the earlier services because it needs both a relational store and a search backend. If the laptop is under pressure, stop other phase services before applying this issue.

## Non-goals

This lab does not configure production HA, backups, external ingress, full connector ingestion, Airflow, SAML, SCIM, or enterprise-only governance features.
