---
id: "X.B.03"
phase: "X"
title: "Build a tiny pretraining corpus pipeline"
status: "optional"
depends_on: ["X.B.01", "03.13"]
route: "required"
---

# X.B.03 — Build a tiny pretraining corpus pipeline

## Outcome

Create licensed corpus ingestion, normalization, exact deduplication, split, tokenization, packing, and contamination checks.

## Allowed paths

- `explorations/pretraining/data/**`
- `tests/explorations/pretraining/data/**`

## Deliverables

- Create licensed corpus ingestion, normalization, exact deduplication, split, tokenization, packing, and contamination checks.
- Emit immutable shards and manifest.

## Acceptance

- Repeated build has identical shard checksums.
- Held-out strings are not exact matches in training.

## Verify

```bash
make test-exploration-pretraining-data
```

## Non-goals

- Web-scale cleaning.

