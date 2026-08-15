# Phase 1 e2e runbook

`01.13` automates the local Kubernetes Phase 1 smoke workflow.

The target is intentionally destructive only for the exact disposable kind cluster named `ml-platform-study-dev`. The cluster scripts refuse unexpected names before create or delete operations.

## Run

```bash
make e2e-phase-01
```

The workflow:

1. proves `scripts/cluster/delete-kind.sh` refuses an unexpected cluster name;
2. deletes the exact study cluster if it exists;
3. creates the kind cluster from an absent state;
4. applies the TLS/gateway foundation;
5. applies default-deny network policies;
6. runs positive and negative network-policy tests;
7. applies PostgreSQL;
8. runs PostgreSQL persistence smoke tests;
9. applies Garage object storage;
10. runs Garage object-storage persistence smoke tests;
11. runs the Phase 1 backup/restore fixture drill;
12. deletes the exact study cluster;
13. confirms the cluster is absent.

## Report

The command writes a timestamped JSON report under:

```text
tests/e2e/phase_01/reports/
```

It also writes:

```text
tests/e2e/phase_01/reports/latest.json
```

The report records command outcomes, elapsed time, redacted stdout/stderr tails, safe deletion-guard evidence, and final cleanup status.

## Boundaries

This workflow does not install Phase 2 identity, GitOps, workload scheduling, feature store, LLM, RAG, or agent services.

It validates the Phase 1 foundation only: local cluster creation, gateway/TLS foundation, network controls, storage/database persistence, backup/restore fixture behavior, and safe cleanup.
