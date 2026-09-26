# Standalone Kubeflow Pipelines source

Issue `04.03.a` uses the upstream standalone Kubeflow Pipelines development
manifest at Git tag `2.17.0` (`4a3592cb2dd0a91a4652ab93893ec8beda1f3158`).

The local overlay in `clusters/dev/pipelines/` keeps the upstream control plane
but makes study-specific choices: it pins KFP server image tags to `2.17.0`,
uses the existing Garage S3 endpoint for artifacts, removes the development
public proxy and SeaweedFS, and applies a namespace resource budget. It does
not install the full Kubeflow distribution.

The upstream cluster-scoped CRDs are applied separately by
`make apply-orchestrator`; they must use the same upstream Git tag as the
namespaced overlay.
