---
id: "X.D.05"
phase: "X"
title: "Study prefix caching and routing"
status: "optional"
depends_on: ["X.D.01"]
route: "required"
---

# X.D.05 — Study prefix caching and routing

## Outcome

Create workloads with controlled shared prefixes and compare cache off/on plus naive/prefix-aware routing simulation.

## Allowed paths

- `explorations/inference/prefix_cache/**`
- `tests/explorations/inference/prefix_cache/**`

## Deliverables

- Create workloads with controlled shared prefixes and compare cache off/on plus naive/prefix-aware routing simulation.
- Measure hit rate, latency, throughput, memory, and tenant isolation keys.

## Acceptance

- Cross-tenant prefix entries never share unless policy explicitly permits.
- Random-prefix control shows expected low hit rate.

## Verify

```bash
make test-exploration-prefix-cache
```

## Non-goals

- Distributed serving.

