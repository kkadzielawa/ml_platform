# ADR 0002: Development Cluster Route

## Status

Accepted

## Context

Phase 1 introduces a local Kubernetes development cluster for the study platform. The governing charter requires laptop-compatible, CPU-first, open source, zero-cloud-spend workflows. The recorded host is an Ubuntu Linux laptop with Docker Engine available, 8 logical CPUs, 15 GiB memory, and enough local disk for a small disposable cluster.

The available Phase 1 route choices are:

- `01.02.a`: kind
- `01.02.b`: k3d
- `01.02.c`: K3s

## Decision

Select `01.02.a — kind` as the required Phase 1 cluster route.

## Rationale

kind is the preferred first route because it is Docker-backed, disposable, common in Kubernetes development and CI, and minimally invasive to the host. It fits the study goal of learning Kubernetes platform mechanics without committing the laptop to a persistent bare-metal-style cluster.

k3d remains a reasonable alternative but is deferred to avoid tool comparison before the first local cluster path exists. K3s is deferred because it is more host-invasive and persistent than needed for the first Phase 1 route.

## Consequences

- `01.02.a` is the next route to implement.
- `01.02.b` and `01.02.c` are not implemented unless a later comparison or hardware-specific issue explicitly revisits them.
- The first cluster implementation should optimize for safe create/status/delete workflows and exact cluster-name protection.
- Persistent storage, production HA, and bare-metal operations remain out of scope for the first cluster route.

