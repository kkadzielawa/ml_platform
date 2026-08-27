# lakeFS runbook

Issue `03.04` deploys lakeFS as the study platform's Git-like data versioning service.

## Purpose

lakeFS sits in front of the selected object store and adds repository, branch, commit, merge, and tag semantics for data. It lets later data-pipeline issues treat data changes more like source-code changes.

## Local deployment

```bash
make apply-lakefs
make test-lakefs
```

`make apply-lakefs`:

1. ensures the kind cluster, PostgreSQL, and scoped Garage data storage are available;
2. creates `Secret/lakefs-secrets` with the PostgreSQL connection string and lakeFS auth encryption key;
3. creates `Secret/lakefs-admin-credentials` for the local integration test admin user;
4. installs or upgrades the pinned upstream `lakefs/lakefs` Helm chart;
5. waits for the lakeFS deployment to become available.

## Local access

Forward the service:

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-data svc/lakefs 18084:80
```

Then open:

```text
http://127.0.0.1:18084
```

The test admin credentials are stored in:

```text
Secret/lakefs-admin-credentials
```

## Storage

Metadata uses the existing CloudNativePG `study-postgres` cluster. Object data uses the Garage-backed `ml-platform-artifacts` bucket under lakeFS repository prefixes such as:

```text
s3://ml-platform-artifacts/lakefs/<repository>/
```

Credentials are injected from Kubernetes Secrets. They are not embedded in Helm values or repository configuration.

## What the test proves

`make test-lakefs` creates a temporary repository and verifies:

- initial commit on `main`;
- branch creation;
- second commit with different object contents;
- merge back to `main`;
- tag creation;
- read by exact commit ID returns distinct historical contents.

The test deletes its temporary repository at the end.

## Non-goals

This study deployment does not configure production garbage collection, high availability, external ingress, large-data performance tuning, or external identity integration.
