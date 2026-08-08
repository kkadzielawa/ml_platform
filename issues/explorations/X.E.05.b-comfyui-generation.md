---
id: "X.E.05.b"
phase: "X"
title: "Generate images with a versioned ComfyUI workflow"
status: "optional"
depends_on: ["08.01"]
route: "choose-one:X.E.05"
---

# X.E.05.b — Generate images with a versioned ComfyUI workflow

## Outcome

Pin ComfyUI/custom-node revisions and one small allowed image model; store a minimal workflow JSON.

## Allowed paths

- `explorations/multimodal/generation/comfyui/**`
- `tests/explorations/multimodal/generation/**`

## Deliverables

- Pin ComfyUI/custom-node revisions and one small allowed image model; store a minimal workflow JSON.
- Generate deterministic-seed samples with provenance and resource metrics.

## Acceptance

- Workflow uses no unpinned remote custom node.
- Output metadata is reproducible.

## Verify

```bash
make test-exploration-generation
```

## Non-goals

- Building a user-facing ComfyUI service.

