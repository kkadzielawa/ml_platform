# Table storage route

## Selected route

This study platform uses **Parquet files plus lakeFS** for tabular datasets. A published dataset is
a complete set of Parquet objects beneath an immutable dataset-version prefix in a lakeFS
repository. The lakeFS commit that records those objects is the reproducibility boundary.

Record all three values wherever a job consumes or publishes a dataset:

- repository name;
- Parquet dataset path and immutable dataset version;
- lakeFS commit ID.

Read a reproducible input with the recorded commit ID. `main` is a convenience branch for the most
recent publication and must not be used as evidence of a historical training or evaluation input.

## Publication rules

1. Transform and validate a complete candidate dataset before creating its publishing commit.
2. Write a new Parquet dataset version, such as `curated/housing-sale-features/v0002/`, rather than
   editing a previously published version.
3. Commit the objects to lakeFS and record the returned commit ID in the run manifest, catalog
   lineage, and any downstream experiment metadata.
4. Merge only a reviewed complete dataset version into `main`.
5. Preserve the prior commit so a consumer can reconstruct the earlier manifest and Parquet files.

## Update and merge limitations

Parquet plus lakeFS provides object-level versioned snapshots. It does not make the objects a
transactional table format.

- A correction rewrites a complete new dataset version; it is not a row-level `UPDATE` or `DELETE`.
- Multiple writers must not independently modify the same dataset path and assume lakeFS can merge
  their Parquet contents correctly. Coordinate a single publisher or create separate candidate
  versions and choose one deliberately.
- lakeFS does not supply table-level schema enforcement, predicate conflict detection, compaction,
  hidden partition management, or atomic semantic updates across a dataset's Parquet files.
- Dataset contracts and the compatibility guidance in `parquet.md` remain the source of truth for
  schema and partition evolution.

Use the Iceberg route only when those table semantics are required and there is a reviewed choice of
catalog, query engine, and operational ownership.
