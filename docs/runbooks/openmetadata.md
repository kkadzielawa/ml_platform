# OpenMetadata runbook

Issue `03.10` introduces OpenMetadata OSS as the local metadata catalog.

## Purpose

OpenMetadata is where the platform can search and explain data assets. In this study setup it catalogs the baseline housing-sale dataset, owner, schemas, an explicitly labelled quality fixture result, and lineage from raw CSV inputs to curated Parquet output.

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
Because the adapter mounts its NGINX configuration with a `subPath`, `make apply-openmetadata`
explicitly restarts the adapter after applying its ConfigMap, waits for the replacement pod, and
then synchronizes the persisted OpenMetadata OIDC setting. Reapplying therefore causes a brief
adapter-only local interruption even when the configuration is unchanged.
If an earlier deployment used a different OIDC route, rerun `make apply-openmetadata`; it restarts
OpenMetadata only when the persisted setting needs to change. On a cold local JVM start, that
replacement can take more than five minutes; the synchronizer waits for up to ten minutes and
fails rather than reporting a successful configuration change before the server is ready.

## Catalog seed

The seed payload lives in:

```text
clusters/dev/openmetadata/catalog-seed-configmap.yaml
```

It describes:

- owner: `platform-learners`;
- service: `ml-platform-lakefs`;
- database/repository: `housing-sale-ingestion`;
- raw schema and train/test input tables;
- schema: `curated`;
- table: `housing-sale-features-v0001`;
- quality suite: `housing_sale_features_quality`;
- quality evidence: `fixture` from the file-based suite declaration;
- pipeline: `baseline-versioned-ingestion`;
- lineage commit marker: `fixture-commit-0001`;
- lineage inputs: raw train/test CSVs;
- lineage output: curated Parquet dataset.

## API registration

`make apply-openmetadata` runs two stdlib-only registration scripts after the services are available:

- `clusters/dev/openmetadata/register_openmetadata_oidc.py` registers the local OpenMetadata OIDC client and admin user in Keycloak.
- `clusters/dev/openmetadata/sync_oidc_configuration.py` makes the persisted OpenMetadata OIDC authority and discovery URL match the local browser and cluster routes.
- `clusters/dev/openmetadata/register_baseline_metadata.py` upserts the baseline catalog assets, quality test case/result, pipeline identity, and raw-to-curated lineage edges into OpenMetadata.

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

The default `make test-openmetadata` command runs offline manifest checks and skips the live
cluster test. To verify the deployed catalog and retrieve the registered quality and lineage
entities, run:

```bash
RUN_OPENMETADATA_INTEGRATION=1 make test-openmetadata
```

The quality result is deliberately marked `fixture`; it proves the catalog registration path,
not that OpenMetadata executed the local validator. A future measured quality report can replace
the seed result without changing the catalog entity shape. The fixture has a fixed observed time,
so rerunning registration reads and verifies the matching stored result instead of overwriting it.

## Notes

OpenMetadata is heavier than the earlier services because it needs both a relational store and a search backend. If the laptop is under pressure, stop other phase services before applying this issue.

## Non-goals

This lab does not configure production HA, backups, external ingress, full connector ingestion, Airflow, SAML, SCIM, or enterprise-only governance features.
