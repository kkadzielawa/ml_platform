---
id: "X.G.01"
phase: "X"
title: "Implement a local replayable feature stream"
status: "optional"
depends_on: ["03.13"]
route: "required"
---

# X.G.01 — Implement a local replayable feature stream

## Outcome

Define event schema/key/event-time/ingest-time/watermark/idempotency and replay deterministic local fixture.

## Allowed paths

- `explorations/realtime/events/**`
- `tests/explorations/realtime/events/**`

## Deliverables

- Define event schema/key/event-time/ingest-time/watermark/idempotency and replay deterministic local fixture.
- Include late, duplicate, and out-of-order events.

## Acceptance

- Replay produces identical final state.
- Event schema evolution compatibility is tested.

## Verify

```bash
make test-exploration-event-replay
```

## Non-goals

- Deploying a broker.

