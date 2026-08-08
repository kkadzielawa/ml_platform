---
id: "X.B.05"
phase: "X"
title: "Checkpoint and resume tiny pretraining"
status: "optional"
depends_on: ["X.B.04"]
route: "required"
---

# X.B.05 — Checkpoint and resume tiny pretraining

## Outcome

Save model/optimizer/scheduler/scaler/RNG/data-cursor/config state atomically and resume.

## Allowed paths

- `explorations/pretraining/checkpoints/**`
- `tests/explorations/pretraining/checkpoints/**`

## Deliverables

- Save model/optimizer/scheduler/scaler/RNG/data-cursor/config state atomically and resume.
- Compare uninterrupted and interrupted runs.

## Acceptance

- Final states/metrics match declared tolerance.
- Corrupt/incomplete checkpoint is rejected.

## Verify

```bash
make test-exploration-pretraining-resume
```

## Non-goals

- Cross-world-size resume.

