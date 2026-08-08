---
id: "X.H.01"
phase: "X"
title: "Create annotation guidelines and task schema"
status: "optional"
depends_on: ["03.01"]
route: "required"
---

# X.H.01 — Create annotation guidelines and task schema

## Outcome

Define one bounded labeling task, examples/counterexamples, uncertainty/skip, PII, adjudication, and versioned label schema.

## Allowed paths

- `explorations/human_feedback/annotation/**`
- `tests/explorations/human_feedback/annotation/**`

## Deliverables

- Define one bounded labeling task, examples/counterexamples, uncertainty/skip, PII, adjudication, and versioned label schema.
- Create synthetic items only.

## Acceptance

- Independent reviewer can apply rules to fixture.
- Schema retains annotator/task/guideline versions.

## Verify

```bash
make test-exploration-annotation
```

## Non-goals

- Deploying labeling software.

