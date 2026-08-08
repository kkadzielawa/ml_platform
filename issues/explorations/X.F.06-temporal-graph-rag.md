---
id: "X.F.06"
phase: "X"
title: "Add temporal/conflicting-fact retrieval"
status: "optional"
depends_on: ["X.F.05"]
route: "required"
---

# X.F.06 — Add temporal/conflicting-fact retrieval

## Outcome

Model valid/observed time and conflicting source claims; answer as-of and conflict-aware fixtures with provenance.

## Allowed paths

- `explorations/retrieval/temporal/**`
- `tests/explorations/retrieval/temporal/**`

## Deliverables

- Model valid/observed time and conflicting source claims; answer as-of and conflict-aware fixtures with provenance.
- Compare with vector baseline.

## Acceptance

- As-of query excludes future facts.
- Conflicts are surfaced rather than silently merged.

## Verify

```bash
make test-exploration-temporal-retrieval
```

## Non-goals

- Truth adjudication.

