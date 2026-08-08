---
id: "X.B.07.b"
phase: "X"
title: "Study parallelism with DeepSpeed"
status: "optional"
depends_on: ["X.B.05", "07.03"]
route: "choose-one:X.B.07"
---

# X.B.07.b — Study parallelism with DeepSpeed

## Outcome

Pin DeepSpeed and run the tiny model with one supported ZeRO/parallel configuration.

## Allowed paths

- `explorations/pretraining/parallelism/deepspeed/**`
- `tests/explorations/pretraining/parallelism/**`

## Deliverables

- Pin DeepSpeed and run the tiny model with one supported ZeRO/parallel configuration.
- Measure communication, memory, and correctness against single-device baseline.

## Acceptance

- Distributed output matches tolerance.
- Config and world topology are captured.

## Verify

```bash
make test-exploration-pretraining-parallel
```

## Non-goals

- Large-scale pretraining.

