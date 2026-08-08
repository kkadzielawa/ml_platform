---
id: "X.C.07"
phase: "X"
title: "Compare alignment methods and regressions"
status: "optional"
depends_on: ["X.C.04", "X.C.06"]
route: "required"
---

# X.C.07 — Compare alignment methods and regressions

## Outcome

Evaluate base, SFT, preference, and RL checkpoints on identical task/general/safety/reward-hack sets with human trajectory review.

## Allowed paths

- `explorations/alignment/evaluation/**`
- `docs/experiments/alignment-report.md`
- `tests/explorations/alignment/evaluation/**`

## Deliverables

- Evaluate base, SFT, preference, and RL checkpoints on identical task/general/safety/reward-hack sets with human trajectory review.
- Report gains, regressions, uncertainty, and resource cost.

## Acceptance

- No checkpoint is selected on the final test set alone.
- Raw results and immutable references are retained.

## Verify

```bash
make test-exploration-alignment-report
```

## Non-goals

- Declaring broad human alignment.

