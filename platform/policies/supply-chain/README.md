# Supply-chain admission policies

Purpose: defines local study admission policies for signed-image enforcement.

Artifacts here eventually hold policy bundles, rollout notes, test fixtures, and exception rules for software supply-chain controls.

Implementation belongs to later backlog issues for production rollout, registry-specific keys, admission exceptions, and cluster-wide enforcement.

Current rollout mode:

- `ml-platform.local/namespace-class=project`: enforced for the Kyverno test image family.
- `ml-platform.local/namespace-class=platform`: explicitly staged as audit-only/documentation-only for this issue.

The project enforcement policy uses Kyverno's public signed/unsigned fixture image:

- signed allow image: `ghcr.io/kyverno/test-verify-image:signed`
- unsigned deny image: `ghcr.io/kyverno/test-verify-image:unsigned`

This keeps the lab runnable without publishing our own signed OCI image to Harbor yet. The previous issue signed a local blob/image digest for learning Cosign mechanics; future registry work can replace this sample key/image with our own registry-published image signatures.
