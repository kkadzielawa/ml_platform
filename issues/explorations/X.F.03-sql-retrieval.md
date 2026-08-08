---
id: "X.F.03"
phase: "X"
title: "Add typed SQL/structured retrieval"
status: "optional"
depends_on: ["X.F.01"]
route: "required"
---

# X.F.03 — Add typed SQL/structured retrieval

## Outcome

Create a small relational fixture and a safe typed query/tool route or constrained text-to-SQL study.

## Allowed paths

- `explorations/retrieval/sql/**`
- `tests/explorations/retrieval/sql/**`

## Deliverables

- Create a small relational fixture and a safe typed query/tool route or constrained text-to-SQL study.
- Use read-only role, schema allowlist, statement timeout, and row limit.

## Acceptance

- Mutation/multi-statement/unauthorized-table attempts fail.
- Relationship-heavy questions are compared with text RAG.

## Verify

```bash
make test-exploration-sql-retrieval
```

## Non-goals

- Arbitrary production database access.

