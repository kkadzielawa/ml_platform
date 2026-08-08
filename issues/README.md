# Atomic Implementation Backlog

This directory decomposes `IMPLEMENTATION_PLAN.md` into issues intended to fit a lesser coding model's context and reasoning budget.

## Execution order

File names begin with `<phase>.<task>[.<route>]`:

- `00.03-...md` is Phase 0, task 3.
- `01.02.a-...md` and `01.02.b-...md` are mutually exclusive implementations of Phase 1, task 2.
- Complete dependencies declared in the file, not merely the lexicographically previous file.
- For `route: choose-one:<group>`, complete exactly one file in that group unless a later comparison task explicitly asks for several disposable implementations.
- Files under `explorations/` are optional after their declared core dependencies.

## Lesser-model execution contract

Give the model only:

1. this file;
2. the selected issue file;
3. files named under **Allowed paths**;
4. outputs from completed dependencies that the issue explicitly references.

The implementing model must:

- inspect before editing and preserve unrelated work;
- use versions already pinned by `00.04`; never use `latest`;
- make changes only under **Allowed paths**;
- implement only the stated deliverables;
- add or update the listed tests and run the verification commands;
- stop and report a blocker if a required dependency, credential, device, or input fixture is absent;
- never weaken a test, security control, or acceptance threshold merely to pass;
- report changed files, commands run, results, assumptions, and remaining risks.

## Human/strong-model responsibilities

Architecture choices, route selection, credential authorization, hardware/cloud spending, destructive operations, production rollout, and acceptance of security/license risks remain reviewer decisions. A lesser model may implement a recorded decision but must not silently make one.

## Issue states

- `ready`: executable once dependencies exist.
- `decision`: produces an ADR or pinned choice; reviewer approval is part of acceptance.
- `hardware`: requires explicitly available hardware.
- `optional`: an exploration rather than a core dependency.

## Definition of done

An issue is complete only when all deliverables exist, verification passes, documentation is updated where requested, no unrelated files changed, and the reviewer can reproduce the result from a clean checkout.

Run `python3 issues/validate_backlog.py` after editing backlog metadata or file names.

## Concrete prompts

Copy-paste execution prompts live under `issues/prompts/` and use the same ID prefix as their issue. A prompt narrows ambiguity but never overrides its issue's allowed paths, dependencies, or acceptance criteria.
