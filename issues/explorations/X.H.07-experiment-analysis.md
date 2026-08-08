---
id: "X.H.07"
phase: "X"
title: "Analyze an A/B experiment with guardrails"
status: "optional"
depends_on: ["X.H.06"]
route: "required"
---

# X.H.07 — Analyze an A/B experiment with guardrails

## Outcome

Analyze generated outcomes with sample-ratio mismatch, primary/guardrail metrics, confidence intervals, missingness, and optional sequential-look warning.

## Allowed paths

- `explorations/product_experiments/analysis/**`
- `tests/explorations/product_experiments/analysis/**`
- `docs/experiments/ab-report.md`

## Deliverables

- Analyze generated outcomes with sample-ratio mismatch, primary/guardrail metrics, confidence intervals, missingness, and optional sequential-look warning.
- Report practical and statistical significance.

## Acceptance

- Seeded SRM and guardrail regression are detected.
- No winner is declared on biased fixture.

## Verify

```bash
make test-exploration-experiment-analysis
```

## Non-goals

- Making product decisions from synthetic outcomes.

