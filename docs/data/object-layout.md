# Object Layout

This document defines the logical object layout for platform-owned data assets. Later issues will create buckets and wire services to these prefixes.

## Bucket ownership

| Bucket | Purpose | Default owner | Allowed classes |
|---|---|---|---|
| `ml-platform-public` | Shareable examples, documentation exports, public schemas, and approved demo datasets. | `platform-docs` | `public` |
| `ml-platform-internal` | Run manifests, aggregate metrics, SBOMs, scans, reports, and operational metadata. | `platform-ops` | `public`, `internal` |
| `ml-platform-confidential` | Model artifacts, experiment outputs, curated datasets, evaluation slices, and backups. | `model-platform` | `public`, `internal`, `confidential` |
| `ml-platform-restricted` | Redacted pointers and controlled metadata for secrets or sensitive raw inputs. | `security-platform` | `restricted` |

Raw secret values should live in the secret manager, not in object storage. If object storage must reference restricted material, store only redacted metadata, object IDs, checksums, and policy decisions.

## Prefix conventions

Use lowercase portable slugs. Dataset versions use `v0001` style versions. Model versions use semantic versions or registry versions recorded in the asset metadata.

```text
projects/<project>/datasets/<dataset-id>/versions/<dataset-version>/
projects/<project>/datasets/<dataset-id>/versions/<dataset-version>/splits/<split>/
projects/<project>/datasets/<dataset-id>/versions/<dataset-version>/schemas/
projects/<project>/models/<model-id>/versions/<model-version>/
projects/<project>/runs/<run-id>/manifests/
projects/<project>/runs/<run-id>/metrics/
projects/<project>/runs/<run-id>/artifacts/
projects/<project>/experiments/<experiment-id>/
projects/<project>/observability/
projects/<project>/supply-chain/<artifact-id>/
projects/<project>/backups/<system>/<backup-id>/
projects/<project>/secrets/<secret-id>/
```

## Required asset metadata

Every reusable data asset should carry metadata matching `contracts/data-asset.schema.json`:

- `dataset_id` or other stable `asset_id`;
- immutable `version`;
- `classification`;
- owning team or component;
- bucket and prefix;
- checksums for files or partitions;
- schema identifier and schema version;
- license and provenance;
- retention policy and review date;
- lineage links to source assets, run IDs, or code commits when available.

## Dataset ID and version rules

- Use a stable dataset ID such as `housing-sale-synthetic`.
- Do not encode mutable states such as `latest`, `new`, or `final` in the ID.
- Use versions such as `v0001`, `v0002`, and never overwrite the meaning of a version.
- If the schema changes incompatibly, create a new dataset version.
- If only metadata is corrected, keep the data version and update metadata with a new review timestamp.

## Checksums and schemas

- Record SHA-256 checksums for every immutable object or partition.
- Record a schema name and version even for simple CSV or JSON fixtures.
- Store schema files under the dataset version prefix when they describe data objects.
- Store platform-wide reusable schema contracts under `contracts/`.

## License and provenance

Record:

- source type, such as `synthetic`, `public-download`, `generated`, `internal-upload`, or `derived`;
- source URI or local generator path;
- generation or ingestion timestamp;
- license expression or review status;
- attribution requirements;
- parent dataset IDs, run IDs, model IDs, or code commits.

## Phase 0 object placement

| Artifact | Bucket | Prefix |
|---|---|---|
| synthetic housing-sale data | `ml-platform-public` | `projects/ml-platform/datasets/housing-sale-synthetic/versions/v0001/` |
| dataset metadata | `ml-platform-internal` | `projects/ml-platform/datasets/housing-sale-synthetic/versions/v0001/metadata/` |
| run manifests | `ml-platform-internal` | `projects/ml-platform/runs/<run-id>/manifests/` |
| run metrics and params | `ml-platform-internal` | `projects/ml-platform/runs/<run-id>/metrics/` |
| model artifacts | `ml-platform-confidential` | `projects/ml-platform/models/housing-sale-baseline/versions/<model-version>/` |
| PostgreSQL backups | `ml-platform-confidential` | `projects/ml-platform/backups/postgres/<backup-id>/` |
| supply-chain evidence | `ml-platform-internal` | `projects/ml-platform/supply-chain/build-fixture/` |
| redacted secret references | `ml-platform-restricted` | `projects/ml-platform/secrets/<secret-id>/` |
