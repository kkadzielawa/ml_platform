---
id: "X.D.02.c"
phase: "X"
title: "Benchmark llama.cpp"
status: "optional"
depends_on: ["X.D.01", "08.03"]
route: "choose-one:X.D.02"
---

# X.D.02.c — Benchmark llama.cpp

## Outcome

Pin/build llama.cpp and run a compatible GGUF model through the common benchmark on CPU/GPU.

## Allowed paths

- `explorations/inference/runtimes/llamacpp/**`
- `docs/experiments/inference-runtime.md`

## Deliverables

- Pin/build llama.cpp and run a compatible GGUF model through the common benchmark on CPU/GPU.
- Capture offload, threads, context, and quantization.

## Acceptance

- Raw result manifest is complete.
- Runtime passes correctness fixtures.

## Verify

```bash
make benchmark-exploration-runtime
```

## Non-goals

- Comparing another runtime in the same issue.

