---
id: "X.B.04"
phase: "X"
title: "Train the tiny transformer on one device"
status: "optional"
depends_on: ["X.B.02", "X.B.03"]
route: "required"
---

# X.B.04 — Train the tiny transformer on one device

## Outcome

Implement optimizer/schedule, mixed precision where supported, gradient accumulation/clipping, evaluation, logging, and resource cap.

## Allowed paths

- `explorations/pretraining/train/**`
- `tests/explorations/pretraining/train/**`

## Deliverables

- Implement optimizer/schedule, mixed precision where supported, gradient accumulation/clipping, evaluation, logging, and resource cap.
- Track tokens, loss, throughput, memory, and compute estimate.

## Acceptance

- Loss beats unigram/random baseline.
- Run stops at configured token/time budget.

## Verify

```bash
make test-exploration-pretraining && make run-tiny-pretraining
```

## Non-goals

- Training a useful general-purpose LLM.

