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
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_OIDC_INTEGRATION") != "1",
    reason="OIDC integration tests require a running kind cluster, Keycloak, and OIDC echo fixture",
)


def test_oidc_echo_resources_are_ready():
    deployment = kubectl_json("get", "deployment", "oidc-echo", "--namespace", oidc_namespace(), "-o", "json")
    route = kubectl_json("get", "httproute", "oidc-echo", "--namespace", oidc_namespace(), "-o", "json")
    job = kubectl_json("get", "job", "oidc-echo-client-registration", "--namespace", oidc_namespace(), "-o", "json")

    assert deployment["status"].get("availableReplicas") == 1
    assert_condition(route["status"]["parents"][0]["conditions"], "Accepted", "True")
    assert job["status"].get("succeeded") == 1


def test_unauthenticated_viewer_path_redirects_to_keycloak():
    with oidc_echo_port_forward():
        response = http_get("/viewer", allow_http_error=True)

    assert response.status == 302
    assert "/realms/ml-platform-study/protocol/openid-connect/auth" in response.headers["location"]
    assert "client_id=oidc-echo" in response.headers["location"]


def test_viewer_token_can_access_viewer_path_but_not_admin_path():
    with keycloak_port_forward(), oidc_echo_port_forward():
        token = password_grant("viewer")
        viewer = http_get("/viewer", token=token)
        admin = http_get("/admin", token=token, allow_http_error=True)

    assert viewer.status == 200
    assert viewer.json_body["subject"] == viewer_username()
    assert "viewer" in viewer.json_body["roles"]
    assert admin.status == 403
    assert admin.json_body["required_role"] == "admin"


def test_admin_token_can_access_admin_path():
    with keycloak_port_forward(), oidc_echo_port_forward():
        token = password_grant("admin")
        response = http_get("/admin", token=token)

    assert response.status == 200
    assert response.json_body["subject"] == admin_username()
    assert "admin" in response.json_body["roles"]


def password_grant(user_kind: str) -> str:
    client = oidc_client_secret()
    users = oidc_test_users_secret()
    if user_kind == "viewer":
        username = decode_secret_value(users, "viewer-username")
        password = decode_secret_value(users, "viewer-password")
    elif user_kind == "admin":
        username = decode_secret_value(users, "admin-username")
        password = decode_secret_value(users, "admin-password")
    else:
        raise ValueError(f"unknown user kind: {user_kind}")

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
    return payload["access_token"]


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


def http_get(path: str, *, token: str | None = None, allow_http_error: bool = False) -> HttpResponse:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"http://127.0.0.1:{oidc_port()}{path}",
        headers=headers,
        method="GET",
    )

    try:
        opener = urllib.request.build_opener(NoRedirectHandler)
        with opener.open(request, timeout=20) as response:
            return HttpResponse.from_url_response(response.status, response.headers, response.read())
    except urllib.error.HTTPError as error:
        if not allow_http_error:
            raise
        return HttpResponse.from_url_response(error.code, error.headers, error.read())


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


def assert_condition(conditions: list[dict[str, Any]], condition_type: str, status: str) -> None:
    condition = next((item for item in conditions if item.get("type") == condition_type), None)
    assert condition is not None, f"missing condition {condition_type!r}"
    assert condition["status"] == status, condition


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


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def keycloak_namespace() -> str:
    return os.environ.get("KEYCLOAK_NAMESPACE", "ml-platform-system")


def keycloak_port() -> int:
    return int(os.environ.get("KEYCLOAK_PORT", "18081"))


def oidc_namespace() -> str:
    return os.environ.get("OIDC_ECHO_NAMESPACE", "ml-platform-system")


def oidc_port() -> int:
    return int(os.environ.get("OIDC_ECHO_PORT", "18082"))


def viewer_username() -> str:
    return decode_secret_value(oidc_test_users_secret(), "viewer-username")


def admin_username() -> str:
    return decode_secret_value(oidc_test_users_secret(), "admin-username")
