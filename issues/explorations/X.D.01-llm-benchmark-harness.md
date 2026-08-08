---
id: "X.D.01"
phase: "X"
title: "Generalize the LLM inference benchmark harness"
status: "optional"
depends_on: ["08.15"]
route: "required"
---

# X.D.01 — Generalize the LLM inference benchmark harness

## Outcome

Support fixed prompt/output length distributions, concurrency, streaming, structured output, cold/warm runs, correctness, and environment capture.

## Allowed paths

- `explorations/inference/benchmark/**`
- `tests/explorations/inference/benchmark/**`

## Deliverables

- Support fixed prompt/output length distributions, concurrency, streaming, structured output, cold/warm runs, correctness, and environment capture.
- Provide a tiny CPU fixture.

## Acceptance

- Same seed creates same request set.
- Incorrect output fails regardless of speed.

## Verify

```bash
make test-exploration-inference-benchmark
```

## Non-goals

- Running multiple runtimes.

