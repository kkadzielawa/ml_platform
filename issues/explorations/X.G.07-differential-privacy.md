---
id: "X.G.07"
phase: "X"
title: "Add differential privacy to the federated study"
status: "optional"
depends_on: ["X.G.06"]
route: "required"
---

# X.G.07 — Add differential privacy to the federated study

## Outcome

Pin Opacus where compatible; compare non-private/private training across noise/clipping with epsilon/delta accounting.

## Allowed paths

- `explorations/privacy/differential/**`
- `tests/explorations/privacy/differential/**`
- `docs/experiments/privacy-report.md`

## Deliverables

- Pin Opacus where compatible; compare non-private/private training across noise/clipping with epsilon/delta accounting.
- Run a simple memorization/membership-risk proxy and utility comparison.

## Acceptance

- Privacy budget computation and assumptions are explicit.
- Report states DP scope and federated limitations.

## Verify

```bash
make test-exploration-differential-privacy
```

## Non-goals

- Claiming end-to-end privacy.

