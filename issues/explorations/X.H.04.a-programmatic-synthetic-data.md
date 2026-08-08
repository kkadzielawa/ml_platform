---
id: "X.H.04.a"
phase: "X"
title: "Generate synthetic data programmatically"
status: "optional"
depends_on: ["X.H.01"]
route: "choose-one:X.H.04"
---

# X.H.04.a — Generate synthetic data programmatically

## Outcome

Use pinned Faker/Mimesis or explicit simulator to generate schema-valid examples with controlled edge cases and provenance.

## Allowed paths

- `explorations/synthetic/programmatic/**`
- `tests/explorations/synthetic/**`

## Deliverables

- Use pinned Faker/Mimesis or explicit simulator to generate schema-valid examples with controlled edge cases and provenance.
- Measure coverage and downstream utility against small real/generated reference.

## Acceptance

- Same seed is reproducible.
- No input record is copied.

## Verify

```bash
make test-exploration-synthetic
```

## Non-goals

- LLM generation.

