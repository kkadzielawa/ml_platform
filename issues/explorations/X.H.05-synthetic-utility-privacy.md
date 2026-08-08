---
id: "X.H.05"
phase: "X"
title: "Evaluate synthetic data utility and privacy risk"
status: "optional"
depends_on: ["X.H.04"]
route: "required"
---

# X.H.05 — Evaluate synthetic data utility and privacy risk

## Outcome

Compare schema/statistical/task utility, rare-case coverage, nearest-neighbor/memorization proxy, and subgroup behavior.

## Allowed paths

- `explorations/synthetic/evaluation/**`
- `tests/explorations/synthetic/evaluation/**`
- `docs/experiments/synthetic-report.md`

## Deliverables

- Compare schema/statistical/task utility, rare-case coverage, nearest-neighbor/memorization proxy, and subgroup behavior.
- Include all-real/simple/synthetic training baselines.

## Acceptance

- Final task test is never generator input.
- Report does not equate distribution similarity with privacy.

## Verify

```bash
make test-exploration-synthetic-report
```

## Non-goals

- Formal privacy guarantee.

