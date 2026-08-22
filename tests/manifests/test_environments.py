from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_OVERLAYS = {
    "dev": {
        "path": REPO_ROOT / "clusters" / "dev" / "environment",
        "namespace": "ml-platform-dev-housing",
        "replicas": 1,
        "storage": "1Gi",
    },
    "stage": {
        "path": REPO_ROOT / "clusters" / "stage" / "environment",
        "namespace": "ml-platform-stage-housing",
        "replicas": 2,
        "storage": "5Gi",
    },
    "prod-simulation": {
        "path": REPO_ROOT / "clusters" / "prod" / "simulation",
        "namespace": "ml-platform-prod-housing",
        "replicas": 3,
        "storage": "20Gi",
    },
}


@pytest.mark.parametrize(("environment", "expected"), ENVIRONMENT_OVERLAYS.items())
def test_environment_overlay_renders_with_expected_shape(environment: str, expected: dict[str, Any]) -> None:
    documents = parse_rendered_yaml(render_kustomize(expected["path"]))

    assert documents
    assert_no_secrets(documents)
    assert_no_mutable_images(documents)
    assert_namespaces_belong_to_environment(documents, expected["namespace"], environment)

    deployment = find_one(documents, kind="Deployment", name="housing-price-api")
    assert deployment["metadata"]["namespace"] == expected["namespace"]
    assert deployment["spec"]["replicas"] == expected["replicas"]
    assert deployment["spec"]["template"]["metadata"]["labels"]["ml-platform.local/environment"] == environment

    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert "requests" in container["resources"]
    assert "limits" in container["resources"]

    pvc = find_one(documents, kind="PersistentVolumeClaim", name="housing-feature-cache")
    assert pvc["metadata"]["namespace"] == expected["namespace"]
    assert pvc["spec"]["resources"]["requests"]["storage"] == expected["storage"]


def test_environment_guard_rejects_mutable_image_tag() -> None:
    bad_manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "bad-image", "namespace": "ml-platform-dev-housing"},
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "api",
                            "image": "ghcr.io/kkadzielawa/ml-platform-study/housing-price-api:dev",
                        }
                    ]
                }
            }
        },
    }

    with pytest.raises(AssertionError, match="mutable"):
        assert_no_mutable_images([bad_manifest])


def test_environment_guard_rejects_cross_environment_namespace() -> None:
    bad_manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "wrong-namespace", "namespace": "ml-platform-stage-housing"},
    }

    with pytest.raises(AssertionError, match="cross-environment"):
        assert_namespaces_belong_to_environment([bad_manifest], "ml-platform-dev-housing", "dev")


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


def assert_no_secrets(documents: list[dict[str, Any]]) -> None:
    secret_kinds = {"Secret", "ExternalSecret"}
    for document in documents:
        assert document["kind"] not in secret_kinds


def assert_namespaces_belong_to_environment(
    documents: list[dict[str, Any]],
    expected_namespace: str,
    expected_environment: str,
) -> None:
    for document in documents:
        metadata = document["metadata"]
        if document["kind"] == "Namespace":
            assert metadata["name"] == expected_namespace, "cross-environment namespace rendered"
            assert metadata["labels"]["ml-platform.local/environment"] == expected_environment
            continue
        namespace = metadata.get("namespace")
        if namespace is not None:
            assert namespace == expected_namespace, "cross-environment namespace rendered"


def assert_no_mutable_images(documents: list[dict[str, Any]]) -> None:
    for document in documents:
        for image in find_container_images(document):
            assert image != "latest"
            assert ":latest" not in image
            assert "@sha256:" in image, f"image reference is mutable: {image}"


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


def find_one(documents: list[dict[str, Any]], *, kind: str, name: str) -> dict[str, Any]:
    matches = [
        document
        for document in documents
        if document["kind"] == kind and document["metadata"]["name"] == name
    ]
    assert len(matches) == 1
    return matches[0]
