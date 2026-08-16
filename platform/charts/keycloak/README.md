# Keycloak local identity configuration

This directory records the pinned local Keycloak runtime choice for the Phase 2 study identity provider.

The current implementation uses direct Kubernetes manifests under `clusters/dev/identity` rather than a reusable Helm chart because the first issue needs one small, inspectable deployment with a declarative realm import.

Reusable chart packaging, production hardening, external federation, and high availability belong to later backlog issues.
