---
id: "X.A.08"
phase: "X"
title: "Build a reinforcement-learning study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.A.08 — Build a reinforcement-learning study

## Outcome

Train a small Gymnasium/Stable-Baselines3 agent, checkpoint/evaluate seeds, and construct one reward-hacking variant.

## Allowed paths

- `explorations/specialized_ml/reinforcement_learning/**`
- `tests/explorations/reinforcement_learning/**`

## Deliverables

- Train a small Gymnasium/Stable-Baselines3 agent, checkpoint/evaluate seeds, and construct one reward-hacking variant.
- Compare with random/heuristic baseline.

## Acceptance

- Evaluation seeds are held out.
- Report shows reward can diverge from intended behavior.

## Verify

```bash
make test-exploration-rl
```

## Non-goals

- LLM RL post-training.

