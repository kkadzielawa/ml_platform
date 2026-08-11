from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import time
from contextlib import contextmanager

import pytest

from tests.integration.object_store.smoke_s3 import request


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CLUSTER_OBJECT_STORE_INTEGRATION") != "1",
    reason="cluster object storage tests require a running kind cluster and Garage deployment",
)


def test_cluster_garage_s3_contract_put_get_list_delete():
    with garage_port_forward():
        from tests.integration.object_store.smoke_s3 import main

        main()


def test_cluster_garage_storage_survives_pod_restart():
    key = f"smoke/persistence-{int(time.time())}.txt"
    body = b"garage cluster persistence smoke ok\n"
    expected_sha256 = hashlib.sha256(body).hexdigest()

    with garage_port_forward():
        s3_request("PUT", key, body=body)

    original_uid = garage_pod_uid()
    kubectl("delete", "pod", "garage-0", "--namespace", namespace())
    wait_for_garage_ready()
    wait_for_garage_pod_recreated(original_uid)

    with garage_port_forward():
        fetched = s3_request("GET", key)
        assert hashlib.sha256(fetched).hexdigest() == expected_sha256
        s3_request("DELETE", key)


def s3_request(method: str, key: str, *, body: bytes = b"") -> bytes:
    return request(
        method,
        endpoint(),
        bucket(),
        key,
        access_key(),
        secret_key(),
        region(),
        body=body,
    )


@contextmanager
def garage_port_forward():
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "port-forward",
            "--namespace",
            namespace(),
            "svc/garage-s3",
            f"{local_port()}:3900",
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
    raise AssertionError(f"Garage port-forward did not open 127.0.0.1:{local_port()}")


def wait_for_garage_ready() -> None:
    kubectl(
        "wait",
        "--timeout=5m",
        "--namespace",
        namespace(),
        "statefulset/garage",
        "--for=jsonpath={.status.readyReplicas}=1",
    )


def wait_for_garage_pod_recreated(original_uid: str) -> None:
    for _ in range(60):
        current_uid = garage_pod_uid()
        if current_uid != original_uid:
            return
        time.sleep(5)
    raise AssertionError("Garage pod was not recreated within timeout")


def garage_pod_uid() -> str:
    result = kubectl("get", "pod", "garage-0", "--namespace", namespace(), "-o", "jsonpath={.metadata.uid}")
    return result.stdout.strip()


def kubectl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def endpoint() -> str:
    return os.environ.get("GARAGE_S3_ENDPOINT", f"http://127.0.0.1:{local_port()}").rstrip("/")


def local_port() -> int:
    return int(os.environ.get("CLUSTER_GARAGE_PORT", "13900"))


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def namespace() -> str:
    return os.environ.get("CLUSTER_GARAGE_NAMESPACE", "ml-platform-data")


def bucket() -> str:
    return os.environ.get("GARAGE_BUCKET", "ml-platform-artifacts")


def access_key() -> str:
    return os.environ.get("GARAGE_KEY_ID", "GK111111111111111111111111")


def secret_key() -> str:
    return os.environ.get("GARAGE_SECRET_KEY", "2222222222222222222222222222222222222222222222222222222222222222")


def region() -> str:
    return os.environ.get("GARAGE_S3_REGION", "garage")
