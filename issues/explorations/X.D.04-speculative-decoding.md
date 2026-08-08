---
id: "X.D.04"
phase: "X"
title: "Evaluate speculative decoding"
status: "optional"
depends_on: ["X.D.03"]
route: "required"
---

# X.D.04 — Evaluate speculative decoding

## Outcome

Configure a compatible draft/target or self-speculative method and compare identical requests.

## Allowed paths

- `explorations/inference/speculative/**`
- `tests/explorations/inference/speculative/**`

## Deliverables

- Configure a compatible draft/target or self-speculative method and compare identical requests.
- Measure acceptance, quality equivalence, TTFT/inter-token/throughput, and memory.

## Acceptance

- Disabled baseline uses same target/settings.
- Unsupported model case exits clearly.

## Verify

```bash
make test-exploration-speculative
```

## Non-goals

- Generalizing gains to all workloads.

