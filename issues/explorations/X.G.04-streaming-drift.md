---
id: "X.G.04"
phase: "X"
title: "Connect online learning and drift to the stream"
status: "optional"
depends_on: ["X.G.02", "X.A.05"]
route: "required"
---

# X.G.04 — Connect online learning and drift to the stream

## Outcome

Consume/replay events into River model/detector and compare update/reset policies with delayed labels.

## Allowed paths

- `explorations/realtime/drift/**`
- `tests/explorations/realtime/drift/**`

## Deliverables

- Consume/replay events into River model/detector and compare update/reset policies with delayed labels.
- Checkpoint state and metrics.

## Acceptance

- Replay after restart matches tolerance.
- Drift alert links event/model versions.

## Verify

```bash
make test-exploration-streaming-drift
```

## Non-goals

- Automatic production retraining.

