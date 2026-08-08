---
id: "X.E.04"
phase: "X"
title: "Build a multimodal retrieval study"
status: "optional"
depends_on: ["X.E.03", "09.16"]
route: "required"
---

# X.E.04 — Build a multimodal retrieval study

## Outcome

Index text/table/image representations with a pinned licensed multimodal model and answer a small golden set with citations.

## Allowed paths

- `explorations/multimodal/rag/**`
- `tests/explorations/multimodal/rag/**`

## Deliverables

- Index text/table/image representations with a pinned licensed multimodal model and answer a small golden set with citations.
- Compare text-only baseline.

## Acceptance

- Questions requiring table/image show measured comparison.
- Citations resolve to modality and source region.

## Verify

```bash
make test-exploration-multimodal-rag
```

## Non-goals

- Video retrieval.

