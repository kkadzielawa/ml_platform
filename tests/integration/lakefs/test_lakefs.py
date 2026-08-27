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
import yaml


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LAKEFS_INTEGRATION") != "1",
    reason="lakeFS integration tests require a running kind cluster and lakeFS deployment",
)

REPO_ROOT = Path(__file__).resolve().parents[3]
VALUES_PATH = REPO_ROOT / "platform/charts/lakefs/values-dev-kind.yaml"
OBJECT_PATH = "datasets/housing-sale/features.txt"


def test_lakefs_values_reference_secrets_without_embedded_credentials():
    values = yaml.safe_load(VALUES_PATH.read_text(encoding="utf-8"))

    assert values["existingSecret"] == "lakefs-secrets"
    assert values["secretKeys"]["databaseConnectionString"] == "database_connection_string"
    assert values["secretKeys"]["authEncryptSecretKey"] == "auth_encrypt_secret_key"

    rendered = json.dumps(values)
    forbidden = [
        "local-dev-cluster-postgres-password",
        "lakefs-admin-secret",
        "5555555555555555555555555555555555555555555555555555555555555555",
        "postgres://",
    ]
    for value in forbidden:
        assert value not in rendered


def test_lakefs_repository_branch_commit_merge_tag_and_read_by_commit():
    repository = f"study-lakefs-smoke-{int(time.time())}"
    with lakefs_port_forward():
        wait_for_lakefs()
        setup_lakefs()
        delete_repository_if_exists(repository)
        create_repository(repository)

        try:
            upload_object(repository, "main", OBJECT_PATH, b"version one\n")
            first_commit = commit(repository, "main", "initial version")

            create_branch(repository, "experiment", first_commit)
            upload_object(repository, "experiment", OBJECT_PATH, b"version two\n")
            second_commit = commit(repository, "experiment", "experiment version")

            merge(repository, "experiment", "main")
            create_tag(repository, "v2", second_commit)

            first_content = get_object(repository, first_commit, OBJECT_PATH)
            second_content = get_object(repository, second_commit, OBJECT_PATH)
            tagged_content = get_object(repository, "v2", OBJECT_PATH)

            assert first_content == b"version one\n"
            assert second_content == b"version two\n"
            assert tagged_content == b"version two\n"
            assert first_commit != second_commit

        finally:
            delete_repository_if_exists(repository)


@contextmanager
def lakefs_port_forward():
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "port-forward",
            "--namespace",
            namespace(),
            "svc/lakefs",
            f"{local_port()}:80",
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


def wait_for_local_port() -> None:
    for _ in range(60):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", local_port())) == 0:
                return
        time.sleep(0.5)
    raise AssertionError(f"lakeFS port-forward did not open 127.0.0.1:{local_port()}")


def wait_for_lakefs() -> None:
    for _ in range(60):
        try:
            request("GET", "/_health", api=False)
            return
        except urllib.error.URLError:
            time.sleep(1)
    raise AssertionError("lakeFS health endpoint did not become available")


def setup_lakefs() -> None:
    payload = {
        "username": admin_username(),
        "key": {
            "access_key_id": admin_access_key(),
            "secret_access_key": admin_secret_key(),
        },
    }
    try:
        request("POST", "/setup_lakefs", payload=payload, authorized=False)
    except urllib.error.HTTPError as exc:
        if exc.code != 409:
            raise


def create_repository(repository: str) -> None:
    payload = {
        "name": repository,
        "storage_namespace": f"s3://ml-platform-artifacts/lakefs/{repository}/",
        "default_branch": "main",
        "sample_data": False,
    }
    request("POST", "/repositories", payload=payload)


def delete_repository_if_exists(repository: str) -> None:
    try:
        request("DELETE", f"/repositories/{repository}")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise


def create_branch(repository: str, branch: str, source: str) -> None:
    request("POST", f"/repositories/{repository}/branches", payload={"name": branch, "source": source})


def upload_object(repository: str, branch: str, path: str, content: bytes) -> None:
    request(
        "POST",
        f"/repositories/{repository}/branches/{branch}/objects",
        query={"path": path},
        body=content,
        content_type="application/octet-stream",
    )


def commit(repository: str, branch: str, message: str) -> str:
    response = request(
        "POST",
        f"/repositories/{repository}/branches/{branch}/commits",
        payload={"message": message, "metadata": {"issue": "03.04"}},
    )
    parsed = json.loads(response)
    commit_id = parsed["id"]
    assert isinstance(commit_id, str)
    return commit_id


def merge(repository: str, source_ref: str, destination_branch: str) -> None:
    request(
        "POST",
        f"/repositories/{repository}/refs/{source_ref}/merge/{destination_branch}",
        payload={"message": f"merge {source_ref} into {destination_branch}"},
    )


def create_tag(repository: str, tag: str, ref: str) -> None:
    request("POST", f"/repositories/{repository}/tags", payload={"id": tag, "ref": ref})


def get_object(repository: str, ref: str, path: str) -> bytes:
    return request("GET", f"/repositories/{repository}/refs/{ref}/objects", query={"path": path})


def request(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    body: bytes | None = None,
    query: dict[str, str] | None = None,
    content_type: str = "application/json",
    authorized: bool = True,
    api: bool = True,
) -> bytes:
    query_string = urllib.parse.urlencode(query or {})
    prefix = "/api/v1" if api else ""
    url = f"{endpoint()}{prefix}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    headers: dict[str, str] = {}
    data = body
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = content_type
    elif body is not None:
        headers["Content-Type"] = content_type

    if authorized:
        token = base64.b64encode(f"{admin_access_key()}:{admin_secret_key()}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()


def endpoint() -> str:
    return os.environ.get("LAKEFS_ENDPOINT", f"http://127.0.0.1:{local_port()}").rstrip("/")


def local_port() -> int:
    return int(os.environ.get("LAKEFS_PORT", "18084"))


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def namespace() -> str:
    return os.environ.get("LAKEFS_NAMESPACE", "ml-platform-data")


def admin_username() -> str:
    return os.environ.get("LAKEFS_ADMIN_USERNAME", "lakefs-admin")


def admin_access_key() -> str:
    return secret_value("lakefs-admin-credentials", "access-key-id")


def admin_secret_key() -> str:
    return secret_value("lakefs-admin-credentials", "secret-access-key")


def secret_value(secret_name: str, key: str) -> str:
    secret = kubectl_json("get", "secret", secret_name, "--namespace", namespace(), "-o", "json")
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
