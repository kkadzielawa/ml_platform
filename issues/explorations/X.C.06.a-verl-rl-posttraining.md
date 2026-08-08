---
id: "X.C.06.a"
phase: "X"
title: "Run tiny RL post-training with verl"
status: "optional"
depends_on: ["X.C.02", "X.C.05", "07.03"]
route: "choose-one:X.C.06"
---

# X.C.06.a — Run tiny RL post-training with verl

## Outcome

Pin verl and run a strictly bounded toy verifiable RL post-training job.

## Allowed paths

- `explorations/alignment/rl/verl/**`
- `tests/explorations/alignment/rl/**`

## Deliverables

- Pin verl and run a strictly bounded toy verifiable RL post-training job.
- Capture rollout/reward/KL/length/diversity/resources and sample trajectories.

## Acceptance

- Budget hard-stop works.
- Seeded reward exploit is visible in analysis.

## Verify

```bash
make test-exploration-rl-posttraining
```

## Non-goals

- Large-scale RLHF.

