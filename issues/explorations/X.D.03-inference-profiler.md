---
id: "X.D.03"
phase: "X"
title: "Profile model execution and memory"
status: "optional"
depends_on: ["X.D.02"]
route: "required"
---

# X.D.03 — Profile model execution and memory

## Outcome

Profile warmup, prefill, decode, kernel/operator time, memory weights/activations/KV/cache, and host-device transfer with supported tools.

## Allowed paths

- `explorations/inference/profiling/**`
- `tests/explorations/inference/profiling/**`
- `docs/experiments/inference-profile.md`

## Deliverables

- Profile warmup, prefill, decode, kernel/operator time, memory weights/activations/KV/cache, and host-device transfer with supported tools.
- Relate profile to one benchmark workload.

## Acceptance

- Profiler overhead and sampling limits are stated.
- At least one measured bottleneck is identified.

## Verify

```bash
make test-exploration-inference-profile
```

## Non-goals

- Writing custom kernels.

