from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SECRET_ROTATION_INTEGRATION") != "1",
    reason="secret rotation tests require OpenBao, External Secrets, Keycloak, and the OIDC echo fixture",
)


def test_oidc_viewer_password_rotates_through_openbao_without_leaking_values():
    before_secret = oidc_test_users_secret()
    old_password = decode_secret_value(before_secret, "viewer-password")
    username = decode_secret_value(before_secret, "viewer-username")

    with keycloak_port_forward():
        old_token = password_grant(username, old_password)
        assert old_token

    result = subprocess.run(
        [
            "python",
            "scripts/security/rotate_oidc_fixture_credential.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    rotation_report = json.loads(result.stdout)
    assert rotation_report["target"] == "secret/oidc-echo-test-users"
    assert rotation_report["consumer"] == f"keycloak realm/ml-platform-study user/{username}"
    assert old_password not in result.stdout
    assert old_password not in result.stderr
    assert_secret_absent_from_tracked_files(old_password)

    after_secret = oidc_test_users_secret()
    new_password = decode_secret_value(after_secret, "viewer-password")
    assert new_password != old_password
    assert new_password not in result.stdout
    assert new_password not in result.stderr
    assert_secret_absent_from_tracked_files(new_password)

    with keycloak_port_forward(), oidc_echo_port_forward():
        assert_password_grant_fails(username, old_password)
        new_token = password_grant(username, new_password)
        viewer_response = http_get("/viewer", token=new_token)

    assert viewer_response.status == 200
    assert viewer_response.json_body["subject"] == username
    assert "viewer" in viewer_response.json_body["roles"]


def password_grant(username: str, password: str) -> str:
    client = oidc_client_secret()
    data = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": decode_secret_value(client, "client-id"),
            "client_secret": decode_secret_value(client, "client-secret"),
            "username": username,
            "password": password,
            "scope": "openid profile",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{keycloak_port()}/realms/ml-platform-study/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload["access_token"])


def assert_password_grant_fails(username: str, password: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as exc:
        password_grant(username, password)
    assert exc.value.code in {400, 401}


@contextmanager
def keycloak_port_forward():
    with port_forward("svc/keycloak", keycloak_namespace(), keycloak_port(), 8080):
        yield


@contextmanager
def oidc_echo_port_forward():
    with port_forward("svc/oidc-echo", oidc_namespace(), oidc_port(), 8080):
        yield


@contextmanager
def port_forward(resource: str, namespace: str, local_port: int, remote_port: int):
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "port-forward",
            "--namespace",
            namespace,
            resource,
            f"{local_port}:{remote_port}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_local_port(local_port)
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def http_get(path: str, *, token: str) -> HttpResponse:
    request = urllib.request.Request(
        f"http://127.0.0.1:{oidc_port()}{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return HttpResponse.from_url_response(response.status, response.headers, response.read())


def wait_for_local_port(port: int) -> None:
    for _ in range(80):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise AssertionError(f"port-forward did not open 127.0.0.1:{port}")


def oidc_client_secret() -> dict[str, Any]:
    return kubectl_json("get", "secret", "oidc-echo-client", "--namespace", oidc_namespace(), "-o", "json")


def oidc_test_users_secret() -> dict[str, Any]:
    return kubectl_json("get", "secret", "oidc-echo-test-users", "--namespace", oidc_namespace(), "-o", "json")


def decode_secret_value(secret: dict[str, Any], key: str) -> str:
    return base64.b64decode(secret["data"][key]).decode("utf-8")


def assert_secret_absent_from_tracked_files(secret_value: str) -> None:
    tracked = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True)
    needle = secret_value.encode("utf-8")
    for relative_path in tracked.stdout.splitlines():
        path = repo_root() / relative_path
        if path.is_file() and path.stat().st_size <= 1_000_000:
            assert needle not in path.read_bytes(), f"secret value appeared in tracked file {relative_path}"


def kubectl_json(*args: str) -> dict[str, Any]:
    result = subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


class HttpResponse:
    def __init__(self, *, status: int, headers: dict[str, str], body: str) -> None:
        self.status = status
        self.headers = headers
        self.body = body
        self.json_body = json.loads(body) if body and body.lstrip().startswith("{") else {}

    @classmethod
    def from_url_response(cls, status: int, headers: Any, payload: bytes) -> "HttpResponse":
        return cls(
            status=status,
            headers={key.lower(): value for key, value in headers.items()},
            body=payload.decode("utf-8", errors="replace"),
        )


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def keycloak_namespace() -> str:
    return os.environ.get("KEYCLOAK_NAMESPACE", "ml-platform-system")


def keycloak_port() -> int:
    return int(os.environ.get("KEYCLOAK_PORT", "18081"))


def oidc_namespace() -> str:
    return os.environ.get("OIDC_ECHO_NAMESPACE", "ml-platform-system")


def oidc_port() -> int:
    return int(os.environ.get("OIDC_ECHO_PORT", "18082"))
