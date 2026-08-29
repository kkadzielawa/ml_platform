# Baseline data transform example

Issue `03.06` adds a deterministic local transform over the Phase 0 synthetic housing-sale CSV fixture.

Run:

```bash
make transform-baseline-data
```

This writes a curated Parquet dataset under:

```text
examples/data_transform/output/housing-sale-features/
```

The transform records row counts, a schema hash, input checksums, output checksums, and a metadata checksum. The output directory is ignored by Git because it is generated.
