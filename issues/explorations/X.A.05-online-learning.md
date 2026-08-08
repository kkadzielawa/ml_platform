---
id: "X.A.05"
phase: "X"
title: "Build an online-learning and drift study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.A.05 — Build an online-learning and drift study

## Outcome

Use River on a deterministic evolving stream; compare static, incremental, window reset, and drift-triggered strategies.

## Allowed paths

- `explorations/specialized_ml/online/**`
- `tests/explorations/online/**`

## Deliverables

- Use River on a deterministic evolving stream; compare static, incremental, window reset, and drift-triggered strategies.
- Plot prequential performance and memory/time.

## Acceptance

- Stream replay is deterministic.
- Concept drift point and label delay are explicit.

## Verify

```bash
make test-exploration-online
```

## Non-goals

- Kafka/Flink infrastructure.

