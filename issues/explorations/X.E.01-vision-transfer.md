---
id: "X.E.01"
phase: "X"
title: "Build a small vision transfer-learning study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.E.01 — Build a small vision transfer-learning study

## Outcome

Fine-tune a pinned pretrained vision encoder on a small licensed/generated dataset and compare frozen versus unfrozen baseline.

## Allowed paths

- `explorations/multimodal/vision/**`
- `tests/explorations/multimodal/vision/**`

## Deliverables

- Fine-tune a pinned pretrained vision encoder on a small licensed/generated dataset and compare frozen versus unfrozen baseline.
- Track augmentation, slices, calibration, latency, and licenses.

## Acceptance

- Train/eval split has no duplicate images.
- Pretrained weight revision/license is recorded.

## Verify

```bash
make test-exploration-vision
```

## Non-goals

- Large image generation.

