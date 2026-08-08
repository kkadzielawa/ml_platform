# Development cluster requirements

## Scope

This contract defines the Phase 1 local development cluster target. The cluster is for study, reproducibility, and disposable platform exercises on the primary Linux laptop. It is not a production cluster and must not host regulated data, paid cloud resources, or long-running business workloads.

## Recorded host

- Host OS: Ubuntu 24.04 family Linux, kernel `7.0.0-28-generic`, `x86_64`.
- CPU: Intel Core i7-7700HQ, 4 physical cores / 8 logical CPUs, VT-x available.
- Memory: 15 GiB reported by the OS; 16 GiB laptop class from the charter.
- Disk: project filesystem has approximately 164 GiB free at recording time.
- GPU: NVIDIA GTX 1050 Ti Mobile is known from the charter but is not required or assumed for Phase 1.
- Container runtime: Docker Engine `29.6.1`, `runc`, cgroup driver `systemd`, cgroup v2.

## Minimum resource contract

- CPU: reserve at least 4 logical CPUs for the local cluster path; keep enough headroom for the browser, editor, and host services.
- Memory: reserve up to 8 GiB for cluster workloads; avoid enabling heavyweight stacks together until their issue explicitly requires it.
- Disk: reserve at least 40 GiB free for images, local volumes, logs, and throwaway platform artifacts.
- Network: bind local ingress ports only to `127.0.0.1` unless an issue explicitly records a different exposure.

These requirements fit the Phase 0 charter because they remain CPU-first, local-only, and within the single-laptop/zero-cloud-spend constraint.

## Kubernetes target

- Kubernetes version target: a pinned Kubernetes `v1.34.x` local cluster line for Phase 1.
- Selected `01.02` route: `01.02.a — kind`.
- Deferred routes:
  - `01.02.b — k3d`, useful but deferred to avoid comparing two Docker-backed local cluster tools before the first route exists.
  - `01.02.c — K3s`, deferred because it is more persistent and host-invasive than needed for the first disposable study cluster.

The exact node image and cluster tool versions belong to `01.02.a`; this issue records the host contract and route choice only.

## Ports

Reserve these localhost ports for the first development cluster route unless a later issue records a change:

- HTTP ingress: `127.0.0.1:8080`
- HTTPS ingress: `127.0.0.1:8443`
- Kubernetes API: cluster-tool default unless explicitly mapped by the selected route.
- Existing Phase 0 services remain outside the cluster while Phase 1 is being introduced:
  - PostgreSQL: `127.0.0.1:5432`
  - Garage S3 API: `127.0.0.1:3900`
  - Garage admin API: `127.0.0.1:3903`
  - MLflow: `127.0.0.1:5000`
  - Prometheus: `127.0.0.1:19090`
  - Grafana: `127.0.0.1:13000`
  - Baseline FastAPI manual service: `127.0.0.1:18080`

## Disposable and persistent boundaries

Disposable:

- local Kubernetes cluster nodes;
- test namespaces;
- sample workloads;
- generated manifests from smoke tests;
- temporary images and local cluster volumes unless explicitly promoted by a later issue.

Persistent:

- repository source code, contracts, ADRs, runbooks, and tests;
- pinned version catalog entries;
- reviewed configuration under `clusters/**` once created by later issues;
- intentionally retained Phase 0 Docker volumes for PostgreSQL/Garage/MLflow unless a cleanup command is explicitly invoked.

No cluster issue may delete broad host paths, the repository, the user home directory, or Phase 0 volumes as an implicit side effect.

## Minimum smoke test

The selected Phase 1 cluster route must provide a noninteractive smoke test that verifies:

1. the cluster can be created from the checked-in configuration;
2. `kubectl` can reach the expected cluster context;
3. all expected nodes are `Ready`;
4. a trivial workload can be scheduled;
5. the exact study cluster can be deleted and recreated.

## Destruction and Recreate expectations

Recreate must be safe and boring:

- create, status, and delete commands must target exactly the recorded study cluster name;
- delete commands must refuse an empty, wildcard, or unexpected cluster name;
- the cluster must be disposable enough to delete and recreate during study sessions;
- deleting the cluster must not delete repository files, Phase 0 service volumes, or unrelated Docker resources;
- after Recreate, the minimum smoke test must pass again.

