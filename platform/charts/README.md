# Helm chart conventions

This directory is reserved for first-party Helm charts created by later backlog issues.

Conventions:

- one chart per deployable platform component;
- chart names use the repository naming convention from `docs/conventions.md`;
- chart defaults must be safe, local-study defaults only;
- environment-specific values belong in overlay value files, not chart templates;
- values files must be named by environment and purpose, such as `values-dev.yaml` or `values-dev-kind.yaml`;
- chart templates must emit standard labels compatible with the Kustomize conventions in `docs/platform/manifests.md`;
- container images must be digest-pinned or otherwise immutable before a chart is accepted by `make test-manifests`.

No chart is created in `01.03`; later issues own component installation.

