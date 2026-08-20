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
from typing import Any


REALM = "ml-platform-study"
CLIENT_ID = "argocd"


def main() -> None:
    cluster_name = os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
    keycloak_namespace = os.environ.get("KEYCLOAK_NAMESPACE", "ml-platform-system")
    argocd_namespace = os.environ.get("ARGOCD_NAMESPACE", "ml-platform-gitops")
    keycloak_port = int(os.environ.get("KEYCLOAK_PORT", "18081"))
    argocd_port = int(os.environ.get("ARGOCD_PORT", "18083"))

    admin = read_secret(cluster_name, keycloak_namespace, "keycloak-bootstrap-admin")
    client = read_secret(cluster_name, argocd_namespace, "argocd-oidc-client")

    with port_forward(cluster_name, keycloak_namespace, "svc/keycloak", keycloak_port, 8080):
        token = admin_token(keycloak_port, admin["username"], admin["password"])
        upsert_argocd_client(token, keycloak_port, client["clientSecret"], argocd_port)

    print(json.dumps({"registered": CLIENT_ID, "realm": REALM}, sort_keys=True))


def upsert_argocd_client(token: str, port: int, client_secret: str, argocd_port: int) -> None:
    existing = get_json(
        f"http://127.0.0.1:{port}/admin/realms/{REALM}/clients?clientId={urllib.parse.quote(CLIENT_ID)}",
        token,
    )
    body = {
        "clientId": CLIENT_ID,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "secret": client_secret,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "redirectUris": [
            f"http://127.0.0.1:{argocd_port}/auth/callback",
            f"http://127.0.0.1:{argocd_port}/api/dex/callback",
        ],
        "webOrigins": [f"http://127.0.0.1:{argocd_port}"],
        "attributes": {
            "post.logout.redirect.uris": f"http://127.0.0.1:{argocd_port}/*",
        },
    }
    if existing:
        put_json(f"http://127.0.0.1:{port}/admin/realms/{REALM}/clients/{existing[0]['id']}", token, body)
        return

    post_json(f"http://127.0.0.1:{port}/admin/realms/{REALM}/clients", token, body)


def admin_token(port: int, username: str, password: str) -> str:
    response = post_form(
        f"http://127.0.0.1:{port}/realms/master/protocol/openid-connect/token",
        {
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": username,
            "password": password,
        },
    )
    return str(response["access_token"])


@contextmanager
def port_forward(cluster_name: str, namespace: str, resource: str, local_port: int, remote_port: int):
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{cluster_name}",
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


def wait_for_local_port(port: int) -> None:
    for _ in range(80):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise TimeoutError(f"port-forward did not open 127.0.0.1:{port}")


def read_secret(cluster_name: str, namespace: str, name: str) -> dict[str, str]:
    result = subprocess.run(
        [
            "kubectl",
            "--context",
            f"kind-{cluster_name}",
            "get",
            "secret",
            name,
            "--namespace",
            namespace,
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return {key: base64.b64decode(value).decode("utf-8") for key, value in payload["data"].items()}


def get_json(url: str, token: str) -> Any:
    request = urllib.request.Request(url, headers=auth_headers(token))
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, token: str, body: Any) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20):
        return


def put_json(url: str, token: str, body: Any) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=20):
        return


def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


if __name__ == "__main__":
    main()
