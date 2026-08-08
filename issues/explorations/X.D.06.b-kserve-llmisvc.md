---
id: "X.D.06.b"
phase: "X"
title: "Study KServe LLMInferenceService"
status: "optional"
depends_on: ["X.D.01", "07.03", "05.02.a"]
route: "choose-one:X.D.06"
---

# X.D.06.b — Study KServe LLMInferenceService

## Outcome

Pin/deploy the smallest supported KServe LLMInferenceService path and compare with single-server baseline.

## Allowed paths

- `explorations/inference/distributed/kserve_llmisvc/**`
- `tests/explorations/inference/distributed/**`

## Deliverables

- Pin/deploy the smallest supported KServe LLMInferenceService path and compare with single-server baseline.
- Study one routing/caching/multi-node capability supported by the hardware.

## Acceptance

- Correctness matches baseline.
- Operational overhead and resource floor are reported.

## Verify

```bash
make test-exploration-distributed-inference
```

## Non-goals

- Production scale claims.

