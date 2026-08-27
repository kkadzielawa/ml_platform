# Phase 2 end-to-end runbook

## Purpose

Phase 2 verifies the platform control-plane guardrails added during the identity, secrets, GitOps, and supply-chain issues.

Run:

```bash
make e2e-phase-02
```

The command writes:

- `tests/e2e/phase_02/reports/latest.json`
- `tests/e2e/phase_02/reports/phase-02-e2e-<timestamp>.json`

## What it verifies

The e2e runner executes the existing issue-level targets in order:

1. apply and test Kubernetes RBAC;
2. apply the OpenBao/External Secrets backend;
3. apply the OIDC fixture;
4. reset stale generated OIDC rotation routes from prior local runs;
5. run the secret-rotation test;
6. apply and test Argo CD GitOps reconciliation;
7. sign and verify the fixture image digest;
8. apply and test Kyverno admission policy.

The evidence report includes the current git commit and the signed fixture digest.

## Safety notes

This is a local study workflow. It does not perform destructive production credential rotation, cluster-wide admission enforcement, or external evidence publishing.

Report output is redacted for known local secret values. If you introduce new local secret environment variables, add them to `scripts/phase_02/e2e.py` before using this as evidence.
