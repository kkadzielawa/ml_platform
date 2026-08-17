from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import socket
import subprocess
import sys
import textwrap
import time
import urllib.parse
import urllib.request
from contextlib import contextmanager
from typing import Any


OPENBAO_POD = "openbao-0"
OPENBAO_BOOTSTRAP_SECRET = "openbao-bootstrap"
OPENBAO_POLICY = "external-secrets-oidc-echo-test-users"
OPENBAO_TOKEN_KEY = "openbao-token"
OPENBAO_SECRET_STORE = "openbao-oidc-echo"
OPENBAO_EXTERNAL_SECRET = "oidc-echo-test-users"
OPENBAO_REMOTE_KEY = "projects/identity/oidc-echo/test-users"
OIDC_CLIENT_SECRET = "oidc-echo-client"
OIDC_SECRET = "oidc-echo-test-users"
KEYCLOAK_BOOTSTRAP_SECRET = "keycloak-bootstrap-admin"
KEYCLOAK_REALM = "ml-platform-study"


def main() -> int:
    args = parse_args()
    cluster_name = os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
    openbao_namespace = os.environ.get("OPENBAO_NAMESPACE", "ml-platform-system")
    oidc_namespace = os.environ.get("OIDC_ECHO_NAMESPACE", "ml-platform-system")

    existing = read_secret(cluster_name, oidc_namespace, OIDC_SECRET)
    old_password = existing["viewer-password"]
    new_password = generate_new_password(old_password)

    root_token = read_secret(cluster_name, openbao_namespace, OPENBAO_BOOTSTRAP_SECRET)["root-token"]
    write_openbao_secret(cluster_name, openbao_namespace, root_token, {**existing, "viewer-password": new_password})
    reader_token = create_scoped_reader_token(cluster_name, openbao_namespace, root_token)
    apply_external_secret_route(cluster_name, oidc_namespace, reader_token)
    wait_for_synced_password(cluster_name, oidc_namespace, new_password)
    update_keycloak_user_password(cluster_name, oidc_namespace, existing["viewer-username"], new_password)

    print(
        json.dumps(
            {
                "rotated": "oidc-echo viewer test password",
                "namespace": oidc_namespace,
                "source": f"openbao:kv/{OPENBAO_REMOTE_KEY}",
                "target": f"secret/{OIDC_SECRET}",
                "consumer": f"keycloak realm/{KEYCLOAK_REALM} user/{existing['viewer-username']}",
                "dry_run": args.dry_run,
            },
            sort_keys=True,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rotate the OIDC echo viewer test password through OpenBao and External Secrets."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reserved for documentation parity; this issue intentionally performs a real rotation.",
    )
    args = parser.parse_args()
    if args.dry_run:
        raise SystemExit("--dry-run is not implemented because the integration test must verify a real rotation")
    return args


def generate_new_password(old_password: str) -> str:
    for _ in range(5):
        candidate = secrets.token_urlsafe(36)
        if candidate != old_password:
            return candidate
    raise RuntimeError("failed to generate a different password")


def write_openbao_secret(
    cluster_name: str,
    openbao_namespace: str,
    root_token: str,
    values: dict[str, str],
) -> None:
    script = textwrap.dedent(
        f"""
        set -eu
        read -r root_token
        read -r viewer_username
        read -r viewer_password
        read -r admin_username
        read -r admin_password
        export BAO_TOKEN="$root_token"
        bao secrets enable -path=kv kv-v2 >/dev/null 2>&1 || true
        bao kv put kv/{OPENBAO_REMOTE_KEY} \\
          viewer-username="$viewer_username" \\
          viewer-password="$viewer_password" \\
          admin-username="$admin_username" \\
          admin-password="$admin_password" >/dev/null
        """
    ).strip()
    payload = "\n".join(
        [
            root_token,
            values["viewer-username"],
            values["viewer-password"],
            values["admin-username"],
            values["admin-password"],
            "",
        ]
    )
    kubectl(
        cluster_name,
        "exec",
        "--namespace",
        openbao_namespace,
        "-i",
        OPENBAO_POD,
        "--",
        "sh",
        "-ec",
        script,
        input_text=payload,
    )


def create_scoped_reader_token(cluster_name: str, openbao_namespace: str, root_token: str) -> str:
    script = textwrap.dedent(
        f"""
        set -eu
        read -r root_token
        export BAO_TOKEN="$root_token"
        cat >/tmp/{OPENBAO_POLICY}.hcl <<'EOF'
        path "kv/data/{OPENBAO_REMOTE_KEY}" {{
          capabilities = ["read"]
        }}
        path "kv/metadata/{OPENBAO_REMOTE_KEY}" {{
          capabilities = ["read"]
        }}
        EOF
        bao policy write {OPENBAO_POLICY} /tmp/{OPENBAO_POLICY}.hcl >/dev/null
        bao token create -policy={OPENBAO_POLICY} -period=24h -format=json
        """
    ).strip()
    result = kubectl(
        cluster_name,
        "exec",
        "--namespace",
        openbao_namespace,
        "-i",
        OPENBAO_POD,
        "--",
        "sh",
        "-ec",
        script,
        input_text=f"{root_token}\n",
    )
    payload = json.loads(result.stdout)
    return str(payload["auth"]["client_token"])


def apply_external_secret_route(cluster_name: str, oidc_namespace: str, reader_token: str) -> None:
    patch_secret_data(cluster_name, oidc_namespace, OIDC_CLIENT_SECRET, OPENBAO_TOKEN_KEY, reader_token)
    manifest = textwrap.dedent(
        f"""
        apiVersion: external-secrets.io/v1
        kind: SecretStore
        metadata:
          name: {OPENBAO_SECRET_STORE}
          namespace: {oidc_namespace}
          labels:
            app.kubernetes.io/name: oidc-echo
            app.kubernetes.io/component: secret-rotation
        spec:
          provider:
            vault:
              server: http://openbao.ml-platform-system.svc.cluster.local:8200
              path: kv
              version: v2
              auth:
                tokenSecretRef:
                  name: {OIDC_CLIENT_SECRET}
                  key: {OPENBAO_TOKEN_KEY}
        ---
        apiVersion: external-secrets.io/v1
        kind: ExternalSecret
        metadata:
          name: {OPENBAO_EXTERNAL_SECRET}
          namespace: {oidc_namespace}
          labels:
            app.kubernetes.io/name: oidc-echo
            app.kubernetes.io/component: secret-rotation
          annotations:
            force-sync: "{int(time.time())}"
        spec:
          refreshInterval: 5s
          secretStoreRef:
            kind: SecretStore
            name: {OPENBAO_SECRET_STORE}
          target:
            name: {OIDC_SECRET}
            creationPolicy: Merge
          data:
            - secretKey: viewer-username
              remoteRef:
                key: {OPENBAO_REMOTE_KEY}
                property: viewer-username
            - secretKey: viewer-password
              remoteRef:
                key: {OPENBAO_REMOTE_KEY}
                property: viewer-password
            - secretKey: admin-username
              remoteRef:
                key: {OPENBAO_REMOTE_KEY}
                property: admin-username
            - secretKey: admin-password
              remoteRef:
                key: {OPENBAO_REMOTE_KEY}
                property: admin-password
        """
    ).strip()
    kubectl(cluster_name, "apply", "-f", "-", input_text=f"{manifest}\n")
    kubectl(
        cluster_name,
        "wait",
        "--timeout=2m",
        "--namespace",
        oidc_namespace,
        f"secretstore/{OPENBAO_SECRET_STORE}",
        "--for=condition=Ready",
    )
    kubectl(
        cluster_name,
        "wait",
        "--timeout=2m",
        "--namespace",
        oidc_namespace,
        f"externalsecret/{OPENBAO_EXTERNAL_SECRET}",
        "--for=condition=Ready",
    )


def patch_secret_data(cluster_name: str, namespace: str, name: str, key: str, value: str) -> None:
    patch = json.dumps({"data": {key: base64.b64encode(value.encode("utf-8")).decode("ascii")}})
    kubectl(cluster_name, "patch", "secret", name, "--namespace", namespace, "--type=merge", "--patch-file", "/dev/stdin", input_text=patch)


def wait_for_synced_password(cluster_name: str, oidc_namespace: str, expected_password: str) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        observed = read_secret(cluster_name, oidc_namespace, OIDC_SECRET).get("viewer-password")
        if observed == expected_password:
            return
        time.sleep(2)
    raise TimeoutError(f"secret/{OIDC_SECRET} did not receive the rotated viewer password")


def update_keycloak_user_password(cluster_name: str, keycloak_namespace: str, username: str, password: str) -> None:
    admin = read_secret(cluster_name, keycloak_namespace, KEYCLOAK_BOOTSTRAP_SECRET)
    keycloak_port = int(os.environ.get("KEYCLOAK_PORT", "18081"))
    with port_forward(cluster_name, keycloak_namespace, "svc/keycloak", keycloak_port, 8080):
        token = keycloak_admin_token(keycloak_port, admin["username"], admin["password"])
        user_id = keycloak_user_id(keycloak_port, token, username)
        put_json(
            f"http://127.0.0.1:{keycloak_port}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/reset-password",
            token,
            {
                "type": "password",
                "value": password,
                "temporary": False,
            },
        )


def keycloak_admin_token(port: int, username: str, password: str) -> str:
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


def keycloak_user_id(port: int, token: str, username: str) -> str:
    users = get_json(
        f"http://127.0.0.1:{port}/admin/realms/{KEYCLOAK_REALM}/users?username={urllib.parse.quote(username)}&exact=true",
        token,
    )
    if not users:
        raise RuntimeError(f"Keycloak user {username!r} does not exist")
    return str(users[0]["id"])


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


def get_json(url: str, token: str) -> Any:
    request = urllib.request.Request(url, headers=auth_headers(token))
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


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


def read_secret(cluster_name: str, namespace: str, name: str) -> dict[str, str]:
    payload = kubectl_json(cluster_name, "get", "secret", name, "--namespace", namespace, "-o", "json")
    return {key: base64.b64decode(value).decode("utf-8") for key, value in payload["data"].items()}


def kubectl_json(cluster_name: str, *args: str) -> dict[str, Any]:
    result = kubectl(cluster_name, *args)
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def kubectl(
    cluster_name: str,
    *args: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", f"kind-{cluster_name}", *args],
        input=input_text,
        check=True,
        capture_output=True,
        text=True,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        raise
