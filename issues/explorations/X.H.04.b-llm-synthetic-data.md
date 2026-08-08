---
id: "X.H.04.b"
phase: "X"
title: "Generate synthetic data with a local LLM"
status: "optional"
depends_on: ["X.H.01", "08.05"]
route: "choose-one:X.H.04"
---

# X.H.04.b — Generate synthetic data with a local LLM

## Outcome

Use a versioned prompt/schema/local model to generate bounded examples, validate/deduplicate/filter them, and retain provenance.

## Allowed paths

- `explorations/synthetic/llm/**`
- `tests/explorations/synthetic/**`

## Deliverables

- Use a versioned prompt/schema/local model to generate bounded examples, validate/deduplicate/filter them, and retain provenance.
- Compare with programmatic/simple baseline.

## Acceptance

- Malformed/duplicate outputs are rejected.
- Prompt/model/version/seed or sampling parameters are recorded.

## Verify

```bash
make test-exploration-synthetic
```

## Non-goals

- Treating generated labels as automatically correct.

