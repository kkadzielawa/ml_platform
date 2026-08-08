---
id: "X.F.04.b"
phase: "X"
title: "Build an in-process GraphRAG study with NetworkX"
status: "optional"
depends_on: ["X.F.01"]
route: "choose-one:X.F.04"
---

# X.F.04.b — Build an in-process GraphRAG study with NetworkX

## Outcome

Define a small ontology, load versioned entities/relations/evidence into NetworkX, and implement bounded graph queries.

## Allowed paths

- `explorations/retrieval/graph/networkx/**`
- `tests/explorations/retrieval/graph/**`

## Deliverables

- Define a small ontology, load versioned entities/relations/evidence into NetworkX, and implement bounded graph queries.
- Serialize graph and provenance deterministically.

## Acceptance

- Graph rebuild can be diffed.
- ACL filtering occurs before evidence return.

## Verify

```bash
make test-exploration-graph-store
```

## Non-goals

- Concurrent database serving.

