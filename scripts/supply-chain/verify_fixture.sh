#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cosign_image="${COSIGN_IMAGE:?COSIGN_IMAGE is required}"
artifact_dir="${COSIGN_ARTIFACT_DIR:-config/cosign}"

cd "$repo_root"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$repo_root:/workspace:ro" \
  -w /workspace \
  "$cosign_image" \
  verify-blob \
  --key "$artifact_dir/cosign.pub" \
  --bundle "$artifact_dir/build-fixture.digest.bundle.json" \
  --insecure-ignore-tlog \
  "$artifact_dir/build-fixture.digest.txt"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$repo_root:/workspace:ro" \
  -w /workspace \
  "$cosign_image" \
  verify-blob-attestation \
  --key "$artifact_dir/cosign.pub" \
  --bundle "$artifact_dir/build-fixture.sbom.bundle.json" \
  --type spdxjson \
  --insecure-ignore-tlog \
  "$artifact_dir/build-fixture.digest.txt"

tampered_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$tampered_dir"
}
trap cleanup EXIT

printf 'sha256:0000000000000000000000000000000000000000000000000000000000000000\n' > "$tampered_dir/tampered-digest.txt"

if docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$repo_root:/workspace:ro" \
  -v "$tampered_dir:/tampered:ro" \
  -w /workspace \
  "$cosign_image" \
  verify-blob \
  --key "$artifact_dir/cosign.pub" \
  --bundle "$artifact_dir/build-fixture.digest.bundle.json" \
  --insecure-ignore-tlog \
  /tampered/tampered-digest.txt >/tmp/ml-platform-cosign-tampered.out 2>&1; then
  cat /tmp/ml-platform-cosign-tampered.out
  echo "expected tampered digest verification to fail"
  exit 1
fi

echo "tampered digest verification failed as expected"
