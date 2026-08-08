---
id: "X.C.04.a"
phase: "X"
title: "Run preference optimization with TRL DPO"
status: "optional"
depends_on: ["X.C.02", "X.C.03"]
route: "choose-one:X.C.04"
---

# X.C.04.a — Run preference optimization with TRL DPO

## Outcome

Pin TRL and run a tiny DPO experiment from the common SFT checkpoint with explicit beta/reference behavior.

## Allowed paths

- `explorations/alignment/preference/trl_dpo/**`
- `tests/explorations/alignment/preference/**`

## Deliverables

- Pin TRL and run a tiny DPO experiment from the common SFT checkpoint with explicit beta/reference behavior.
- Log losses, margins, KL proxy, resources, and checkpoint.

## Acceptance

- Tiny fixture proves preference direction.
- Held-out task/safety evaluation runs.

## Verify

```bash
make test-exploration-preference
```

## Non-goals

- Other preference algorithms.

