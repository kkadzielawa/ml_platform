from __future__ import annotations

import base64
import io
import json
import os
import re
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CI_INTEGRATION") != "1",
    reason="CI integration tests require Forgejo, Woodpecker, and Harbor in the kind cluster",
)


CI_PROJECT = "ci-study"
CI_REPOSITORY = "sample-pipeline"


def test_forgejo_and_woodpecker_are_ready_and_connected_to_forgejo():
    namespace = ci_namespace()
    forgejo = kubectl_json("get", "deployment", "forgejo", "--namespace", namespace, "-o", "json")
    server = kubectl_json("get", "statefulset", "woodpecker-server", "--namespace", namespace, "-o", "json")
    agent = kubectl_json("get", "statefulset", "woodpecker-agent", "--namespace", namespace, "-o", "json")

    assert forgejo["status"].get("availableReplicas") == 1
    assert server["status"].get("readyReplicas") == 1
    assert agent["status"].get("readyReplicas") == 1

    server_env = container_env(server, "server")
    agent_env = container_env(agent, "agent")
    assert env_value(server_env, "WOODPECKER_FORGEJO") == "true"
    assert "forgejo-http" in env_value(server_env, "WOODPECKER_FORGEJO_URL")
    assert env_value(agent_env, "WOODPECKER_BACKEND") == "kubernetes"
    assert env_value(agent_env, "WOODPECKER_BACKEND_K8S_NAMESPACE") == namespace


def test_sample_pipeline_is_commit_attributed_and_registry_scoped():
    commit_sha = current_commit_sha()
    assert re.fullmatch(r"[0-9a-f]{40}", commit_sha)

    with harbor_port_forward():
        wait_for_harbor_health()
        ensure_project(CI_PROJECT)
        robot = create_project_robot(CI_PROJECT, commit_sha)

        image = f"{registry_host()}/{CI_PROJECT}/{CI_REPOSITORY}:{commit_sha[:12]}"
        outside_image = f"{registry_host()}/library/{CI_REPOSITORY}:{commit_sha[:12]}"

        try:
            with tempfile.TemporaryDirectory(prefix="ci-robot-") as docker_config:
                docker_login(docker_config, robot["name"], robot["token"])
                create_tiny_image(image, commit_sha)
                pushed_digest = docker_push_digest(image, docker_config)

                docker(docker_config, "tag", image, outside_image)
                rejected = docker_run(docker_config, "push", outside_image, check=False)
                assert rejected.returncode != 0
                rejection_text = f"{rejected.stdout}\n{rejected.stderr}".lower()
                assert any(
                    phrase in rejection_text
                    for phrase in ("unauthorized", "authentication required", "denied", "insufficient_scope")
                )
        finally:
            delete_robot_by_id(robot["id"])

    kubectl(
        "create",
        "configmap",
        "ci-sample-pipeline-run",
        "--namespace",
        ci_namespace(),
        f"--from-literal=commit={commit_sha}",
        f"--from-literal=image={image}",
        f"--from-literal=digest={pushed_digest}",
        "--dry-run=client",
        "-o",
        "yaml",
        stdout_to_stdin_apply=True,
    )
    recorded = kubectl_json("get", "configmap", "ci-sample-pipeline-run", "--namespace", ci_namespace(), "-o", "json")
    assert recorded["data"]["commit"] == commit_sha
    assert recorded["data"]["digest"] == pushed_digest


def container_env(workload: dict[str, Any], container_name: str) -> list[dict[str, Any]]:
    containers = workload["spec"]["template"]["spec"]["containers"]
    container = next(item for item in containers if item["name"] == container_name)
    return list(container.get("env", []))


def env_value(env: list[dict[str, Any]], name: str) -> str:
    item = next(entry for entry in env if entry.get("name") == name)
    return str(item["value"])


def ensure_project(project_name: str) -> None:
    request = harbor_request(
        "GET",
        f"/api/v2.0/projects/{urllib.parse.quote(project_name, safe='')}",
        allow_http_error=True,
    )
    if request.status == 200:
        return
    assert request.status == 404, request.body
    response = harbor_request(
        "POST",
        "/api/v2.0/projects",
        {
            "project_name": project_name,
            "metadata": {"public": "false"},
        },
    )
    assert response.status in {200, 201}, response.body


def create_project_robot(project_name: str, commit_sha: str) -> dict[str, str]:
    robot_name = f"{project_name}-writer-{commit_sha[:8]}-{int(time.time())}"
    response = harbor_request(
        "POST",
        "/api/v2.0/robots",
        {
            "name": robot_name,
            "level": "project",
            "duration": 1,
            "description": "Study CI robot scoped to the ci-study project",
            "permissions": [
                {
                    "kind": "project",
                    "namespace": project_name,
                    "access": [
                        {"resource": "repository", "action": "pull"},
                        {"resource": "repository", "action": "push"},
                        {"resource": "artifact", "action": "read"},
                    ],
                }
            ],
        },
        allow_http_error=True,
    )
    if response.status in {200, 201}:
        payload = json.loads(response.body)
        return {"id": str(payload["id"]), "name": str(payload["name"]), "token": str(payload["secret"])}

    raise AssertionError(response.body)


