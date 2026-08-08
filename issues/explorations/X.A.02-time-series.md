---
id: "X.A.02"
phase: "X"
title: "Build a time-series forecasting study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.A.02 — Build a time-series forecasting study

## Outcome

Compare seasonal-naive/statistical and one ML/neural forecast using temporal backtesting and probabilistic intervals.

## Allowed paths

- `explorations/specialized_ml/time_series/**`
- `tests/explorations/time_series/**`

## Deliverables

- Compare seasonal-naive/statistical and one ML/neural forecast using temporal backtesting and probabilistic intervals.
- Log horizon-wise metrics and interval coverage.

## Acceptance

- No future data enters features/fits.
- Advanced model must be compared under identical folds.

## Verify

```bash
make test-exploration-time-series
```

## Non-goals

- Production forecasting service.

