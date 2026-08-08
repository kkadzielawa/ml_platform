---
id: "X.C.05"
phase: "X"
title: "Build and attack a tiny reward or verifier"
status: "optional"
depends_on: ["X.C.01"]
route: "required"
---

# X.C.05 — Build and attack a tiny reward or verifier

## Outcome

Implement a deterministic verifier for toy tasks or a tiny reward model and create adversarial reward-hacking examples.

## Allowed paths

- `explorations/alignment/reward/**`
- `tests/explorations/alignment/reward/**`

## Deliverables

- Implement a deterministic verifier for toy tasks or a tiny reward model and create adversarial reward-hacking examples.
- Measure calibration/ranking where applicable.

## Acceptance

- Verifier accepts correct and rejects seeded wrong solutions.
- At least one exploit/failure is documented.

## Verify

```bash
make test-exploration-reward
```

## Non-goals

- Treating reward as ground truth.

