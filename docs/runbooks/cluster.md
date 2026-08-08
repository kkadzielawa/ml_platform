# Development cluster runbook

## Purpose

Phase 1 introduces a disposable local Kubernetes cluster for the study platform. The selected route is `01.02.a — kind`, recorded in `adr/0002-development-cluster-route.md`.

This cluster is for learning platform mechanics: namespaces, quotas, ingress, policies, operators, and later ML platform components. It is not a production cluster.

## Requirements

- Docker Engine is installed and running.
- `kind` is installed.
- `kubectl` is installed.
- Ports `127.0.0.1:8080` and `127.0.0.1:8443` are available for future local ingress.

The recorded host contract lives in `docs/platform/cluster-requirements.md`.

## Cluster identity

- Required cluster name: `ml-platform-study-dev`
- Kubernetes context: `kind-ml-platform-study-dev`
- Config: `clusters/dev/kind/cluster.yaml`
- Node image: `kindest/node:v1.34.0@sha256:7416a61b42b1662ca6ca89f02028ac133a309a2a30ba309614e8ec94d976dc5a`

The scripts refuse unexpected cluster names so an accidental environment override does not target another cluster.

## Commands

Create the cluster:

```bash
make cluster-create
```

Check status:

```bash
make cluster-status
```

Delete the exact study cluster:

```bash
make cluster-delete
```

## Expected topology

- one control-plane node;
- two worker nodes;
- worker labels for general platform workloads and ML workloads;
- localhost port mappings reserved for later ingress:
  - HTTP: `127.0.0.1:8080`
  - HTTPS: `127.0.0.1:8443`

## Recreate expectation

The cluster is disposable. It should be safe to run:

```bash
make cluster-delete
make cluster-create
make cluster-status
```

Delete only removes the exact kind cluster named `ml-platform-study-dev`. It must not delete repository files, Phase 0 Docker volumes, unrelated Docker containers, or other Kubernetes clusters.

## Common failures

- `kind` is missing: install kind, then rerun `make cluster-create`.
- `kubectl` is missing: install kubectl, then rerun `make cluster-status`.
- Docker is unavailable: start Docker and rerun the command.
- Port `8080` or `8443` is already in use: stop the conflicting process before creating the cluster.
- A different cluster name is supplied: unset `KIND_CLUSTER_NAME`; the scripts only allow `ml-platform-study-dev`.

