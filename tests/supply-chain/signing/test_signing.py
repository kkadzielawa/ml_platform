from __future__ import annotations

import json
import base64
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
COSIGN_DIR = REPO_ROOT / "config" / "cosign"


def test_signing_artifacts_exist_without_private_key_material() -> None:
    expected = [
        "build-fixture.digest.txt",
        "build-fixture.digest.sig",
        "build-fixture.digest.bundle.json",
        "build-fixture.sbom.attestation.json",
        "build-fixture.sbom.bundle.json",
        "cosign.pub",
        "signing-summary.json",
    ]

    for name in expected:
        assert (COSIGN_DIR / name).exists()

    forbidden_suffixes = {".key", ".pem"}
    for path in COSIGN_DIR.rglob("*"):
        assert path.suffix not in forbidden_suffixes
        if path.is_file():
            content = path.read_text(encoding="utf-8", errors="ignore")
            assert "PRIVATE KEY" not in content


def test_signing_summary_matches_signed_digest() -> None:
    summary = json.loads((COSIGN_DIR / "signing-summary.json").read_text(encoding="utf-8"))
    digest = (COSIGN_DIR / "build-fixture.digest.txt").read_text(encoding="utf-8").strip()

    assert summary["signed_digest"] == digest
    assert summary["private_key_committed"] is False
    assert summary["signature"] == "config/cosign/build-fixture.digest.sig"
    assert summary["sbom_attestation"] == "config/cosign/build-fixture.sbom.attestation.json"


def test_sbom_attestation_references_spdx_predicate() -> None:
    attestation = json.loads((COSIGN_DIR / "build-fixture.sbom.attestation.json").read_text(encoding="utf-8"))
    if "payload" in attestation:
        payload = json.loads(base64.b64decode(attestation["payload"]))
    else:
        payload = attestation

    assert payload["_type"] in {
        "https://in-toto.io/Statement/v0.1",
        "https://in-toto.io/Statement/v1",
    }
    assert payload["predicateType"] == "https://spdx.dev/Document"
    assert payload["subject"][0]["digest"]["sha256"]
