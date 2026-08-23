# Fixture signing runbook

## Purpose

`02.13` signs the accepted local fixture image digest and creates a signed SBOM attestation using pinned Cosign.

This is a local study workflow. It does not create production keys, publish signatures to a registry, or enforce admission policy.

## Tool

Pinned Cosign image:

```text
gcr.io/projectsigstore/cosign:v3.0.6@sha256:de9c65609e6bde17e6b48de485ee788407c9502fa08b8f4459f595b21f56cd00
```

## Local key flow

`make sign-fixture` creates an ephemeral study key pair in a temporary directory.

Committed artifacts include:

- `config/cosign/cosign.pub`
- `config/cosign/build-fixture.digest.txt`
- `config/cosign/build-fixture.digest.sig`
- `config/cosign/build-fixture.digest.bundle.json`
- `config/cosign/build-fixture.sbom.attestation.json`
- `config/cosign/build-fixture.sbom.bundle.json`
- `config/cosign/signing-summary.json`

Private key material is deleted before the command exits and must not be committed.

## Commands

Sign:

```bash
make sign-fixture
```

Verify:

```bash
make verify-fixture
```

Verification checks:

- signature verifies for the accepted fixture digest;
- SBOM attestation verifies for the accepted fixture digest;
- a tampered digest fails verification.
