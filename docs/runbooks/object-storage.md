# Kubernetes object storage runbook

`01.09.a` deploys Garage as the local S3-compatible object store inside the kind study cluster.

This is a single-node learning deployment. It is useful for ML artifacts, test datasets, and registry-style object storage in the lab, but it is not a production durability design.

## Apply and test

```bash
make apply-object-storage
make test-cluster-object-storage
```

`make apply-object-storage`:

1. creates the local Garage credential Secret;
2. applies the Garage StatefulSet, Services, and bootstrap Job;
3. waits for Garage to be ready;
4. bootstraps the layout, key, bucket, and bucket permission through the Garage CLI in the Garage pod;
5. waits for the bootstrap Job marker to complete.

## Local access

The in-cluster S3 service is:

```text
garage-s3.ml-platform-data.svc.cluster.local:3900
```

The integration tests access it from the laptop through a temporary port-forward on:

```text
http://127.0.0.1:13900
```

Use this manually if needed:

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-data svc/garage-s3 13900:3900
```

## Bucket

The default study bucket is:

```text
ml-platform-artifacts
```

The bucket is bootstrapped by the `garage-bootstrap` Job.

## Persistence smoke test

`make test-cluster-object-storage` writes an object, restarts the Garage pod, waits for the StatefulSet to become ready again, then reads the object back and checks its SHA-256 checksum.

That proves object data is backed by the Garage persistent volume rather than only by pod-local ephemeral storage.
