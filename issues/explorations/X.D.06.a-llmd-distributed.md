---
id: "X.D.06.a"
phase: "X"
title: "Study distributed inference with llm-d"
status: "optional"
depends_on: ["X.D.01", "07.03"]
route: "choose-one:X.D.06"
---

# X.D.06.a — Study distributed inference with llm-d

## Outcome

Pin llm-d and deploy its smallest supported path over the selected runtime; compare with single-server baseline.

## Allowed paths

- `explorations/inference/distributed/llmd/**`
- `tests/explorations/inference/distributed/**`

## Deliverables

- Pin llm-d and deploy its smallest supported path over the selected runtime; compare with single-server baseline.
- Study routing/KV locality or one supported distributed feature.

## Acceptance

- Correctness matches baseline.
- Operational overhead and resource floor are reported.

## Verify

```bash
make test-exploration-distributed-inference
```

## Non-goals

- Production scale claims.

