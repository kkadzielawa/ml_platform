---
id: "X.E.05.a"
phase: "X"
title: "Generate images with Diffusers"
status: "optional"
depends_on: ["08.01"]
route: "choose-one:X.E.05"
---

# X.E.05.a — Generate images with Diffusers

## Outcome

Pin a small allowed image model and Diffusers pipeline; generate deterministic-seed samples with full provenance.

## Allowed paths

- `explorations/multimodal/generation/diffusers/**`
- `tests/explorations/multimodal/generation/**`

## Deliverables

- Pin a small allowed image model and Diffusers pipeline; generate deterministic-seed samples with full provenance.
- Record prompt, negative prompt, scheduler, steps, seed, model hash, time, and memory.

## Acceptance

- Blocked/disallowed prompt fixture follows study policy.
- Output metadata is reproducible.

## Verify

```bash
make test-exploration-generation
```

## Non-goals

- Training a diffusion model.

