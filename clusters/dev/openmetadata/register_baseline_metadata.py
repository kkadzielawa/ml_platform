from __future__ import annotations

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


REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = REPO_ROOT / "clusters/dev/openmetadata/catalog-seed-configmap.yaml"


def main() -> None:
    with local_openmetadata_session() as session:
        seed = load_seed()
        responses = register_seed(session.base_url, session.token, seed)
    print(json.dumps({"registered": sorted(responses)}, sort_keys=True))


def load_seed() -> dict[str, Any]:
    content = SEED_PATH.read_text(encoding="utf-8")
    marker = "  baseline-catalog.json: |\n"
    payload = content.split(marker, 1)[1]
    lines = [line[4:] if line.startswith("    ") else line for line in payload.splitlines()]
    return json.loads("\n".join(lines))


def register_seed(base_url: str, token: str, seed: dict[str, Any]) -> dict[str, Any]:
    service = seed["service"]
    database = seed["database"]
    schema = seed["schema"]
    table = seed["table"]
    owner = ensure_team(base_url, token, seed["owner"])

    responses = {
        "team": owner,
        "service": put_json(
            f"{base_url}/v1/services/databaseServices",
            token,
            {
                "name": service["name"],
                "serviceType": service["serviceType"],
                "description": service["description"],
                "connection": {"config": {"type": service["serviceType"]}},
            },
        ),
        "database": put_json(
            f"{base_url}/v1/databases",
            token,
            {
                "name": database["name"],
                "service": database["service"],
                "description": database["description"],
                "retentionPeriod": "P365D",
            },
        ),
        "schema": put_json(
            f"{base_url}/v1/databaseSchemas",
            token,
            {
                "name": schema["name"],
                "database": schema["database"],
                "description": schema["description"],
                "retentionPeriod": "P365D",
            },
        ),
        "table": put_json(
            f"{base_url}/v1/tables",
            token,
            table,
        ),
    }
    responses["tableOwner"] = patch_table_owner(base_url, token, table, owner)
    return responses


def ensure_team(base_url: str, token: str, owner: dict[str, str]) -> dict[str, Any]:
    name = owner["name"]
    try:
        return get_json(f"{base_url}/v1/teams/name/{urllib.parse.quote(name, safe='')}", token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    return post_json(
        f"{base_url}/v1/teams",
        token,
        {
            "name": name,
            "displayName": name,
            "teamType": "Group",
            "description": "Study platform learners that own exploratory ML platform datasets.",
        },
    )


def get_table_by_name(base_url: str, token: str, fqn: str, *, fields: str | None = None) -> dict[str, Any]:
    query = f"?fields={urllib.parse.quote(fields, safe=',')}" if fields else ""
    return get_json(f"{base_url}/v1/tables/name/{urllib.parse.quote(fqn, safe='')}{query}", token)


def patch_table_owner(base_url: str, token: str, table: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
    fqn = f"{table['databaseSchema']}.{table['name']}"
    current_table = get_table_by_name(base_url, token, fqn, fields="owners")
    operation = "replace" if "owners" in current_table else "add"
    return patch_json(
        f"{base_url}/v1/tables/name/{urllib.parse.quote(fqn, safe='')}?changeSource=Automated",
        token,
        [
            {
                "op": operation,
                "path": "/owners",
                "value": [
                    {
                        "id": owner["id"],
                        "type": "team",
                        "name": owner["name"],
                    }
                ],
            }
        ],
    )


class OpenMetadataSession:
    def __init__(self, *, base_url: str, token: str) -> None:
        self.base_url = base_url
        self.token = token


@contextmanager
def local_openmetadata_session():
    token = os.environ.get("OPENMETADATA_JWT_TOKEN")
    base_url = os.environ.get("OPENMETADATA_URL")
    if token and base_url:
        yield OpenMetadataSession(base_url=base_url.rstrip("/"), token=token)
        return

    cluster_name = os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
    keycloak_namespace = os.environ.get("KEYCLOAK_NAMESPACE", "ml-platform-system")
    openmetadata_namespace = os.environ.get("OPENMETADATA_NAMESPACE", "ml-platform-data")
    keycloak_port = int(os.environ.get("KEYCLOAK_PORT", "18081"))
    openmetadata_port = int(os.environ.get("OPENMETADATA_PORT", "8585"))

    with (
        port_forward(cluster_name, keycloak_namespace, "svc/keycloak", keycloak_port, 8080),
        port_forward(cluster_name, openmetadata_namespace, "svc/openmetadata", openmetadata_port, 8585),
    ):
        yield OpenMetadataSession(
            base_url=f"http://127.0.0.1:{openmetadata_port}/api",
            token=keycloak_token(cluster_name, openmetadata_namespace, keycloak_port),
        )


def keycloak_token(cluster_name: str, openmetadata_namespace: str, keycloak_port: int) -> str:
    client = read_secret(cluster_name, openmetadata_namespace, "openmetadata-oidc-client")
    response = post_form(
        f"http://127.0.0.1:{keycloak_port}/realms/ml-platform-study/protocol/openid-connect/token",
        {
            "grant_type": "password",
            "client_id": "openmetadata",
            "client_secret": client["clientSecret"],
            "username": os.environ.get("OPENMETADATA_ADMIN_USERNAME", "admin"),
            "password": os.environ["OPENMETADATA_ADMIN_PASSWORD"],
        },
    )
    return str(response["access_token"])


def put_json(url: str, token: str, body: Any) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenMetadata PUT {url} failed with HTTP {exc.code}: {detail}") from exc
    assert isinstance(parsed, dict)
    return parsed


def post_json(url: str, token: str, body: Any) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenMetadata POST {url} failed with HTTP {exc.code}: {detail}") from exc
    assert isinstance(parsed, dict)
    return parsed


def patch_json(url: str, token: str, body: Any) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json-patch+json"},
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenMetadata PATCH {url} failed with HTTP {exc.code}: {detail}") from exc
    assert isinstance(parsed, dict)
    return parsed


def get_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=auth_headers(token))
    with urllib.request.urlopen(request, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    assert isinstance(parsed, dict)
    return parsed


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
    import base64

    return {key: base64.b64decode(value).decode("utf-8") for key, value in payload["data"].items()}


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
