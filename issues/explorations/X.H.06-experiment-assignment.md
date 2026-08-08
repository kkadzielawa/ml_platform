---
id: "X.H.06"
phase: "X"
title: "Implement stable A/B assignment and exposure logging"
status: "optional"
depends_on: ["06.13", "05.09"]
route: "required"
---

# X.H.06 — Implement stable A/B assignment and exposure logging

## Outcome

Implement deterministic salted assignment by eligible unit, config/version, allocation, exclusions, and exposure-before-outcome logging.

## Allowed paths

- `explorations/product_experiments/assignment/**`
- `tests/explorations/product_experiments/assignment/**`

## Deliverables

- Implement deterministic salted assignment by eligible unit, config/version, allocation, exclusions, and exposure-before-outcome logging.
- Support shadow/no-exposure distinction.

## Acceptance

- Same unit/config remains stable and allocation matches tolerance.
- Outcome without exposure is excluded/flagged.

## Verify

```bash
make test-exploration-experiment-assignment
```

## Non-goals

- Production feature-flag service.

