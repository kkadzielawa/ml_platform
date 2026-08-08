---
id: "X.G.05.c"
phase: "X"
title: "Compile a model with Apache TVM"
status: "optional"
depends_on: ["00.15"]
route: "choose-one:X.G.05"
---

# X.G.05.c — Compile a model with Apache TVM

## Outcome

Pin TVM, import/compile one baseline model for a recorded target, and compare with source runtime.

## Allowed paths

- `explorations/edge/tvm/**`
- `tests/explorations/edge/**`

## Deliverables

- Pin TVM, import/compile one baseline model for a recorded target, and compare with source runtime.
- Capture IR/pass config and generated artifact.

## Acceptance

- Numerics match tolerance.
- Performance result includes compilation cost and target details.

## Verify

```bash
make test-exploration-edge
```

## Non-goals

- Custom code generation.

