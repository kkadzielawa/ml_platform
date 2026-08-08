---
id: "X.A.03"
phase: "X"
title: "Build a two-stage recommender study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.A.03 — Build a two-stage recommender study

## Outcome

Implement popularity baseline, candidate retrieval, and ranking on a small licensed/generated implicit-feedback dataset.

## Allowed paths

- `explorations/specialized_ml/recommender/**`
- `tests/explorations/recommender/**`

## Deliverables

- Implement popularity baseline, candidate retrieval, and ranking on a small licensed/generated implicit-feedback dataset.
- Measure recall@k, nDCG, coverage, diversity, novelty, and latency.

## Acceptance

- User/time split prevents interaction leakage.
- Cold-user/item behavior is explicit.

## Verify

```bash
make test-exploration-recommender
```

## Non-goals

- Online personalization.

