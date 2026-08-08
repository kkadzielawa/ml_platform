---
id: "X.D.07"
phase: "X"
title: "Publish the inference tradeoff matrix"
status: "optional"
depends_on: ["X.D.03", "X.D.04", "X.D.05", "X.D.06"]
route: "required"
---

# X.D.07 — Publish the inference tradeoff matrix

## Outcome

Compare quality, TTFT, inter-token latency, throughput, memory, energy/cost proxy, complexity, and failure behavior from raw results.

## Allowed paths

- `docs/experiments/inference-tradeoffs.md`
- `explorations/inference/results/**`
- `tests/explorations/inference/report/**`

## Deliverables

- Compare quality, TTFT, inter-token latency, throughput, memory, energy/cost proxy, complexity, and failure behavior from raw results.
- Recommend by workload, not one global winner.

## Acceptance

- Report is reproducible from saved data.
- Unsupported/untested cells are marked, not inferred.

## Verify

```bash
make test-exploration-inference-report
```

## Non-goals

- Choosing a production runtime.

