---
id: "X.E.02"
phase: "X"
title: "Build a small audio study"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.E.02 — Build a small audio study

## Outcome

Implement a small audio classification or transcription experiment with deterministic resampling/features and a licensed/generated fixture.

## Allowed paths

- `explorations/multimodal/audio/**`
- `tests/explorations/multimodal/audio/**`

## Deliverables

- Implement a small audio classification or transcription experiment with deterministic resampling/features and a licensed/generated fixture.
- Measure task metric, real-time factor, memory, and noisy slice.

## Acceptance

- Sample-rate/channel handling is tested.
- No unlicensed user audio is committed.

## Verify

```bash
make test-exploration-audio
```

## Non-goals

- Production speech service.

