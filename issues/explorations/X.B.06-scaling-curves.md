---
id: "X.B.06"
phase: "X"
title: "Measure tiny-model scaling curves"
status: "optional"
depends_on: ["X.B.04"]
route: "required"
---

# X.B.06 — Measure tiny-model scaling curves

## Outcome

Run bounded model-size/data-token experiments and fit/report empirical loss/compute trends.

## Allowed paths

- `explorations/pretraining/scaling/**`
- `tests/explorations/pretraining/scaling/**`
- `docs/experiments/tiny-scaling.md`

## Deliverables

- Run bounded model-size/data-token experiments and fit/report empirical loss/compute trends.
- Retain raw run IDs and confidence/variance.

## Acceptance

- All comparisons share tokenizer/eval protocol.
- Report does not extrapolate beyond evidence without labeling it.

## Verify

```bash
make test-exploration-scaling-report
```

## Non-goals

- Deriving universal scaling laws.

