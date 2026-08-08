---
id: "X.F.05"
phase: "X"
title: "Implement and evaluate entity extraction/resolution"
status: "optional"
depends_on: ["X.F.04", "09.06"]
route: "required"
---

# X.F.05 — Implement and evaluate entity extraction/resolution

## Outcome

Extract fixture entities/relations with deterministic and model-assisted methods, normalize identities, and retain confidence/evidence.

## Allowed paths

- `explorations/retrieval/entity_resolution/**`
- `tests/explorations/retrieval/entity_resolution/**`

## Deliverables

- Extract fixture entities/relations with deterministic and model-assisted methods, normalize identities, and retain confidence/evidence.
- Create a small labeled eval set.

## Acceptance

- Precision/recall and merge/split errors are reported.
- Low-confidence/model output cannot silently overwrite strong identities.

## Verify

```bash
make test-exploration-entity-resolution
```

## Non-goals

- Universal ontology learning.

