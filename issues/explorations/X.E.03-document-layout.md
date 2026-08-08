---
id: "X.E.03"
phase: "X"
title: "Extract text, tables, and images from one document"
status: "optional"
depends_on: ["09.03"]
route: "required"
---

# X.E.03 — Extract text, tables, and images from one document

## Outcome

Parse a redistributable document containing prose, table, and image; preserve layout/page/bounding-box provenance.

## Allowed paths

- `explorations/multimodal/document_layout/**`
- `tests/explorations/multimodal/document_layout/**`

## Deliverables

- Parse a redistributable document containing prose, table, and image; preserve layout/page/bounding-box provenance.
- Create golden structured output.

## Acceptance

- Every element resolves to page/location.
- Repeated extraction differences are detected.

## Verify

```bash
make test-exploration-document-layout
```

## Non-goals

- Arbitrary document coverage.

