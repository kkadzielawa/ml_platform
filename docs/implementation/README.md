# Implementation review and improvement plan

Reviewed: 2026-09-07. Scope: the working tree at commit `73bb39f8651c57cc15b66913428b5b10c2652bb9`, including uncommitted OpenMetadata work.

This folder is a **planning deliverable**. No proposed repair, deployment, route change, or commit is authorized merely by appearing here. The review changed only Markdown under this folder. Existing implementation files and backlog files remain as found.

Start with [the overall assessment](00.01-overall-assessment.md), [documentation gaps](00.02-documentation-gaps.md), and [the future learning route](00.03-future-learning-route.md). The numbered task files are specifications for later implementation sessions, not evidence that those changes have been made.

## Reading and execution order

Task IDs use `IMP-` to avoid collision with the original backlog. Numbers indicate recommended order within this review, not replacement phase numbers. Suffixes `.a` and `.b` are mutually exclusive routes. Follow declared dependencies rather than executing every file sequentially.

P1 means a correctness, evidence, or integration concern to address before relying on the affected capability. It is not a claim of a production emergency. P2 means a useful next improvement before scaling or broadening the learning path. These tasks do not all need to finish before the next original issue.

| ID | Proposed task | Priority | Dependency |
|---|---|---|---|
| [IMP-01.01](01.01-openmetadata-settings-sync.md) | Make persisted OpenMetadata OIDC updates verifiable | P1 | None |
| [IMP-01.02](01.02-openmetadata-upgrade-lifecycle.md) | Make OpenMetadata apply safe to repeat under study quotas | P1 | None |
| [IMP-01.03](01.03-openmetadata-browser-sso.md) | Verify the complete OpenMetadata login session | P1 | IMP-01.01 and IMP-01.02 |
| [IMP-01.04](01.04-openmetadata-quality-results.md) | Register actual quality results in OpenMetadata | P1 | None; coordinate with IMP-02.04 selected route |
| [IMP-01.05](01.05-openmetadata-lineage-registration.md) | Publish and retrieve catalog lineage | P1 | None |
| [IMP-02.01](02.01-ingestion-cache-identity.md) | Invalidate ingestion reuse when processing changes | P1 | None |
| [IMP-02.02](02.02-ingestion-failure-evidence.md) | Preserve failure events and distinguish post-commit failures | P1 | None |
| [IMP-02.03](02.03-truthful-run-provenance.md) | Separate real artifacts from placeholder provenance | P1 | None |
| [IMP-02.04.a](02.04.a-real-great-expectations.md) | Execute the selected Great Expectations engine | P1 | Choose exactly one IMP-02.04 route |
| [IMP-02.04.b](02.04.b-label-custom-validator.md) | Record the custom Polars validator as the selected route | P2 | Reviewer selects this instead of IMP-02.04.a |
| [IMP-03.01](03.01-contract-validation-boundary.md) | Use one tested contract-validation implementation | P2 | None; coordinate schema changes with IMP-02.03 |
| [IMP-03.02](03.02-reproducible-python-environments.md) | Make clean-checkout environments explicit | P2 | None |
| [IMP-03.03](03.03-serving-readiness.md) | Make readiness mean the pinned model can serve | P2 | None |
| [IMP-04.01](04.01-helm-context-consistency.md) | Bind Helm and kubectl to the same cluster | P1 | None |
| [IMP-04.02](04.02-port-forward-ownership.md) | Detect occupied ports and failed forwards | P2 | None |
| [IMP-04.03](04.03-study-resource-profiles.md) | Turn laptop limits into an executable preflight | P2 | None |
| [IMP-05.01](05.01-license-policy-enforcement.md) | Make executable license checks match the written policy | P1 | None |
| [IMP-05.02](05.02-secret-safe-command-output.md) | Keep bootstrap credentials out of command transcripts | P1 | None |
| [IMP-05.03](05.03-real-ci-trigger.md) | Prove a commit actually runs through Woodpecker | P2 | None |
| [IMP-05.04](05.04-data-recovery-followup.md) | Inventory recovery gaps and prove one database restore | P2 | None |
| [IMP-06.01](06.01-documentation-and-completion-ledger.md) | Make implemented scope and completion evidence navigable | P1 | None |
| [IMP-06.02](06.02-cpu-first-learning-route.md) | Define a reachable CPU route to RAG and bounded agents | P2 | None; reviewer approves route before implementation |

## Suggested batches

1. Document current reality: IMP-06.01, then record the evidence gaps in 03.10. This is useful even before runtime work resumes.
2. Finish the current catalog learning slice: IMP-01.01 → IMP-01.03 (with IMP-01.02), plus IMP-01.04 and IMP-01.05. Do not close 03.10 based only on a healthy pod or a ConfigMap.
3. Make data reuse and evidence dependable: IMP-02.01, IMP-02.02, IMP-02.03; select one IMP-02.04 route.
4. Improve repeatable execution and policy: IMP-04.01, IMP-05.01, IMP-05.02, then the remaining environment/readiness/resource tasks as needed.
5. Resume the original Phase 3 exit and Phase 4 pipeline work. Use IMP-06.02 to plan a CPU learning branch; revisit full CI and recovery before depending on them.

Do not turn this review into a requirement to install more products. Most recommendations improve behavior and evidence around components already selected.

## Smaller-model handoff contract

Give the model this README, exactly one selected task, the referenced original issue, and the implementation files named in that task. Read relevant dependency output before editing. Each task contains evidence, scoped paths, actions, tests and non-goals.

The task's paths are a proposed scope for a future authorized session. If they conflict with the original issue, document the needed exception in that session; this review does not silently expand the original issue. User-authorized exceptions already recorded in the conversation still apply.

Use this prompt:

> Implement only TASK-ID from docs/implementation/SELECTED-FILE.md. Inspect its evidence and current files first; the review may be stale. Preserve unrelated work. Complete the smallest bounded change described. Do not implement sibling alternatives or unrelated findings. Use pinned APIs and versions; verify upstream documentation if an API is unknown. Run the stated checks, distinguishing unit/fake-service, static/rendered, and live results. Do not weaken tests or invent evidence. Update only the task's relevant runbook after behavior is verified. Do not commit or push unless asked. Report changed files, exact verification outcomes, assumptions and remaining blockers. If a task is too large, finish one explicitly identified substep and report it as partial.

No plan can guarantee a smaller model succeeds unaided. Review architecture decisions, auth changes, schema migrations and lifecycle operations yourself. Passing tests is necessary but is only evidence for the behavior those tests exercise.

## Verification performed for this review

The following existing offline checks ran without deployment operations:

```bash
.venv/bin/python -m pytest -q tests/test_smoke.py tests/config tests/contracts tests/unit/data tests/data_quality tests/integration/ingestion tests/integration/lineage tests/integration/openmetadata
python3 issues/validate_backlog.py
```

Results: **51 passed, 1 skipped**; **310 issues across 37 alternative route groups validated**. The skipped check is live OpenMetadata integration. The ingestion/lineage checks in this selection use local fixtures/fakes; directory naming does not make them live integration tests.

Additional read-only probes confirmed the license checker accepts `NOASSERTION` and `MIT AND BUSL-1.1`, and the runtime manifest validator ignores an added `minimum` constraint. These are focused demonstrations, not a full security audit.

No live SSO, cluster availability, clean-environment installation, full CI trigger, or disaster recovery was tested in this review. Previous conversation outcomes are historical context, not current verification.

