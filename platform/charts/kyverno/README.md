# Kyverno chart configuration

Purpose: records the pinned Kyverno Helm chart used for local admission-control study work.

Artifacts here eventually hold environment-specific Helm values and version notes for the policy engine.

Implementation belongs to later backlog issues when production-grade admission rollout, HA sizing, and policy reporting are introduced.

Current study pin:

- chart: `kyverno/kyverno`
- chart version: `3.8.2`
- app version: `v1.18.2`
- repo: `https://kyverno.github.io/kyverno`

This pin is selected for the local Kubernetes 1.34 kind cluster line; Kyverno release docs list v1.18 as supporting Kubernetes v1.33-v1.35.
