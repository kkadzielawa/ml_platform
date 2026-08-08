---
id: "X.G.02.b"
phase: "X"
title: "Run the event study on NATS JetStream"
status: "optional"
depends_on: ["X.G.01", "01.03"]
route: "choose-one:X.G.02"
---

# X.G.02.b — Run the event study on NATS JetStream

## Outcome

Deploy pinned NATS JetStream and publish/consume/replay the common event fixture with bounded retention.

## Allowed paths

- `explorations/realtime/brokers/nats/**`
- `tests/explorations/realtime/broker/**`

## Deliverables

- Deploy pinned NATS JetStream and publish/consume/replay the common event fixture with bounded retention.
- Record stream/consumer/delivery and resource cost.

## Acceptance

- Duplicate/restart behavior matches documented semantics.
- No production durability claim.

## Verify

```bash
make test-exploration-stream-broker
```

## Non-goals

- Kafka comparison in the same issue.

