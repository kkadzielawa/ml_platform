---
id: "X.G.05.b"
phase: "X"
title: "Deploy a small LLM with llama.cpp"
status: "optional"
depends_on: ["08.03"]
route: "choose-one:X.G.05"
---

# X.G.05.b — Deploy a small LLM with llama.cpp

## Outcome

Convert/use a verified GGUF model and run llama.cpp under explicit CPU/RAM/thread/context budget.

## Allowed paths

- `explorations/edge/llamacpp/**`
- `tests/explorations/edge/**`

## Deliverables

- Convert/use a verified GGUF model and run llama.cpp under explicit CPU/RAM/thread/context budget.
- Measure size, startup, TTFT, tokens/s, memory, and quality fixture.

## Acceptance

- Model hash/license is retained.
- Process stays within budget.

## Verify

```bash
make test-exploration-edge
```

## Non-goals

- Production edge fleet.

