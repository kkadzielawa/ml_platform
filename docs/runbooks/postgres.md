# Kubernetes Postgres runbook

`01.08` installs CloudNativePG and creates a single-instance, non-HA study database in the local kind cluster.

This database is for platform learning only. It is intentionally not configured for high availability, backups, point-in-time recovery, or production retention.

## Apply and test

```bash
make apply-postgres
make test-cluster-postgres
```

`make apply-postgres` performs three steps:

1. installs the pinned CloudNativePG operator;
2. creates the application credential Secret in Kubernetes;
3. applies the `study-postgres` cluster manifest.

## Local credential handling

Credentials are not embedded in the committed Kubernetes manifests. The cluster manifest references this Secret:

```text
study-postgres-app
```

For local study, `make apply-postgres` creates that Secret from environment variables:

```bash
CLUSTER_POSTGRES_USER=study_app \
CLUSTER_POSTGRES_PASSWORD=local-dev-cluster-postgres-password \
make apply-postgres
```

The defaults are intentionally local-only. Use a real secret-management flow for shared or production environments.

## Service endpoint

Inside Kubernetes, applications use the CloudNativePG read-write service:

```text
study-postgres-rw.ml-platform-data.svc.cluster.local:5432
```

Database:

```text
study_app
```

User:

```text
study_app
```

## Inspecting status

```bash
kubectl --context kind-ml-platform-study-dev \
  get cluster,pod,pvc,svc -n ml-platform-data

kubectl --context kind-ml-platform-study-dev \
  describe cluster study-postgres -n ml-platform-data
```

## Persistence smoke test

`make test-cluster-postgres` writes a marker row, deletes the database pod, waits for CloudNativePG to bring it back, then verifies the marker row still exists.

This proves the database is using persistent storage rather than only ephemeral pod filesystem state.
