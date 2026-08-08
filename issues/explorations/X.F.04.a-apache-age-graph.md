---
id: "X.F.04.a"
phase: "X"
title: "Build a GraphRAG store with Apache AGE"
status: "optional"
depends_on: ["X.F.01", "01.08"]
route: "choose-one:X.F.04"
---

# X.F.04.a — Build a GraphRAG store with Apache AGE

## Outcome

Pin Apache AGE, define a small ontology, load versioned entities/relations/evidence, and implement bounded graph queries.

## Allowed paths

- `explorations/retrieval/graph/apache_age/**`
- `tests/explorations/retrieval/graph/**`

## Deliverables

- Pin Apache AGE, define a small ontology, load versioned entities/relations/evidence, and implement bounded graph queries.
- Preserve source evidence and ACLs.

## Acceptance

- Graph rebuild is deterministic enough to diff.
- Query cannot traverse into denied evidence.

## Verify

```bash
make test-exploration-graph-store
```

## Non-goals

- Enterprise graph features.

