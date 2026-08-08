---
id: "X.C.06.b"
phase: "X"
title: "Run tiny RL post-training with OpenRLHF"
status: "optional"
depends_on: ["X.C.02", "X.C.05", "07.03"]
route: "choose-one:X.C.06"
---

# X.C.06.b — Run tiny RL post-training with OpenRLHF

## Outcome

Pin OpenRLHF and run a strictly bounded toy verifiable RL post-training job.

## Allowed paths

- `explorations/alignment/rl/openrlhf/**`
- `tests/explorations/alignment/rl/**`

## Deliverables

- Pin OpenRLHF and run a strictly bounded toy verifiable RL post-training job.
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

