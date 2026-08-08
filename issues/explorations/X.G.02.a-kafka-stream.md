---
id: "X.G.02.a"
phase: "X"
title: "Run the event study on Apache Kafka"
status: "optional"
depends_on: ["X.G.01", "01.03"]
route: "choose-one:X.G.02"
---

# X.G.02.a — Run the event study on Apache Kafka

## Outcome

Deploy pinned Kafka in study topology and publish/consume/replay the common event fixture with bounded retention.

## Allowed paths

- `explorations/realtime/brokers/kafka/**`
- `tests/explorations/realtime/broker/**`

## Deliverables

- Deploy pinned Kafka in study topology and publish/consume/replay the common event fixture with bounded retention.
- Record partitions, ordering, delivery, and resource cost.

## Acceptance

- Duplicate/restart behavior matches documented semantics.
- No production durability claim.

## Verify

```bash
make test-exploration-stream-broker
```

## Non-goals

- Flink processing.