def delete_robot_by_id(robot_id: str) -> None:
    harbor_request("DELETE", f"/api/v2.0/robots/{robot_id}", allow_http_error=True)


def harbor_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    allow_http_error: bool = False,
) -> HttpResponse:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{registry_url()}{path}",
        data=data,
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {basic_auth(admin_user(), admin_password())}",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return HttpResponse.from_url_response(response.status, response.headers, response.read())
    except urllib.error.HTTPError as error:
        if not allow_http_error:
            raise
        return HttpResponse.from_url_response(error.code, error.headers, error.read())


@contextmanager
def harbor_port_forward():
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "port-forward",
            "--namespace",
            harbor_namespace(),
            "svc/harbor",
            f"{local_registry_port()}:80",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_local_port(local_registry_port())
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for_harbor_health() -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{registry_url()}/api/v2.0/health", timeout=5) as response:
                body = response.read().decode("utf-8", errors="replace")
                if response.status == 200 and '"status":"healthy"' in body.replace(" ", ""):
                    return
        except OSError:
            pass
        time.sleep(2)
    raise AssertionError("Harbor health endpoint did not become healthy")


def wait_for_local_port(port: int) -> None:
    for _ in range(90):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(1)
    raise AssertionError(f"port-forward did not open 127.0.0.1:{port}")


def docker_login(docker_config: str, username: str, password: str) -> None:
    docker(
        docker_config,
        "login",
        registry_host(),
        "-u",
        username,
        "--password-stdin",
        input_text=f"{password}\n",
    )


def create_tiny_image(image: str, commit_sha: str) -> None:
    with tempfile.TemporaryDirectory(prefix="ci-image-") as directory:
        tar_path = Path(directory) / "image.tar"
        payload = f"ml-platform ci sample pipeline\ncommit={commit_sha}\n".encode("utf-8")
        tar_info = tarfile.TarInfo("CI_COMMIT.txt")
        tar_info.size = len(payload)
        tar_info.mtime = 0
        with tarfile.open(tar_path, "w") as archive:
            archive.addfile(tar_info, io.BytesIO(payload))
        subprocess.run(["docker", "import", str(tar_path), image], check=True, capture_output=True, text=True)


def docker_push_digest(image: str, docker_config: str) -> str:
    result = docker(docker_config, "push", image)
    match = re.search(r"digest:\s*(sha256:[a-f0-9]{64})", result.stdout)
    assert match is not None, result.stdout
    return match.group(1)


def docker(
    docker_config: str,
    *args: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return docker_run(docker_config, *args, input_text=input_text, check=True)


def docker_run(
    docker_config: str,
    *args: str,
    input_text: str | None = None,
    check: bool,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DOCKER_CONFIG"] = docker_config
    return subprocess.run(
        ["docker", *args],
        check=check,
        input=input_text,
        capture_output=True,
        text=True,
        env=environment,
    )


def current_commit_sha() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def basic_auth(username: str, password: str) -> str:
    return base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")


def kubectl_json(*args: str) -> dict[str, Any]:
    result = kubectl(*args)
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def kubectl(
    *args: str,
    stdout_to_stdin_apply: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args]
    if not stdout_to_stdin_apply:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    rendered = subprocess.run(command, check=True, capture_output=True, text=True)
    return subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", "apply", "-f", "-"],
        input=rendered.stdout,
        check=True,
        capture_output=True,
        text=True,
    )


class HttpResponse:
    def __init__(self, *, status: int, headers: dict[str, str], body: str) -> None:
        self.status = status
        self.headers = headers
        self.body = body

    @classmethod
    def from_url_response(cls, status: int, headers: Any, payload: bytes) -> "HttpResponse":
        return cls(
            status=status,
            headers={key.lower(): value for key, value in headers.items()},
            body=payload.decode("utf-8", errors="replace"),
        )


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def ci_namespace() -> str:
    return os.environ.get("CI_NAMESPACE", "ml-platform-ci")


def harbor_namespace() -> str:
    return os.environ.get("HARBOR_NAMESPACE", "ml-platform-system")


def admin_user() -> str:
    return os.environ.get("HARBOR_ADMIN_USER", "admin")


def admin_password() -> str:
    return os.environ.get("HARBOR_ADMIN_PASSWORD", "local-dev-harbor-password")


def registry_host() -> str:
    return os.environ.get("CLUSTER_REGISTRY_HOST", f"127.0.0.1:{local_registry_port()}")


def registry_url() -> str:
    return f"http://{registry_host()}"


def local_registry_port() -> int:
    return int(os.environ.get("CLUSTER_REGISTRY_PORT", "15000"))
