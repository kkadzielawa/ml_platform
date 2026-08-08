---
id: "X.G.03"
phase: "X"
title: "Add offline/online features with Feast"
status: "optional"
depends_on: ["X.G.02", "01.08"]
route: "required"
---

# X.G.03 — Add offline/online features with Feast

## Outcome

Pin Feast, define entities/features, build point-in-time correct training data, materialize/push online values, and retrieve them.

## Allowed paths

- `explorations/realtime/feast/**`
- `tests/explorations/realtime/feast/**`

## Deliverables

- Pin Feast, define entities/features, build point-in-time correct training data, materialize/push online values, and retrieve them.
- Use a generated real-time prediction fixture.

## Acceptance

- Offline join prevents future leakage.
- Online value and freshness match expected event.

## Verify

```bash
make test-exploration-feast
```

## Non-goals

- Organization-wide feature platform.

