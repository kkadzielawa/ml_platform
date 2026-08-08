---
id: "X.A.04"
phase: "X"
title: "Build an anomaly-detection study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.A.04 — Build an anomaly-detection study

## Outcome

Compare robust statistical, isolation-based, and optional autoencoder methods on controlled anomalies.

## Allowed paths

- `explorations/specialized_ml/anomaly/**`
- `tests/explorations/anomaly/**`

## Deliverables

- Compare robust statistical, isolation-based, and optional autoencoder methods on controlled anomalies.
- Evaluate precision/recall under class imbalance and detection delay.

## Acceptance

- Labels are used only for evaluation/tuning as documented.
- Threshold selection is separate from final evaluation.

## Verify

```bash
make test-exploration-anomaly
```

## Non-goals

- Claiming unknown real anomalies are covered.

