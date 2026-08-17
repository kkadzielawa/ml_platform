# Kubernetes access baseline

`02.04` maps the first Phase 2 identity groups to Kubernetes RBAC.

This document describes authorization policy only. It does not configure workstation OIDC login, Kubernetes API server OIDC flags, kubeconfig plugins, or production identity federation.

## Group mapping

| OIDC group | Kubernetes role | Scope | Intent |
|---|---|---|---|
| `platform-viewers` | `project-viewer` | `ml-platform-project-housing` | Read project workload status, logs, services, routes, jobs, and non-sensitive configuration. |
| `platform-learners` | `project-editor` | `ml-platform-project-housing` | Edit the study project workload resources without crossing namespace boundaries. |
| `platform-admins` | `platform-observer` | `ml-platform-system`, `ml-platform-data`, `ml-platform-observability` | Observe platform health and non-sensitive configuration without receiving mutation rights from this issue. |

## Deny-by-default decisions

- Viewers cannot create, update, patch, or delete workload resources.
- Viewers cannot read Secrets.
- Editors cannot access another project namespace.
- Editors cannot read Secrets in their own project namespace.
- Platform observers cannot read Secrets or mutate platform resources.
- This issue intentionally does not create a Kubernetes `cluster-admin` binding.

## Why `platform-admins` only receive observer RBAC here

The Phase 2 access matrix says platform admins eventually operate shared platform services. This issue is narrower: it proves group-based RBAC and explicit deny cases first.

Mutation/admin permissions for platform services should be added only when a later issue has a concrete workflow, test, and approval boundary.

## Validation

Apply:

```bash
make apply-rbac
```

Test:

```bash
make test-rbac
```

The tests use `kubectl auth can-i` with simulated usernames and OIDC group names. That means the RBAC policy can be verified before workstation OIDC login is configured.
