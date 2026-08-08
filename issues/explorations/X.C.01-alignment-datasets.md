---
id: "X.C.01"
phase: "X"
title: "Create instruction, preference, and verifier datasets"
status: "optional"
depends_on: ["08.08"]
route: "required"
---

# X.C.01 — Create instruction, preference, and verifier datasets

## Outcome

Create tiny versioned licensed/generated SFT, paired-preference, and verifiable-task fixtures with provenance and held-out splits.

## Allowed paths

- `explorations/alignment/data/**`
- `tests/explorations/alignment/data/**`

## Deliverables

- Create tiny versioned licensed/generated SFT, paired-preference, and verifiable-task fixtures with provenance and held-out splits.
- Add agreement/quality/contamination checks.

## Acceptance

- Chosen/rejected ordering and verifier outcomes are validated.
- No held-out prompt duplicate is in training.

## Verify

```bash
make test-exploration-alignment-data
```

## Non-goals

- Large human-labeling effort.

