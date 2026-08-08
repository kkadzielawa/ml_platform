---
id: "X.C.03"
phase: "X"
title: "Audit preference signal and judge bias"
status: "optional"
depends_on: ["X.C.01"]
route: "required"
---

# X.C.03 — Audit preference signal and judge bias

## Outcome

Measure class/order/length/style correlations, annotator agreement, and one judge-order swap test.

## Allowed paths

- `explorations/alignment/audit/**`
- `tests/explorations/alignment/audit/**`
- `docs/experiments/preference-audit.md`

## Deliverables

- Measure class/order/length/style correlations, annotator agreement, and one judge-order swap test.
- Flag leakage and shortcuts.

## Acceptance

- Seeded position/length bias is detected.
- Report distinguishes human and model-generated preferences.

## Verify

```bash
make test-exploration-preference-audit
```

## Non-goals

- Training a reward model.

