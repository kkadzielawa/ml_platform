---
id: "X.D.02.a"
phase: "X"
title: "Benchmark vLLM"
status: "optional"
depends_on: ["X.D.01", "08.03"]
route: "choose-one:X.D.02"
---

# X.D.02.a — Benchmark vLLM

## Outcome

Pin/configure vLLM and run the common benchmark on authorized hardware.

## Allowed paths

- `explorations/inference/runtimes/vllm/**`
- `docs/experiments/inference-runtime.md`

## Deliverables

- Pin/configure vLLM and run the common benchmark on authorized hardware.
- Capture scheduler/cache/precision parameters.

## Acceptance

- Raw result manifest is complete.
- Runtime passes correctness fixtures.

## Verify

```bash
make benchmark-exploration-runtime
```

## Non-goals

- Comparing another runtime in the same issue.

