---
id: "X.G.02.c"
phase: "X"
title: "Process the event study with Apache Flink"
status: "optional"
depends_on: ["X.G.01", "01.03"]
route: "choose-one:X.G.02"
---

# X.G.02.c — Process the event study with Apache Flink

## Outcome

Deploy pinned Flink study topology with a bounded source/sink and event-time window over the fixture.

## Allowed paths

- `explorations/realtime/brokers/flink/**`
- `tests/explorations/realtime/broker/**`

## Deliverables

- Deploy pinned Flink study topology with a bounded source/sink and event-time window over the fixture.
- Record checkpoint/watermark/late-event behavior and resources.

## Acceptance

- Restart produces documented exactly/at-least-once outcome.
- Late-event fixture follows configured policy.

## Verify

```bash
make test-exploration-stream-broker
```

## Non-goals

- Operating a production Flink cluster.

