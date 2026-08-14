# Kubernetes registry runbook

`01.10` installs Harbor as the local study container registry inside the kind cluster.

Harbor stores registry blobs in a chart-managed registry PVC for this local study route. Its metadata database and Redis cache are the lightweight internal services from the Harbor chart for now.

## Apply and test

```bash
make apply-registry
make test-registry
```

`make apply-registry`:

1. confirms the cluster and namespaces are available;
2. creates a local-only Harbor admin Secret;
3. installs pinned Harbor chart `1.19.1`;
4. waits for Harbor's core, registry, and nginx components to become available.

`make test-registry`:

1. opens a temporary port-forward to `svc/harbor`;
2. verifies Harbor health;
3. creates a tiny local Docker image;
4. logs in as the local admin;
5. pushes the image to Harbor;
6. pulls it back and verifies the digest matches;
7. confirms anonymous push is rejected.

## Local access

The in-cluster service is:

```text
harbor.ml-platform-system.svc.cluster.local:80
```

The integration test accesses Harbor from the laptop through:

```text
http://127.0.0.1:15000
```

Manual port-forward:

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-system svc/harbor 15000:80
```

Manual login:

```bash
docker login 127.0.0.1:15000 -u admin
```

The default local password is controlled by `HARBOR_ADMIN_PASSWORD` in the `Makefile`.

## Storage

The registry storage backend is a Kubernetes PVC mounted into Harbor's registry pod:

```text
/storage
```

Garage-backed S3 storage was tested during this issue and deferred. Harbor's embedded Docker Distribution S3 driver reached Garage, but Garage rejected registry upload writes with `403 Forbidden: Invalid signature`, even after path-style, insecure HTTP, and region overrides were applied.

That means the registry acceptance criteria can be validated with local filesystem storage now, while a later issue can revisit S3-compatible registry storage using MinIO, a newer registry backend, or a dedicated Garage compatibility route.

## Scope

This issue intentionally does not configure image scanning, signing, replication, retention policies, external object storage, external ingress, or production-grade credentials.
