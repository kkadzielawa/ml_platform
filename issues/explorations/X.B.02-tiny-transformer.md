---
id: "X.B.02"
phase: "X"
title: "Implement a tiny decoder transformer"
status: "optional"
depends_on: ["X.B.01"]
route: "required"
---

# X.B.02 — Implement a tiny decoder transformer

## Outcome

Implement embeddings, positional method, causal attention, MLP, normalization, residuals, and LM head transparently in PyTorch.

## Allowed paths

- `explorations/pretraining/model/**`
- `tests/explorations/pretraining/model/**`

## Deliverables

- Implement embeddings, positional method, causal attention, MLP, normalization, residuals, and LM head transparently in PyTorch.
- Add shape, masking, gradient, parameter-count, and tiny-overfit tests.

## Acceptance

- Future-token masking test passes.
- Tiny batch overfits reproducibly.

## Verify

```bash
make test-exploration-tiny-transformer
```

## Non-goals

- Optimization or distributed parallelism.

