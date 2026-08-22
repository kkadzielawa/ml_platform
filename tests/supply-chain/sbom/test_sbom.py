from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
IMAGE_NAME = os.environ.get("BUILD_FIXTURE_IMAGE", "ml-platform-study/build-fixture:local")
SBOM_DIR = REPO_ROOT / "config" / "syft"
CYCLONEDX_SBOM = SBOM_DIR / "build-fixture.cdx.json"
SPDX_SBOM = SBOM_DIR / "build-fixture.spdx.json"
IMAGE_DIGEST_FILE = SBOM_DIR / "build-fixture.image-id"
APPLICATION_CONTRACT = SBOM_DIR / "build-fixture-application.json"


def test_sbom_files_exist_and_match_fixture_image_digest() -> None:
    image_id = docker("image", "inspect", IMAGE_NAME, "--format", "{{.Id}}").stdout.strip()
    recorded_image_id = IMAGE_DIGEST_FILE.read_text(encoding="utf-8").strip()

    assert recorded_image_id == image_id

    for path in [CYCLONEDX_SBOM, SPDX_SBOM]:
        assert path.exists()
        assert image_id in path.read_text(encoding="utf-8")


def test_cyclonedx_sbom_contains_application_and_os_packages() -> None:
    sbom = read_json(CYCLONEDX_SBOM)
    components = sbom["components"]
    application = read_json(APPLICATION_CONTRACT)

    assert sbom["bomFormat"] == "CycloneDX"
    assert any(component.get("name") == application["application_name"] for component in components)
    assert any(component.get("type") == "operating-system" for component in components)
    assert any(component.get("type") == "library" for component in components)


def test_spdx_sbom_contains_application_and_os_packages() -> None:
    sbom = read_json(SPDX_SBOM)
    packages = sbom["packages"]
    application = read_json(APPLICATION_CONTRACT)

    assert sbom["spdxVersion"].startswith("SPDX-")
    assert any(package.get("name") == application["application_name"] for package in packages)
    assert any("python" in package.get("name", "").lower() for package in packages)
    package_names = {package.get("name") for package in packages}
    assert {"apt", "base-files", "dpkg"}.issubset(package_names)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
