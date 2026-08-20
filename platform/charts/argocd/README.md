# Argo CD chart configuration

This directory contains the pinned Helm values for the local Argo CD GitOps route.

The values are sized for the kind study cluster: one replica per required component, local-only HTTP access, direct OIDC configuration for Keycloak, and optional subcomponents disabled until later issues need them.

Production promotion policy, external ingress, HA Redis, SSO hardening, and secret management for Git credentials belong to later backlog issues.
