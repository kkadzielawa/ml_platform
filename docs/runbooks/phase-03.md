# Phase 3 runbook: versioned data path

Phase 3 combines the platform's data classification, scoped object storage, lakeFS versioning,
Parquet transforms, quality gates, OpenLineage, OpenMetadata, and read-by-commit behavior.

## Prerequisites

The Kind cluster must already contain the Phase 3 services from earlier issues. Check the individual
services if necessary:

```bash
make test-lakefs
RUN_OPENMETADATA_INTEGRATION=1 make test-openmetadata
```

The end-to-end target does not reapply charts or require a browser session. This keeps it focused on
behavior and avoids changing already-running study services.

## Run the automated proof

```bash
make e2e-phase-03
```

The test automatically:

1. ingests the valid housing-sale source into a uniquely named lakeFS repository;
2. transforms it to Parquet and verifies the quality-gated commit, manifest, and `START`/`COMPLETE`
   OpenLineage events;
3. submits a deliberately malformed source and verifies that no curated commit or run manifest is
   created, while a sanitized `FAIL` lineage event is emitted;
4. verifies a separate Parquet plus lakeFS read-by-commit snapshot;
5. queries the deployed OpenMetadata catalog through its automated API tests for owner, quality, and
   raw-to-curated lineage;
6. publishes two releases and reproduces the older release by its immutable data commit.

All temporary lakeFS repositories created by the proof are deleted automatically. No manual UI work
is part of the acceptance check.

## Evidence

The compact report is written to:

```text
/tmp/ml-platform-phase-03/latest.json
```

It records the good and bad ingestion outcomes, the output data commit and run ID, results of the
snapshot and catalog checks, and the location of the detailed 03.12 reproducibility report. To use a
different report location, set `PHASE_03_E2E_REPORT` before invoking the target.

## Failure triage

- If lakeFS is unavailable, run `make apply-lakefs` and wait for its deployment before retrying.
- If the catalog check fails, run `make apply-openmetadata`, then retry once its server is available.
- The deliberately malformed input failing is expected. The e2e test fails only if it is accepted,
  writes a manifest, creates curated output, or emits unsanitized lineage evidence.
