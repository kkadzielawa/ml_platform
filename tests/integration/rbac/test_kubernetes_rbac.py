from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_RBAC_INTEGRATION") != "1",
    reason="RBAC integration tests require a running kind cluster with RBAC manifests applied",
)


PROJECT_NAMESPACE = "ml-platform-project-housing"
OTHER_PROJECT_NAMESPACE = "ml-platform-project-fraud"
PLATFORM_SYSTEM_NAMESPACE = "ml-platform-system"
PLATFORM_DATA_NAMESPACE = "ml-platform-data"


def test_required_roles_and_bindings_exist():
    project_viewer = kubectl_json("get", "role", "project-viewer", "--namespace", PROJECT_NAMESPACE, "-o", "json")
    project_editor = kubectl_json("get", "role", "project-editor", "--namespace", PROJECT_NAMESPACE, "-o", "json")
    platform_observer = kubectl_json("get", "role", "platform-observer", "--namespace", PLATFORM_SYSTEM_NAMESPACE, "-o", "json")

    assert project_viewer["metadata"]["name"] == "project-viewer"
    assert project_editor["metadata"]["name"] == "project-editor"
    assert platform_observer["metadata"]["name"] == "platform-observer"

    viewer_binding = kubectl_json(
        "get",
        "rolebinding",
        "platform-viewers-project-viewer",
        "--namespace",
        PROJECT_NAMESPACE,
        "-o",
        "json",
    )
    editor_binding = kubectl_json(
        "get",
        "rolebinding",
        "platform-learners-project-editor",
        "--namespace",
        PROJECT_NAMESPACE,
        "-o",
        "json",
    )

    assert group_subject_names(viewer_binding) == {"platform-viewers"}
    assert group_subject_names(editor_binding) == {"platform-learners"}


def test_project_viewer_can_read_project_but_cannot_mutate_or_read_secrets():
    viewer = Subject(username="viewer@example.local", groups=("platform-viewers",))

    assert can_i(viewer, "get", "pods", namespace=PROJECT_NAMESPACE)
    assert can_i(viewer, "list", "deployments.apps", namespace=PROJECT_NAMESPACE)
    assert can_i(viewer, "get", "pods/log", namespace=PROJECT_NAMESPACE)

    assert not can_i(viewer, "create", "deployments.apps", namespace=PROJECT_NAMESPACE)
    assert not can_i(viewer, "patch", "configmaps", namespace=PROJECT_NAMESPACE)
    assert not can_i(viewer, "delete", "services", namespace=PROJECT_NAMESPACE)
    assert not can_i(viewer, "get", "secrets", namespace=PROJECT_NAMESPACE)
    assert not can_i(viewer, "list", "secrets", namespace=PROJECT_NAMESPACE)


def test_project_editor_can_edit_own_project_but_not_other_namespaces_or_secrets():
    editor = Subject(username="learner@example.local", groups=("platform-learners",))

    assert can_i(editor, "create", "deployments.apps", namespace=PROJECT_NAMESPACE)
    assert can_i(editor, "patch", "configmaps", namespace=PROJECT_NAMESPACE)
    assert can_i(editor, "delete", "jobs.batch", namespace=PROJECT_NAMESPACE)

    assert not can_i(editor, "get", "pods", namespace=OTHER_PROJECT_NAMESPACE)
    assert not can_i(editor, "create", "deployments.apps", namespace=OTHER_PROJECT_NAMESPACE)
    assert not can_i(editor, "get", "pods", namespace=PLATFORM_DATA_NAMESPACE)
    assert not can_i(editor, "get", "secrets", namespace=PROJECT_NAMESPACE)


def test_platform_observer_can_read_platform_namespaces_without_mutation_or_secret_access():
    observer = Subject(username="admin@example.local", groups=("platform-admins",))

    assert can_i(observer, "get", "pods", namespace=PLATFORM_SYSTEM_NAMESPACE)
    assert can_i(observer, "list", "services", namespace=PLATFORM_DATA_NAMESPACE)
    assert can_i(observer, "get", "clusters.postgresql.cnpg.io", namespace=PLATFORM_DATA_NAMESPACE)

    assert not can_i(observer, "create", "deployments.apps", namespace=PLATFORM_SYSTEM_NAMESPACE)
    assert not can_i(observer, "delete", "configmaps", namespace=PLATFORM_DATA_NAMESPACE)
    assert not can_i(observer, "get", "secrets", namespace=PLATFORM_SYSTEM_NAMESPACE)


def can_i(subject: Subject, verb: str, resource: str, *, namespace: str) -> bool:
    result = subprocess.run(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "auth",
            "can-i",
            verb,
            resource,
            "--namespace",
            namespace,
            "--as",
            subject.username,
            *[item for group in subject.groups for item in ("--as-group", group)],
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode in {0, 1}, result.stderr
    answer = result.stdout.strip()
    assert answer in {"yes", "no"}, result.stdout
    return answer == "yes"


def group_subject_names(binding: dict[str, Any]) -> set[str]:
    return {
        subject["name"]
        for subject in binding["subjects"]
        if subject.get("kind") == "Group" and subject.get("apiGroup") == "rbac.authorization.k8s.io"
    }


def kubectl_json(*args: str) -> dict[str, Any]:
    result = kubectl(*args)
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def kubectl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


@dataclass(frozen=True)
class Subject:
    username: str
    groups: tuple[str, ...]
