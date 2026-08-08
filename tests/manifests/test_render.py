from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
KUSTOMIZE_ENTRIES = [
    REPO_ROOT / "clusters" / "base",
    REPO_ROOT / "clusters" / "dev" / "kind",
]
BASE_FORBIDDEN_STRINGS = [
    "ml-platform.local/environment",
    "ml-platform.local/cluster-route",
    "127.0.0.1",
    "localhost",
    "ml-platform-study-dev",
    "values-dev",
    "values-prod",
]


def test_current_kustomize_entries_render_and_parse():
    for entry in KUSTOMIZE_ENTRIES:
        rendered = render_kustomize(entry)
        documents = parse_rendered_yaml(rendered)
        assert isinstance(documents, list)
        assert_no_mutable_images(documents)


def test_base_does_not_contain_environment_specific_values():
    base_dir = REPO_ROOT / "clusters" / "base"
    for path in base_dir.rglob("*.yaml"):
        content = path.read_text(encoding="utf-8")
        for forbidden in BASE_FORBIDDEN_STRINGS:
            assert forbidden not in content, f"{path} contains environment-specific value {forbidden!r}"


def render_kustomize(path: Path) -> str:
    result = subprocess.run(
        ["kubectl", "kustomize", str(path)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def parse_rendered_yaml(rendered: str) -> list[dict[str, Any]]:
    if not rendered.strip():
        return []
    documents = [document for document in yaml.safe_load_all(rendered) if document is not None]
    for document in documents:
        assert isinstance(document, dict)
        assert "apiVersion" in document
        assert "kind" in document
        assert "metadata" in document
    return documents


def assert_no_mutable_images(documents: list[dict[str, Any]]) -> None:
    for document in documents:
        for image in find_container_images(document):
            assert image != "latest"
            assert ":latest" not in image
            assert has_immutable_image_reference(image), f"image reference is mutable: {image}"


def find_container_images(value: Any) -> list[str]:
    images = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"containers", "initContainers"} and isinstance(item, list):
                for container in item:
                    if isinstance(container, dict) and "image" in container:
                        images.append(container["image"])
            images.extend(find_container_images(item))
    elif isinstance(value, list):
        for item in value:
            images.extend(find_container_images(item))
    return images


def has_immutable_image_reference(image: str) -> bool:
    return "@sha256:" in image
