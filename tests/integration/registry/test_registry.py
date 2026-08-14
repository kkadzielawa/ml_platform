from __future__ import annotations

import io
import os
import re
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_REGISTRY_INTEGRATION") != "1",
    reason="registry integration tests require a running kind cluster and Harbor deployment",
)


def test_harbor_push_pull_digest_and_anonymous_rejection():
    tag_suffix = str(int(time.time()))
    image = f"{registry_host()}/library/harbor-smoke:{tag_suffix}"
    anonymous_image = f"{registry_host()}/library/anonymous-smoke:{tag_suffix}"

    with harbor_port_forward():
        wait_for_harbor_health()

        with tempfile.TemporaryDirectory(prefix="harbor-auth-") as auth_config:
            docker_login(auth_config)
            create_tiny_image(image)
            pushed_digest = docker_push_digest(image, auth_config)

            remove_local_image(image)
            docker(auth_config, "pull", image)
            pulled_digest = repo_digest(image)

            assert pulled_digest == pushed_digest

        with tempfile.TemporaryDirectory(prefix="harbor-anon-") as anonymous_config:
            create_tiny_image(anonymous_image)
            rejected = docker_run(anonymous_config, "push", anonymous_image, check=False)

            assert rejected.returncode != 0
            rejection_text = f"{rejected.stdout}\n{rejected.stderr}".lower()
            assert any(
                phrase in rejection_text
                for phrase in ("unauthorized", "authentication required", "denied", "no basic auth credentials")
            )


@contextmanager
def harbor_port_forward():
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "port-forward",
            "--namespace",
            namespace(),
            "svc/harbor",
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
    for _ in range(90):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", local_port())) == 0:
                return
        time.sleep(1)
    raise AssertionError(f"Harbor port-forward did not open 127.0.0.1:{local_port()}")


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


def docker_login(docker_config: str) -> None:
    docker(
        docker_config,
        "login",
        registry_host(),
        "-u",
        admin_user(),
        "--password-stdin",
        input_text=f"{admin_password()}\n",
    )


def create_tiny_image(image: str) -> None:
    with tempfile.TemporaryDirectory(prefix="harbor-image-") as directory:
        tar_path = Path(directory) / "image.tar"
        payload = b"ml-platform harbor smoke image\n"
        tar_info = tarfile.TarInfo("README.txt")
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


def repo_digest(image: str) -> str:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{index .RepoDigests 0}}", image],
        check=True,
        capture_output=True,
        text=True,
    )
    digest_ref = result.stdout.strip()
    assert "@" in digest_ref
    return digest_ref.rsplit("@", maxsplit=1)[1]


def remove_local_image(image: str) -> None:
    subprocess.run(["docker", "image", "rm", "--force", image], check=False, capture_output=True, text=True)


def docker(docker_config: str, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
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


def registry_url() -> str:
    return f"http://{registry_host()}"


def registry_host() -> str:
    return os.environ.get("CLUSTER_REGISTRY_HOST", f"127.0.0.1:{local_port()}")


def local_port() -> int:
    return int(os.environ.get("CLUSTER_REGISTRY_PORT", "15000"))


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def namespace() -> str:
    return os.environ.get("HARBOR_NAMESPACE", "ml-platform-system")


def admin_user() -> str:
    return os.environ.get("HARBOR_ADMIN_USER", "admin")


def admin_password() -> str:
    return os.environ.get("HARBOR_ADMIN_PASSWORD", "local-dev-harbor-password")
