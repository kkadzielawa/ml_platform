# Data reproducibility study report

Issue `03.12` proves the platform's selected Parquet plus lakeFS route can reproduce a historical
curated dataset. It is deliberately a correctness exercise, not a performance benchmark.

Run it from the repository root:

```bash
make e2e-data-reproducibility
```

The command creates a unique temporary lakeFS repository and publishes two complete versions of the
housing-sale feature dataset. Source `v0002` changes one documented listing price from source
`v0001`; therefore the curated content checksum must change. It then reads `v0001` by its recorded
lakeFS commit ID after `v0002` has been published. The check compares the reconstructed schema, row
count, and deterministic content checksum with the original `v0001` output.

## Evidence report

The command writes a machine-readable report to
`/tmp/ml-platform-data-reproducibility/latest.json` by default. Set
`DATA_REPRODUCIBILITY_REPORT` to choose another local report path. The report records, for each
release:

- the dataset and source versions;
- the immutable data commit and later evidence commit;
- a `repository` / `ref` / `path` link to its run manifest;
- a `repository` / `ref` / `path` link to its OpenLineage JSONL events;
- the schema, row count, and content checksum.

The report's reproduction section names the exact old `data_commit` it read. It never treats the
moving `main` branch as historical evidence.

## Inspecting an evidence run

The default workflow deletes its generated lakeFS repository after validation, so repeated study runs
do not leave test data behind. To keep it long enough to inspect with the lakeFS UI or API, run:

```bash
KEEP_DATA_REPRODUCIBILITY_REPOSITORY=1 make e2e-data-reproducibility
```

Open the report, then use the recorded repository, evidence commit, and paths below
`evidence/data-reproducibility/runs/` to find the run manifest and OpenLineage events. Use the
recorded **data** commit—not the evidence commit or `main`—to read the historical Parquet release.
After inspection, delete that uniquely named `study-data-reproducibility-*` repository in lakeFS.

## Interpretation

A passing report demonstrates object-level reproducibility: the same release can be reconstructed
after a later release exists. It does not add Iceberg-style row updates, concurrent-writer conflict
detection, or transactional table semantics. Those are intentionally outside the selected 03.11.a
route.
