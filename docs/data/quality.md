# Data Quality

Issue `03.07.a` selects Great Expectations as the local data-quality route.

## Purpose

The data-quality layer validates curated datasets before they are committed, published, or used by training jobs. It checks things that schema validation alone cannot fully capture:

- exact expected columns;
- row counts;
- required non-null fields;
- uniqueness;
- numeric ranges;
- categorical value sets;
- leakage-oriented feature names.

## Local implementation

The suite lives at:

```text
config/great_expectations/housing_sale_suite.yaml
```

The runner lives under:

```text
src/ml_platform/data_quality/
```

Run:

```bash
make test-data-quality
```

The tests generate the deterministic Parquet dataset from `03.06`, validate the good fixture, seed defects, and verify each defect fails the intended expectation.

## Result shape

Validation emits compact JSON with:

- validator name and version;
- suite name;
- dataset ID;
- success/failure;
- evaluated/successful/failed expectation counts;
- per-expectation success flags and aggregate summaries.

It does not include raw failing row values. This keeps the validation path safe for future confidential or restricted datasets.

## Why this is still local

This issue does not deploy a data-quality server or use Great Expectations Cloud. It creates a small local validation path that later ingestion and pipeline issues can call before publishing data.
