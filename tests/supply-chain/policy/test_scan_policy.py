from __future__ import annotations

import json
import importlib.util
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = REPO_ROOT / "config" / "license-policy" / "policy.json"
TRIVY_CONFIG = REPO_ROOT / "config" / "trivy" / "trivy.yaml"
SCAN_REPORT = REPO_ROOT / "config" / "trivy" / "build-fixture.scan.json"
SPDX_SBOM = REPO_ROOT / "config" / "syft" / "build-fixture.spdx.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
POLICY_MODULE_PATH = REPO_ROOT / "config" / "license-policy" / "check_policy.py"

spec = importlib.util.spec_from_file_location("check_policy", POLICY_MODULE_PATH)
assert spec is not None
check_policy = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(check_policy)


def test_pinned_trivy_configuration_is_not_ignoring_unfixed_vulnerabilities() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    trivy_config = TRIVY_CONFIG.read_text(encoding="utf-8")

    assert "export TRIVY_VERSION ?= 0.72.0" in makefile
    assert "docker.io/aquasec/trivy:$(TRIVY_VERSION)@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f" in makefile
    assert "ignore-unfixed: false" in trivy_config
    assert "--ignore-unfixed=false" in makefile


def test_approved_fixture_scan_and_license_policy_pass() -> None:
    policy = check_policy.read_json(POLICY)
    scan = check_policy.read_json(SCAN_REPORT)
    spdx = check_policy.read_json(SPDX_SBOM)

    assert scan["ArtifactName"] == "ml-platform-study/build-fixture:local"
    assert scan["ArtifactType"] == "container_image"
    assert "Results" in scan
    assert check_policy.check_exception_schema(policy) == []
    assert check_policy.check_spdx_licenses(policy, spdx) == []


def test_seeded_forbidden_secret_fixture_fails() -> None:
    findings = check_policy.find_forbidden_secrets(FIXTURES)

    assert findings == [str(FIXTURES / "forbidden-secret.env")]


def test_seeded_forbidden_license_fixture_fails() -> None:
    policy = check_policy.read_json(POLICY)
    bad_spdx = check_policy.read_json(FIXTURES / "forbidden-license.spdx.json")

    violations = check_policy.check_spdx_licenses(policy, bad_spdx)

    assert violations == [
        "forbidden license AGPL-3.0-only on package bad-license-package",
    ]


def test_policy_cli_fails_seeded_forbidden_license_fixture(tmp_path: Path) -> None:
    clean_scan = tmp_path / "clean-scan.json"
    clean_scan.write_text(json.dumps({"Results": []}), encoding="utf-8")

    result = subprocess.run(
        [
            "python",
            "config/license-policy/check_policy.py",
            str(POLICY),
            str(FIXTURES / "forbidden-license.spdx.json"),
            str(clean_scan),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "forbidden license AGPL-3.0-only" in result.stderr
