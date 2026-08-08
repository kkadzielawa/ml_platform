---
id: "X.D.02.b"
phase: "X"
title: "Benchmark SGLang"
status: "optional"
depends_on: ["X.D.01", "08.03"]
route: "choose-one:X.D.02"
---

# X.D.02.b — Benchmark SGLang

## Outcome

Pin/configure SGLang and run the common benchmark on authorized hardware.

## Allowed paths

- `explorations/inference/runtimes/sglang/**`
- `docs/experiments/inference-runtime.md`

## Deliverables

- Pin/configure SGLang and run the common benchmark on authorized hardware.
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

