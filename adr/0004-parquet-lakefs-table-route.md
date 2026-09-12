# ADR 0004: Parquet plus lakeFS as the study table route

## Status

Accepted

## Context

The study platform publishes small and medium tabular datasets as Parquet objects in lakeFS-backed
object storage. The current ingestion path validates a complete dataset, writes Parquet files, and
records the resulting lakeFS commit in its run manifest.

The alternative route for issue `03.11` is an Iceberg table format and catalog. Iceberg would add
table metadata, transaction coordination, and richer query-engine integration. Those capabilities
are valuable when workloads need concurrent writers, row-level changes, partition evolution, or
large analytical tables. They are not yet required to study immutable dataset publication,
provenance, quality gates, and reproducible training inputs.

## Decision

Select `03.11.a`: store each published dataset version as immutable Parquet files under a versioned
lakeFS path. Treat a lakeFS commit ID as the snapshot identifier. Training, evaluation, and catalog
records must retain the repository, Parquet path, and commit ID needed to reproduce an input.

Publish corrections and schema-breaking changes as a new dataset version and a new commit. A
consumer that needs stable input must read by the recorded commit, not the moving `main` branch.

## Consequences

This route is intentionally simple and keeps the existing lakeFS and Parquet learning slices useful.
It proves object-level versioned snapshots, not transactional table semantics.

- Do not update or delete individual rows inside a published Parquet file.
- Do not rely on automatic semantic merges when two writers change the same dataset path; serialize
  publication or resolve the conflict by producing a new complete version.
- Do not treat a lakeFS merge as a multi-file table transaction with schema enforcement,
  predicate-based conflict detection, compaction, or row-level mutation.
- Partition and schema compatibility remain governed by `docs/data/parquet.md` and dataset
  contracts; lakeFS records object revisions but does not validate those conventions.

Revisit the Iceberg route when a workload needs concurrent writers, atomic multi-file table commits,
row-level changes, partition evolution at scale, or direct table-catalog integration with query
engines.
