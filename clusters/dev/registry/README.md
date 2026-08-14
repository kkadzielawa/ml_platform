# Dev registry deployment

This directory documents the local Kubernetes registry route for the study cluster.

Harbor is installed through the pinned Helm values in `platform/charts/harbor`, while local credentials are created by the `apply-registry` Make target.

The local route uses chart-managed filesystem storage. Garage-backed S3 storage was tested and deferred because Harbor's embedded Docker Distribution S3 driver returned `Invalid signature` against Garage during blob upload writes.

Additional registry manifests, Gateway exposure, external object storage, image signing policy, retention policy, and promotion workflows belong to later backlog issues.
