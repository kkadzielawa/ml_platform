# Secrets runbook

`02.05.a` installs the study secrets-management route: OpenBao plus External Secrets Operator.

This route is intentionally local and educational. It is not a production unseal design, not HSM/KMS-backed, and not a broad migration of every platform secret.

## Components

| Component | Purpose | Local scope |
|---|---|---|
| OpenBao | Stores the source secret value. | Single-node standalone server with file storage on a PVC. |
| External Secrets Operator | Reads from OpenBao and creates Kubernetes Secrets. | Runs in `ml-platform-system`. |
| `SecretStore/openbao-housing` | Names the OpenBao backend and auth token for one namespace. | `ml-platform-project-housing`. |
| `ExternalSecret/housing-database-credential` | Syncs one scoped database credential. | Creates `Secret/housing-database-credential`. |

## Apply and test

```bash
make apply-secrets
make test-secrets
```

`make apply-secrets`:

1. ensures the local cluster and baseline PostgreSQL dependency exist;
2. installs pinned OpenBao chart values;
3. installs pinned External Secrets Operator chart values;
4. initializes and unseals OpenBao if needed;
5. enables a `kv-v2` engine at `kv/`;
6. writes one generated study credential to OpenBao if it does not already exist;
7. creates a scoped OpenBao policy and token for External Secrets;
8. stores that scoped token in the project namespace;
9. applies the `SecretStore` and `ExternalSecret`;
10. waits until the synced Kubernetes Secret is ready.

## Study bootstrap material

The local route stores OpenBao root and unseal material in:

```text
Secret/openbao-bootstrap
Namespace/ml-platform-system
```

This is acceptable only for this local study route. Production routes should use a real unseal and custody model such as KMS/HSM plus documented break-glass controls.

## Synced credential

OpenBao path:

```text
kv/projects/housing/database/study-reader
```

Kubernetes target:

```text
Secret/housing-database-credential
Namespace/ml-platform-project-housing
```

The secret value is generated during apply. It is not committed to Git and does not appear in rendered manifests.

## Access boundary

The `unauthorized-secret-reader` service account is intentionally not granted permission to read either:

- `Secret/housing-database-credential`;
- `Secret/openbao-housing-reader-token`.

The integration test verifies both deny cases with `kubectl auth can-i`.

## Useful commands

Check OpenBao:

```bash
kubectl --context kind-ml-platform-study-dev get pod openbao-0 -n ml-platform-system
```

Check External Secrets:

```bash
kubectl --context kind-ml-platform-study-dev get externalsecret,secretstore \
  -n ml-platform-project-housing
```

Inspect synced Secret keys without printing values:

```bash
kubectl --context kind-ml-platform-study-dev get secret housing-database-credential \
  -n ml-platform-project-housing \
  -o jsonpath='{.data}' | jq 'keys'
```

## Boundaries

This issue does not:

- configure production auto-unseal;
- deploy OpenBao HA;
- configure audit storage;
- migrate all existing platform credentials;
- grant applications broad secret-reading permissions;
- commit encrypted or plaintext secrets to Git.
