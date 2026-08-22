# Build fixture digest notes

`make build-fixture` builds the fixture image twice and writes the observed image IDs to `build/reports/build-fixture-digests.txt`.

The two builds are expected to be identical when Docker BuildKit reuses the same source tree, base image digest, and build inputs.

The fixture build uses `--provenance=false` because `02.10` is only about deterministic local image construction. BuildKit provenance attestations can legitimately differ between repeated builds even when the runtime image manifest and config are unchanged. Later supply-chain issues own SBOMs, provenance, scans, and signing.
