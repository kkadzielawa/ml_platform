# Parquet Dataset Conventions

This document defines the study platform's Parquet dataset metadata contract. It applies to future lakeFS-backed datasets, curated features, evaluation slices, and RAG-ready tabular assets.

## Dataset metadata

Every reusable Parquet dataset must have a small metadata document validated by `contracts/dataset.schema.json`. The metadata is intentionally separate from the data files so validators can check conventions without loading an entire dataset into memory.

Required metadata includes:

- dataset ID and version;
- classification and owner;
- storage bucket and prefix;
- file format and compression;
- partition columns and partition path template;
- schema fields with types, nullability, timestamp timezone rules, categorical encoding, and compatibility notes;
- schema evolution policy;
- small-file guidance;
- checksums or manifest-level checksums;
- license and provenance.

## Dataset IDs and versions

- Use lowercase portable dataset IDs such as `housing-sale-features`.
- Use immutable versions such as `v0001`, `v0002`.
- Do not use floating names such as `latest`, `final`, or `new`.
- If column meaning or compatibility changes, publish a new version.

## Partition naming

Partition directories must use Hive-style key/value segments:

```text
split=train/ingest_date=2026-08-27/
```

Rules:

- partition column names use lowercase snake case;
- partition values must not contain credentials, usernames, personal data, spaces, `..`, or duplicate slashes;
- prefer low-cardinality partitions such as `split`, `ingest_date`, `event_date`, or coarse region/category fields;
- avoid high-cardinality partitions such as user IDs, request IDs, raw addresses, or exact timestamps.

## Timestamps and timezones

- Store timestamps as logical UTC instants.
- Metadata must declare timestamp timezone behavior.
- Prefer `timestamp[us, tz=UTC]` for event and ingestion times.
- If a source field has local time semantics, preserve the original local value as a separate string or date column and document the conversion.
- Do not silently mix local timezones in one timestamp column.

## Nullability

- Every field must explicitly set `nullable`.
- Required identifiers and labels should usually be non-nullable.
- Optional source attributes may be nullable, but the meaning of null must be documented.
- Adding a nullable field is backward compatible.
- Removing a field or making a nullable field non-nullable is not backward compatible.

## Categorical encoding

Categorical columns must declare one of:

- `plain-string`: human-readable string values with documented allowed values when bounded;
- `dictionary`: Parquet dictionary encoding is expected but logical values remain strings;
- `integer-coded`: integer values map to documented category labels;
- `boolean`: true/false category;
- `none`: not categorical.

If integer-coded categories are used, metadata must include the code-to-label mapping. Do not use unexplained numeric category IDs.

## Small-file guidance

Tiny Parquet files are painful for query engines and object stores. Metadata must set target and maximum file sizes:

- target file size: 128-512 MiB for larger datasets;
- maximum file size: no more than 1024 MiB for this study platform;
- small local fixtures may be smaller, but they must be marked with `allow_small_files: true`.

The contract validates the policy and file-count metadata. It does not scan every Parquet object.

## Schema evolution compatibility

Backward-compatible examples:

- adding a nullable column;
- adding optional metadata;
- widening compatible numeric types when documented;
- adding new categorical values when consumers tolerate unknowns.

Breaking examples:

- removing a column;
- renaming a column without an alias/migration;
- changing a field from nullable to required;
- changing timestamp timezone semantics;
- changing categorical encoding without a migration.

Each dataset metadata file must include compatibility examples or notes so downstream training and evaluation jobs can decide whether a version change is safe.
