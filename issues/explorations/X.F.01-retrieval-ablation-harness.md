---
id: "X.F.01"
phase: "X"
title: "Create the advanced-retrieval ablation harness"
status: "optional"
depends_on: ["09.16"]
route: "required"
---

# X.F.01 — Create the advanced-retrieval ablation harness

## Outcome

Run dense, sparse, hybrid, reranker, and future routes on one immutable corpus/golden set with stage latency/cost.

## Allowed paths

- `explorations/retrieval/common/**`
- `tests/explorations/retrieval/common/**`

## Deliverables

- Run dense, sparse, hybrid, reranker, and future routes on one immutable corpus/golden set with stage latency/cost.
- Support train/dev/test query partitions.

## Acceptance

- One config change produces attributable result diff.
- Final test set cannot tune route parameters.

## Verify

```bash
make test-exploration-retrieval-harness
```

## Non-goals

- Adding a retrieval method.

