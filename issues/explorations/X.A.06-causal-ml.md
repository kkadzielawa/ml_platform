---
id: "X.A.06"
phase: "X"
title: "Build a causal-inference study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.A.06 — Build a causal-inference study

## Outcome

Generate data from a known causal graph and estimate treatment effects with naive association and DoWhy/EconML method.

## Allowed paths

- `explorations/specialized_ml/causal/**`
- `tests/explorations/causal/**`

## Deliverables

- Generate data from a known causal graph and estimate treatment effects with naive association and DoWhy/EconML method.
- Run refutation/sensitivity checks.

## Acceptance

- True effect is known and recovery tolerance declared.
- Report distinguishes assumptions from observed data.

## Verify

```bash
make test-exploration-causal
```

## Non-goals

- Making causal claims on real observational data.

