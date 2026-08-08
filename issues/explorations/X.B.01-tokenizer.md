---
id: "X.B.01"
phase: "X"
title: "Implement and evaluate a tiny tokenizer"
status: "optional"
depends_on: ["03.13"]
route: "required"
---

# X.B.01 — Implement and evaluate a tiny tokenizer

## Outcome

Train a tiny BPE/Unigram tokenizer on a versioned licensed corpus and compare against character/word baselines.

## Allowed paths

- `explorations/pretraining/tokenizer/**`
- `tests/explorations/pretraining/tokenizer/**`

## Deliverables

- Train a tiny BPE/Unigram tokenizer on a versioned licensed corpus and compare against character/word baselines.
- Record vocabulary, special tokens, fertility, unknown/byte behavior, and artifact hash.

## Acceptance

- Encode/decode invariants pass for fixtures.
- Eval text is excluded from tokenizer training where required.

## Verify

```bash
make test-exploration-tokenizer
```

## Non-goals

- Using a foundation-model tokenizer.

