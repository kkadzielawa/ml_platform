---
id: "X.A.01"
phase: "X"
title: "Create the specialized-ML experiment contract"
status: "optional"
depends_on: ["04.16"]
route: "required"
---

# X.A.01 — Create the specialized-ML experiment contract

## Outcome

Define required immutable data, leakage-safe split/backtest, naive baseline, metrics, MLflow logging, card, batch/serve demo, and resource cap.

## Allowed paths

- `explorations/specialized_ml/common/**`
- `tests/explorations/specialized_ml/**`
- `docs/experiments/specialized-ml.md`

## Deliverables

- Define required immutable data, leakage-safe split/backtest, naive baseline, metrics, MLflow logging, card, batch/serve demo, and resource cap.
- Provide a reusable project scaffold.

## Acceptance

- Scaffold test runs without external data.
- Each later project can fill the contract without changing it.

## Verify

```bash
make test-specialized-ml-scaffold
```

## Non-goals

- Implementing a domain model.

