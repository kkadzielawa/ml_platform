# Base manifests

This directory contains environment-neutral Kubernetes manifests and Kustomize entries.

Rules:

- no hostnames, localhost ports, credentials, node names, or laptop-specific values;
- no namespace creation until `01.04`;
- no application installation until the owning backlog issue;
- every image reference introduced under this tree must be immutable, preferably digest-pinned.

Environment-specific values belong under `clusters/dev/**` or a later overlay.

