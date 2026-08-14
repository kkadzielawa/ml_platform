# Harbor chart configuration

This directory contains the pinned Helm values used to install Harbor as the study platform's in-cluster container registry.

The values here are for the local kind environment: ClusterIP exposure, constrained resources, chart-managed filesystem registry storage, and scanners disabled.

Garage-backed S3 storage was tested for this issue, but Docker Distribution's S3 driver returned `Invalid signature` on blob upload writes. A later issue can revisit S3-compatible registry storage with MinIO, a newer registry backend, or a dedicated Garage compatibility route.

Production registry hardening, image signing, vulnerability scanning, replication, retention policies, external object storage, and ingress exposure belong to later backlog issues.
