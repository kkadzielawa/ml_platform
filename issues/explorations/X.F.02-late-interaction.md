---
id: "X.F.02"
phase: "X"
title: "Study late-interaction retrieval"
status: "optional"
depends_on: ["X.F.01", "08.01"]
route: "required"
---

# X.F.02 — Study late-interaction retrieval

## Outcome

Pin/license-record a ColBERT-style model and compare candidate retrieval/reranking with the common baseline.

## Allowed paths

- `explorations/retrieval/late_interaction/**`
- `tests/explorations/retrieval/late_interaction/**`

## Deliverables

- Pin/license-record a ColBERT-style model and compare candidate retrieval/reranking with the common baseline.
- Measure index size, recall/nDCG, latency, and memory.

## Acceptance

- Same ACL filters and golden set are used.
- No improvement is reported honestly.

## Verify

```bash
make test-exploration-late-interaction
```

## Non-goals

- Production index scale.

