---
id: "X.G.06"
phase: "X"
title: "Simulate federated learning with Flower"
status: "optional"
depends_on: ["X.A.01"]
route: "required"
---

# X.G.06 — Simulate federated learning with Flower

## Outcome

Pin Flower, partition generated data into non-IID clients, compare centralized/FedAvg/one strategy, and measure rounds/communication/accuracy.

## Allowed paths

- `explorations/privacy/federated/**`
- `tests/explorations/privacy/federated/**`

## Deliverables

- Pin Flower, partition generated data into non-IID clients, compare centralized/FedAvg/one strategy, and measure rounds/communication/accuracy.
- Inject one client dropout.

## Acceptance

- Partitions and seeds are reproducible.
- Report does not claim data never leaks without attack analysis.

## Verify

```bash
make test-exploration-federated
```

## Non-goals

- Real devices or secure aggregation deployment.

