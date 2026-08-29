"""Small stdlib lakeFS client used by the study ingestion command."""

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
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LakeFSNotFoundError(RuntimeError):
    """Raised when a lakeFS object or repository does not exist."""


@dataclass(frozen=True)
class LakeFSClient:
    """Minimal lakeFS API client for local study workflows."""

    endpoint: str
    access_key_id: str
    secret_access_key: str

    @classmethod
    def from_environment(cls) -> "LakeFSClient":
        return cls(
            endpoint=os.environ.get("LAKEFS_ENDPOINT", f"http://127.0.0.1:{os.environ.get('LAKEFS_PORT', '18084')}").rstrip("/"),
            access_key_id=os.environ.get("LAKEFS_ADMIN_ACCESS_KEY") or kubernetes_secret_value("access-key-id"),
            secret_access_key=os.environ.get("LAKEFS_ADMIN_SECRET_KEY") or kubernetes_secret_value("secret-access-key"),
        )

    def setup(self) -> None:
        payload = {
            "username": os.environ.get("LAKEFS_ADMIN_USERNAME", "lakefs-admin"),
            "key": {
                "access_key_id": self.access_key_id,
                "secret_access_key": self.secret_access_key,
            },
        }
        try:
            self.request("POST", "/setup_lakefs", payload=payload, authorized=False)
        except urllib.error.HTTPError as exc:
            if exc.code != 409:
                raise

    def ensure_repository(self, repository: str, *, storage_namespace: str) -> None:
        payload = {
            "name": repository,
            "storage_namespace": storage_namespace,
            "default_branch": "main",
            "sample_data": False,
        }
        try:
            self.request("POST", "/repositories", payload=payload)
        except urllib.error.HTTPError as exc:
            if exc.code != 409:
                raise

    def branch_head(self, repository: str, branch: str) -> str | None:
        try:
            payload = json.loads(self.request("GET", f"/repositories/{repository}/branches/{branch}"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise
        for key in ("commit_id", "id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        commit = payload.get("commit")
        if isinstance(commit, dict) and isinstance(commit.get("id"), str):
            return commit["id"]
        return None

    def create_branch(self, repository: str, branch: str, source: str) -> None:
        self.request("POST", f"/repositories/{repository}/branches", payload={"name": branch, "source": source})

    def upload_file(self, repository: str, branch: str, path: str, local_path: Path) -> None:
        self.upload_bytes(repository, branch, path, local_path.read_bytes())

    def upload_bytes(self, repository: str, branch: str, path: str, content: bytes) -> None:
        self.request(
            "POST",
            f"/repositories/{repository}/branches/{branch}/objects",
            query={"path": path},
            body=content,
            content_type="application/octet-stream",
        )

    def get_object(self, repository: str, ref: str, path: str) -> bytes:
        try:
            return self.request("GET", f"/repositories/{repository}/refs/{ref}/objects", query={"path": path})
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LakeFSNotFoundError(path) from exc
            raise

    def commit(self, repository: str, branch: str, *, message: str, metadata: dict[str, str]) -> str:
        response = self.request(
            "POST",
            f"/repositories/{repository}/branches/{branch}/commits",
            payload={"message": message, "metadata": metadata},
        )
        parsed = json.loads(response)
        commit_id = parsed["id"]
        if not isinstance(commit_id, str):
            raise TypeError("lakeFS commit response did not include a string id")
        return commit_id

    def merge(self, repository: str, source_ref: str, destination_branch: str) -> None:
        self.request(
            "POST",
            f"/repositories/{repository}/refs/{source_ref}/merge/{destination_branch}",
            payload={"message": f"merge {source_ref} into {destination_branch}"},
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        body: bytes | None = None,
        query: dict[str, str] | None = None,
        content_type: str = "application/json",
        authorized: bool = True,
    ) -> bytes:
        query_string = urllib.parse.urlencode(query or {})
        url = f"{self.endpoint}/api/v1{path}"
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
            token = base64.b64encode(f"{self.access_key_id}:{self.secret_access_key}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()


def kubernetes_secret_value(key: str) -> str:
    secret_name = os.environ.get("LAKEFS_ADMIN_SECRET_NAME", "lakefs-admin-credentials")
    namespace = os.environ.get("LAKEFS_NAMESPACE", "ml-platform-data")
    cluster_name = os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
    result = subprocess.run(
        [
            "kubectl",
            "--context",
            f"kind-{cluster_name}",
            "get",
            "secret",
            secret_name,
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
    return base64.b64decode(payload["data"][key]).decode("utf-8")


@contextmanager
def lakefs_port_forward():
    """Open a local port-forward to the in-cluster lakeFS service."""

    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{os.environ.get('KIND_CLUSTER_NAME', 'ml-platform-study-dev')}",
            "port-forward",
            "--namespace",
            os.environ.get("LAKEFS_NAMESPACE", "ml-platform-data"),
            "svc/lakefs",
            f"{os.environ.get('LAKEFS_PORT', '18084')}:80",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_local_port(int(os.environ.get("LAKEFS_PORT", "18084")))
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for_local_port(port: int) -> None:
    for _ in range(60):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise TimeoutError(f"lakeFS port-forward did not open 127.0.0.1:{port}")
