from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
KUSTOMIZE_ENTRIES = [
    REPO_ROOT / "clusters" / "base",
    REPO_ROOT / "clusters" / "base" / "namespaces",
    REPO_ROOT / "clusters" / "dev" / "kind",
    REPO_ROOT / "clusters" / "dev" / "quotas",
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


def test_namespace_and_quota_ownership_do_not_overlap():
    documents = parse_rendered_yaml(render_kustomize(REPO_ROOT / "clusters" / "dev" / "quotas"))
    namespaces = {
        document["metadata"]["name"]: document["metadata"]["labels"]["ml-platform.local/namespace-class"]
        for document in documents
        if document["kind"] == "Namespace"
    }

    assert namespaces == {
        "ml-platform-system": "platform",
        "ml-platform-data": "platform",
        "ml-platform-observability": "platform",
        "ml-platform-project-housing": "project",
    }

    for document in documents:
        if document["kind"] not in {"ResourceQuota", "LimitRange"}:
            continue
        namespace = document["metadata"]["namespace"]
        resource_class = document["metadata"]["labels"]["ml-platform.local/namespace-class"]
        assert namespaces[namespace] == resource_class


def test_project_quota_requires_explicit_compute_resources():
    documents = parse_rendered_yaml(render_kustomize(REPO_ROOT / "clusters" / "dev" / "quotas"))
    project_compute_quota = next(
        document
        for document in documents
        if document["kind"] == "ResourceQuota" and document["metadata"]["namespace"] == "ml-platform-project-housing"
        and document["metadata"]["name"] == "project-housing-quota"
    )
    hard = project_compute_quota["spec"]["hard"]

    assert "requests.cpu" in hard
    assert "requests.memory" in hard
    assert "limits.cpu" in hard
    assert "limits.memory" in hard

    besteffort_quota = next(
        document
        for document in documents
        if document["kind"] == "ResourceQuota" and document["metadata"]["namespace"] == "ml-platform-project-housing"
        and document["metadata"]["name"] == "project-housing-no-besteffort-pods"
    )
    assert besteffort_quota["spec"]["hard"] == {"pods": "0"}
    assert besteffort_quota["spec"]["scopes"] == ["BestEffort"]


def test_project_limitrange_does_not_default_missing_resources():
    documents = parse_rendered_yaml(render_kustomize(REPO_ROOT / "clusters" / "dev" / "quotas"))
    project_limitrange = next(
        document
        for document in documents
        if document["kind"] == "LimitRange" and document["metadata"]["namespace"] == "ml-platform-project-housing"
    )
    project_limits = project_limitrange["spec"]["limits"][0]

    assert "min" in project_limits
    assert "max" not in project_limits
    assert "default" not in project_limits
    assert "defaultRequest" not in project_limits


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
