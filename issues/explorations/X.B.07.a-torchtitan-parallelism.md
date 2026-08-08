---
id: "X.B.07.a"
phase: "X"
title: "Study parallelism with TorchTitan"
status: "optional"
depends_on: ["X.B.05", "07.03"]
route: "choose-one:X.B.07"
---

# X.B.07.a — Study parallelism with TorchTitan

## Outcome

Pin TorchTitan and port a tiny supported model/job to study data/tensor/pipeline/context parallel concepts available on hardware.

## Allowed paths

- `explorations/pretraining/parallelism/torchtitan/**`
- `tests/explorations/pretraining/parallelism/**`

## Deliverables

- Pin TorchTitan and port a tiny supported model/job to study data/tensor/pipeline/context parallel concepts available on hardware.
- Measure communication, memory, and correctness against single-device baseline.

## Acceptance

- Distributed output matches tolerance.
- Unsupported parallel dimensions are documented/skipped.

## Verify

```bash
make test-exploration-pretraining-parallel
```

## Non-goals

- Large-scale pretraining.

