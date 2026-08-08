---
id: "X.F.07"
phase: "X"
title: "Publish advanced retrieval ablations"
status: "optional"
depends_on: ["X.F.02", "X.F.03", "X.F.06"]
route: "required"
---

# X.F.07 — Publish advanced retrieval ablations

## Outcome

Compare dense/sparse/hybrid/late-interaction/SQL/graph routes by question class, quality, latency, storage, and complexity.

## Allowed paths

- `docs/experiments/advanced-retrieval.md`
- `explorations/retrieval/results/**`
- `tests/explorations/retrieval/report/**`

## Deliverables

- Compare dense/sparse/hybrid/late-interaction/SQL/graph routes by question class, quality, latency, storage, and complexity.
- Attribute improvements to stages.

## Acceptance

- Report rebuilds from raw results.
- Graph/SQL recommendation is limited to tasks where structure helps.

## Verify

```bash
make test-exploration-retrieval-report
```

## Non-goals

- Choosing a universal retriever.

