---
id: "X.G.05.a"
phase: "X"
title: "Deploy a model with ONNX Runtime"
status: "optional"
depends_on: ["00.15"]
route: "choose-one:X.G.05"
---

# X.G.05.a — Deploy a model with ONNX Runtime

## Outcome

Export baseline model to ONNX, validate numerics, and run on a constrained CPU/container/mobile-like target.

## Allowed paths

- `explorations/edge/onnx/**`
- `tests/explorations/edge/**`

## Deliverables

- Export baseline model to ONNX, validate numerics, and run on a constrained CPU/container/mobile-like target.
- Measure size, startup, latency, memory.

## Acceptance

- Predictions match source tolerance.
- Unsupported operator fails at export validation.

## Verify

```bash
make test-exploration-edge
```

## Non-goals

- Browser UI.

