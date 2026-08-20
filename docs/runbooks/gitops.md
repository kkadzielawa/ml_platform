# GitOps runbook

This runbook covers the local Argo CD route from issue `02.08.a`.

## Components

- Argo CD runs in `ml-platform-gitops`.
- Keycloak provides the configured OIDC identity provider.
- The root fixture application is `Application/ci-fixture`.
- The fixture source is this repository at `clusters/dev/ci` on `main`.

## Apply and test

```bash
make apply-gitops
make test-gitops
```

`make apply-gitops` installs the pinned Argo CD chart, registers an `argocd` OIDC client in Keycloak, applies the root Application, and waits for the fixture to sync.

`make test-gitops` verifies:

- Argo CD workloads are ready;
- OIDC configuration points at Keycloak;
- RBAC grants sync to platform admins and not to viewers;
- the fixture application syncs from Git;
- manual drift is detected and reconciled.

## Local access

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-gitops svc/argocd-server 18083:80
```

Then open:

```text
http://127.0.0.1:18083
```

The initial Argo CD admin password is stored in:

```bash
kubectl --context kind-ml-platform-study-dev get secret argocd-initial-admin-secret \
  -n ml-platform-gitops \
  -o jsonpath='{.data.password}' | base64 --decode
```

## Scope notes

This local lab wires OIDC configuration and Keycloak client registration, but the automated integration test uses the Argo CD API and Kubernetes state instead of driving a browser login through Keycloak.

Production promotion policy, secret-bearing Git repositories, and multi-environment promotion belong to later issues.
