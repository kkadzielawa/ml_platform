from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_GITOPS_INTEGRATION") != "1",
    reason="GitOps integration tests require Argo CD and the root Application in the kind cluster",
)


ARGOCD_APP = "ci-fixture"
CI_NAMESPACE = "ml-platform-ci"
CI_ROLE = "ci-sample-pipeline-recorder"
EXPECTED_CI_ROLE_VERBS = ["get", "create", "patch", "update"]


def test_argocd_workloads_oidc_and_rbac_are_configured():
    namespace = argocd_namespace()
    server = kubectl_json("get", "deployment", "argocd-server", "--namespace", namespace, "-o", "json")
    repo = kubectl_json("get", "deployment", "argocd-repo-server", "--namespace", namespace, "-o", "json")
    redis = kubectl_json("get", "deployment", "argocd-redis", "--namespace", namespace, "-o", "json")
    controller = kubectl_json(
        "get",
        "statefulset",
        "argocd-application-controller",
        "--namespace",
        namespace,
        "-o",
        "json",
    )
    cm = kubectl_json("get", "configmap", "argocd-cm", "--namespace", namespace, "-o", "json")
    rbac = kubectl_json("get", "configmap", "argocd-rbac-cm", "--namespace", namespace, "-o", "json")

    assert server["status"].get("availableReplicas") == 1
    assert repo["status"].get("availableReplicas") == 1
    assert redis["status"].get("availableReplicas") == 1
    assert controller["status"].get("readyReplicas") == 1

    oidc_config = cm["data"]["oidc.config"]
    assert "issuer: http://keycloak.ml-platform-system.svc.cluster.local:8080/realms/ml-platform-study" in oidc_config
    assert "clientID: argocd" in oidc_config
    assert "$argocd-oidc-client:clientSecret" in oidc_config

    policy = rbac["data"]["policy.csv"]
    assert "p, role:platform-admin, applications, sync, */*, allow" in policy
    assert "g, viewer, role:readonly" in policy
    assert "g, platform-admins, role:platform-admin" in policy
    assert rbac["data"]["policy.default"] == "role:readonly"


def test_root_application_syncs_from_git_and_self_heals_manual_drift():
    wait_for_application_status(sync="Synced", health="Healthy", timeout_seconds=180)

    original = kubectl_json("get", "role", CI_ROLE, "--namespace", CI_NAMESPACE, "-o", "json")
    assert original["rules"][0]["verbs"] == EXPECTED_CI_ROLE_VERBS

    kubectl(
        "patch",
        "role",
        CI_ROLE,
        "--namespace",
        CI_NAMESPACE,
        "--type=json",
        "--patch=[{\"op\":\"replace\",\"path\":\"/rules/0/verbs\",\"value\":[\"get\"]}]",
    )
    kubectl(
        "annotate",
        "application",
        ARGOCD_APP,
        "--namespace",
        argocd_namespace(),
        "argocd.argoproj.io/refresh=hard",
        "--overwrite",
    )

    saw_out_of_sync = wait_for_application_out_of_sync(timeout_seconds=90)
    wait_for_application_status(sync="Synced", health="Healthy", timeout_seconds=180)

    healed = kubectl_json("get", "role", CI_ROLE, "--namespace", CI_NAMESPACE, "-o", "json")
    assert healed["rules"][0]["verbs"] == EXPECTED_CI_ROLE_VERBS
    assert saw_out_of_sync


def wait_for_application_out_of_sync(*, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app = application()
        if app.get("status", {}).get("sync", {}).get("status") == "OutOfSync":
            return True
        role = kubectl_json("get", "role", CI_ROLE, "--namespace", CI_NAMESPACE, "-o", "json")
        if role["rules"][0]["verbs"] == EXPECTED_CI_ROLE_VERBS:
            return True
        time.sleep(2)
    return False


def wait_for_application_status(*, sync: str, health: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status: dict[str, Any] = {}
    while time.monotonic() < deadline:
        app = application()
        last_status = app.get("status", {})
        if (
            last_status.get("sync", {}).get("status") == sync
            and last_status.get("health", {}).get("status") == health
        ):
            return
        time.sleep(3)
    raise AssertionError(f"Application did not reach sync={sync!r}, health={health!r}; last status={last_status}")


def application() -> dict[str, Any]:
    return kubectl_json("get", "application", ARGOCD_APP, "--namespace", argocd_namespace(), "-o", "json")


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


def argocd_namespace() -> str:
    return os.environ.get("ARGOCD_NAMESPACE", "ml-platform-gitops")
