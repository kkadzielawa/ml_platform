from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_KEYCLOAK_INTEGRATION") != "1",
    reason="Keycloak integration tests require a running kind cluster and Keycloak deployment",
)


REALM = "ml-platform-study"
EXPECTED_ROLES = {"admin", "learner", "viewer", "service"}


def test_keycloak_manifests_do_not_embed_plaintext_credentials():
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in identity_manifest_paths())

    assert "KC_BOOTSTRAP_ADMIN_PASSWORD" in rendered
    assert "local-dev-keycloak" not in rendered
    assert "keycloak-password" not in rendered
    assert "--from-literal=password" not in rendered

    cluster = yaml.safe_load((repo_root() / "clusters/dev/identity/keycloak-postgres.yaml").read_text(encoding="utf-8"))
    assert cluster["spec"]["bootstrap"]["initdb"]["secret"]["name"] == "keycloak-postgres-app"


def test_study_realm_imported_with_required_roles_and_groups():
    with keycloak_port_forward():
        token = admin_token()
        realm = keycloak_json(f"/admin/realms/{REALM}", token=token)
        roles = keycloak_json(f"/admin/realms/{REALM}/roles", token=token)
        groups = keycloak_json(f"/admin/realms/{REALM}/groups", token=token)

    assert realm["realm"] == REALM
    assert realm["enabled"] is True
    role_names = {item["name"] for item in roles}
    assert EXPECTED_ROLES <= role_names

    group_names = {item["name"] for item in groups}
    assert {"platform-admins", "platform-learners", "platform-viewers", "platform-services"} <= group_names


def test_realm_import_survives_keycloak_restart():
    original_uid = deployment_uid()
    kubectl("rollout", "restart", "deployment/keycloak", "--namespace", namespace())
    kubectl("rollout", "status", "deployment/keycloak", "--namespace", namespace(), "--timeout=5m")
    wait_for_deployment_uid_change(original_uid)

    with keycloak_port_forward():
        token = admin_token()
        roles = keycloak_json(f"/admin/realms/{REALM}/roles", token=token)

    assert EXPECTED_ROLES <= {item["name"] for item in roles}


def test_bootstrap_admin_secret_is_generated_or_supplied_outside_git():
    secret = kubectl_json("get", "secret", "keycloak-bootstrap-admin", "--namespace", namespace(), "-o", "json")
    password = decode_secret_value(secret, "password")

    assert len(password) >= 32
    assert password not in "\n".join(path.read_text(encoding="utf-8") for path in identity_manifest_paths())


@contextmanager
def keycloak_port_forward():
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "port-forward",
            "--namespace",
            namespace(),
            "svc/keycloak",
            f"{local_port()}:8080",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_local_port()
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def admin_token() -> str:
    secret = kubectl_json("get", "secret", "keycloak-bootstrap-admin", "--namespace", namespace(), "-o", "json")
    username = decode_secret_value(secret, "username")
    password = decode_secret_value(secret, "password")
    data = urllib.parse.urlencode(
        {
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": username,
            "password": password,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url()}/realms/master/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["access_token"]


def keycloak_json(path: str, *, token: str) -> Any:
    request = urllib.request.Request(
        f"{base_url()}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_local_port() -> None:
    for _ in range(80):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", local_port())) == 0:
                return
        time.sleep(0.5)
    raise AssertionError(f"Keycloak port-forward did not open 127.0.0.1:{local_port()}")


def wait_for_deployment_uid_change(original_uid: str) -> None:
    for _ in range(60):
        if deployment_uid() != original_uid:
            return
        time.sleep(2)
    raise AssertionError("Keycloak deployment did not restart within timeout")


def deployment_uid() -> str:
    deployment = kubectl_json("get", "deployment", "keycloak", "--namespace", namespace(), "-o", "json")
    return deployment["metadata"]["annotations"].get("deployment.kubernetes.io/revision", "")


def decode_secret_value(secret: dict[str, Any], key: str) -> str:
    return base64.b64decode(secret["data"][key]).decode("utf-8")


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


def identity_manifest_paths() -> list[Path]:
    return sorted((repo_root() / "clusters/dev/identity").glob("*.yaml"))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def base_url() -> str:
    return f"http://127.0.0.1:{local_port()}"


def local_port() -> int:
    return int(os.environ.get("KEYCLOAK_PORT", "18081"))


def namespace() -> str:
    return os.environ.get("KEYCLOAK_NAMESPACE", "ml-platform-system")


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
