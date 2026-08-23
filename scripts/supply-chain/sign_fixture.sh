#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cosign_image="${COSIGN_IMAGE:?COSIGN_IMAGE is required}"
fixture_image="${BUILD_FIXTURE_IMAGE:?BUILD_FIXTURE_IMAGE is required}"
artifact_dir="${COSIGN_ARTIFACT_DIR:-config/cosign}"
key_prefix="cosign-study"

cd "$repo_root"
mkdir -p "$artifact_dir"
rm -f \
  "$artifact_dir/build-fixture.digest.bundle.json" \
  "$artifact_dir/build-fixture.digest.sig" \
  "$artifact_dir/build-fixture.sbom.attestation.json" \
  "$artifact_dir/build-fixture.sbom.bundle.json" \
  "$artifact_dir/signing-summary.json"

image_id="$(docker image inspect "$fixture_image" --format '{{.Id}}')"
printf '%s\n' "$image_id" > "$artifact_dir/build-fixture.digest.txt"

key_dir="$(mktemp -d)"
chmod 0777 "$key_dir"
cleanup() {
  rm -rf "$key_dir"
}
trap cleanup EXIT

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e COSIGN_PASSWORD= \
  -v "$key_dir:/keys" \
  -w /keys \
  "$cosign_image" \
  generate-key-pair --output-key-prefix "$key_prefix"

cp "$key_dir/$key_prefix.pub" "$artifact_dir/cosign.pub"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e COSIGN_PASSWORD= \
  -v "$key_dir:/keys:ro" \
  -v "$repo_root:/workspace" \
  -w /workspace \
  "$cosign_image" \
  sign-blob \
  --key "/keys/$key_prefix.key" \
  --use-signing-config=false \
  --bundle "$artifact_dir/build-fixture.digest.bundle.json" \
  --yes \
  "$artifact_dir/build-fixture.digest.txt" \
  > "$artifact_dir/build-fixture.digest.sig"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e COSIGN_PASSWORD= \
  -v "$key_dir:/keys:ro" \
  -v "$repo_root:/workspace" \
  -w /workspace \
  "$cosign_image" \
  attest-blob \
  --key "/keys/$key_prefix.key" \
  --use-signing-config=false \
  --predicate config/syft/build-fixture.spdx.json \
  --type spdxjson \
  --bundle "$artifact_dir/build-fixture.sbom.bundle.json" \
  --yes \
  "$artifact_dir/build-fixture.digest.txt" \
  > "$artifact_dir/build-fixture.sbom.attestation.json"

cat > "$artifact_dir/signing-summary.json" <<JSON
{
  "fixture_image": "$fixture_image",
  "signed_digest": "$image_id",
  "private_key_committed": false,
  "public_key": "$artifact_dir/cosign.pub",
  "signature": "$artifact_dir/build-fixture.digest.sig",
  "sbom_attestation": "$artifact_dir/build-fixture.sbom.attestation.json"
}
JSON
