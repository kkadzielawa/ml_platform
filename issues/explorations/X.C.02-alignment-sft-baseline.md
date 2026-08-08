---
id: "X.C.02"
phase: "X"
title: "Train the controlled SFT baseline"
status: "optional"
depends_on: ["X.C.01", "08.10"]
route: "required"
---

# X.C.02 — Train the controlled SFT baseline

## Outcome

Train a resource-bounded SFT adapter and freeze it as the common starting checkpoint.

## Allowed paths

- `explorations/alignment/sft/**`
- `tests/explorations/alignment/sft/**`

## Deliverables

- Train a resource-bounded SFT adapter and freeze it as the common starting checkpoint.
- Evaluate task/general/safety held-out sets.

## Acceptance

- Starting checkpoint and run are immutable.
- All later methods use the same base/SFT reference.

## Verify

```bash
make test-exploration-alignment-sft
```

## Non-goals

- Preference optimization.

