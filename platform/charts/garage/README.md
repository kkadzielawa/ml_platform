# Garage cluster deployment

This directory records the selected object-storage route for Phase 1: Garage as a lightweight S3-compatible study backend.

The current issue uses direct Kubernetes manifests under `clusters/dev/storage` rather than a reusable Helm chart. A first-party chart can be introduced by a later backlog issue if the manifest set grows.

Multi-node durability, production storage tuning, and Ceph are intentionally out of scope for this route.
