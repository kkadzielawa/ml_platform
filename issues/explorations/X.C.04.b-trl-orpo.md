---
id: "X.C.04.b"
phase: "X"
title: "Run preference optimization with TRL ORPO"
status: "optional"
depends_on: ["X.C.02", "X.C.03"]
route: "choose-one:X.C.04"
---

# X.C.04.b — Run preference optimization with TRL ORPO

## Outcome

Pin TRL and run a tiny ORPO experiment from the common base/SFT setup with documented objective differences.

## Allowed paths

- `explorations/alignment/preference/trl_orpo/**`
- `tests/explorations/alignment/preference/**`

## Deliverables

- Pin TRL and run a tiny ORPO experiment from the common base/SFT setup with documented objective differences.
- Log losses, preference margin, resources, and checkpoint.

## Acceptance

- Tiny fixture proves preference direction.
- Held-out task/safety evaluation runs.

## Verify

```bash
make test-exploration-preference
```

## Non-goals

- Other preference algorithms.

