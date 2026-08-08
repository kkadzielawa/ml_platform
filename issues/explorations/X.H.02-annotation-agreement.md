---
id: "X.H.02"
phase: "X"
title: "Measure agreement and adjudicate disagreements"
status: "optional"
depends_on: ["X.H.01"]
route: "required"
---

# X.H.02 — Measure agreement and adjudicate disagreements

## Outcome

Collect or simulate at least two label sets, compute appropriate agreement, surface ambiguous items, and record adjudication separately.

## Allowed paths

- `explorations/human_feedback/agreement/**`
- `tests/explorations/human_feedback/agreement/**`
- `docs/experiments/annotation-agreement.md`

## Deliverables

- Collect or simulate at least two label sets, compute appropriate agreement, surface ambiguous items, and record adjudication separately.
- Do not overwrite original labels.

## Acceptance

- Seeded perfect/disagree cases produce expected metrics.
- Report explains prevalence/metric limitations.

## Verify

```bash
make test-exploration-annotation-agreement
```

## Non-goals

- Hiring annotators.

