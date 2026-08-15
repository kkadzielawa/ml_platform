# ADR 0003: Phase 2 Least-Privilege Access Baseline

## Status

Proposed

## Context

Phase 2 introduces identity, secrets, CI, GitOps, and supply-chain controls. Later issues will install Keycloak, choose a secret-management route, choose CI and GitOps routes, and enforce image policy.

Without a shared access baseline, implementation issues could silently grant broad permissions such as cluster-admin, registry admin, unrestricted secret reads, or direct deployment authority to CI and runtime workloads.

## Decision

Adopt `docs/security/access-matrix.md` as the Phase 2 least-privilege baseline.

The baseline separates:

- human platform administration;
- project developer and viewer access;
- CI build and publish authority;
- GitOps reconciliation authority;
- runtime service identities;
- data/model/RAG/agent service identities;
- backup/restore authority.

All later Phase 2 implementation issues should map their concrete users, groups, service accounts, clients, tokens, and tests back to this matrix.

## Rationale

The study platform should learn production-shaped access boundaries without pretending the local laptop lab is production. A matrix-first approach keeps the early phase understandable while still forcing explicit decisions about owners, approval boundaries, deny cases, and credential lifetimes.

## Consequences

- Keycloak realm groups and clients should align to the matrix.
- Kubernetes RBAC tests should include both allowed and denied actions.
- Secret-management tasks should avoid plaintext values in Git and rendered manifests.
- CI identities should be unable to mutate the cluster directly unless a later issue records a narrow exception.
- GitOps controllers should reconcile only approved paths and namespaces.
- Agentic workflows inherit the same deny-by-default approach, especially for tool execution and side effects.

This ADR remains `Proposed` until the reviewer approves the baseline.
