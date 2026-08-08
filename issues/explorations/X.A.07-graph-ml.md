---
id: "X.A.07"
phase: "X"
title: "Build a graph-ML study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.A.07 — Build a graph-ML study

## Outcome

Compare non-graph baseline with one small PyTorch Geometric/DGL node or graph task.

## Allowed paths

- `explorations/specialized_ml/graph_ml/**`
- `tests/explorations/graph_ml/**`

## Deliverables

- Compare non-graph baseline with one small PyTorch Geometric/DGL node or graph task.
- Track split method, neighborhood leakage, accuracy, memory, and latency.

## Acceptance

- Split prevents prohibited edge/neighborhood leakage.
- Baseline and GNN use equivalent labels.

## Verify

```bash
make test-exploration-graph-ml
```

## Non-goals

- Distributed graph training.

