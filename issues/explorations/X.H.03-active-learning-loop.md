---
id: "X.H.03"
phase: "X"
title: "Implement one active-learning iteration"
status: "optional"
depends_on: ["X.H.02", "00.15"]
route: "required"
---

# X.H.03 — Implement one active-learning iteration

## Outcome

Train baseline, score unlabeled pool, select by uncertainty plus diversity/random control, ingest adjudicated labels, retrain, and compare label efficiency.

## Allowed paths

- `explorations/human_feedback/active_learning/**`
- `tests/explorations/human_feedback/active_learning/**`

## Deliverables

- Train baseline, score unlabeled pool, select by uncertainty plus diversity/random control, ingest adjudicated labels, retrain, and compare label efficiency.
- Version every selection/label/model.

## Acceptance

- Selection excludes held-out test.
- Comparison uses equal label budget.

## Verify

```bash
make test-exploration-active-learning
```

## Non-goals

- Continuous production labeling.

