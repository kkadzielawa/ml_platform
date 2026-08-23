# Cosign signing artifacts

This directory contains public, reproducible study artifacts for `02.13`.

Committed files may include:

- accepted fixture digest;
- public study key;
- blob signature;
- SBOM attestation;
- verification notes.

Private key material must never be committed. `make sign-fixture` creates the study private key in a temporary directory and deletes it before exiting.
