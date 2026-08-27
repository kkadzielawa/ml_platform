from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import time
import urllib.error
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from dataclasses import dataclass

import pytest

from tests.integration.object_store.smoke_s3 import request


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DATA_STORAGE_INTEGRATION") != "1",
    reason="data storage tests require a running kind cluster and Garage deployment",
)


@dataclass(frozen=True)
class Scope:
    name: str
    bucket: str
    prefix: str
    access_key: str
    secret_key: str


SCOPES = [
    Scope(
        name="raw",
        bucket="ml-platform-raw",
        prefix="projects/ml-platform/raw/",
        access_key="GK333333333333333333333333",
        secret_key="3333333333333333333333333333333333333333333333333333333333333333",
    ),
    Scope(
        name="curated",
        bucket="ml-platform-curated",
        prefix="projects/ml-platform/curated/",
        access_key="GK444444444444444444444444",
        secret_key="4444444444444444444444444444444444444444444444444444444444444444",
    ),
    Scope(
        name="artifacts",
        bucket="ml-platform-artifacts",
        prefix="projects/ml-platform/artifacts/",
        access_key="GK555555555555555555555555",
        secret_key="5555555555555555555555555555555555555555555555555555555555555555",
    ),
    Scope(
        name="models",
        bucket="ml-platform-models",
        prefix="projects/ml-platform/models/",
        access_key="GK666666666666666666666666",
        secret_key="6666666666666666666666666666666666666666666666666666666666666666",
    ),
    Scope(
        name="evaluation",
        bucket="ml-platform-evaluation",
        prefix="projects/ml-platform/evaluation/",
        access_key="GK777777777777777777777777",
        secret_key="7777777777777777777777777777777777777777777777777777777777777777",
    ),
]


def test_data_storage_bootstrap_is_idempotent():
    run_bootstrap()
    run_bootstrap()


@pytest.mark.parametrize("scope", SCOPES, ids=lambda scope: scope.name)
def test_scope_identity_can_access_own_bucket_and_prefix(scope: Scope):
    object_key = f"{scope.prefix}smoke/{int(time.time())}.txt"
    body = f"{scope.name} scoped data storage smoke\n".encode()
    expected_sha256 = hashlib.sha256(body).hexdigest()

    with garage_port_forward():
        s3_request("PUT", scope, scope.bucket, object_key, body=body)
        fetched = s3_request("GET", scope, scope.bucket, object_key)
        assert hashlib.sha256(fetched).hexdigest() == expected_sha256

        listing = s3_request(
            "GET",
            scope,
            scope.bucket,
            "",
            query={"list-type": "2", "prefix": f"{scope.prefix}smoke/"},
        )
        keys = {element.text for element in ET.fromstring(listing).iter() if element.tag.endswith("Key")}
        assert object_key in keys

        s3_request("DELETE", scope, scope.bucket, object_key)


@pytest.mark.parametrize(
    ("scope", "other_scope"),
    [(scope, SCOPES[(index + 1) % len(SCOPES)]) for index, scope in enumerate(SCOPES)],
    ids=lambda value: value.name,
)
def test_scope_identity_cannot_write_to_another_scope_bucket(scope: Scope, other_scope: Scope):
    object_key = f"{other_scope.prefix}negative/{int(time.time())}.txt"

    with garage_port_forward(), pytest.raises(urllib.error.HTTPError) as exc_info:
        s3_request("PUT", scope, other_scope.bucket, object_key, body=b"cross-scope write should fail\n")

    assert exc_info.value.code in {403, 404}


def run_bootstrap() -> None:
    result = subprocess.run(
        ["bash", "scripts/data/bootstrap/data-storage.sh"],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "KIND_CLUSTER_NAME": kind_cluster_name(),
            "CLUSTER_GARAGE_NAMESPACE": namespace(),
        },
    )
    assert "data storage buckets and scoped credentials are ready" in result.stdout


def s3_request(
    method: str,
    scope: Scope,
    bucket: str,
    key: str,
    *,
    body: bytes = b"",
    query: dict[str, str] | None = None,
) -> bytes:
    return request(
        method,
        endpoint(),
        bucket,
        key,
        scope.access_key,
        scope.secret_key,
        region(),
        body=body,
        query=query,
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


def endpoint() -> str:
    return os.environ.get("GARAGE_S3_ENDPOINT", f"http://127.0.0.1:{local_port()}").rstrip("/")


def local_port() -> int:
    return int(os.environ.get("CLUSTER_GARAGE_PORT", "13900"))


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def namespace() -> str:
    return os.environ.get("CLUSTER_GARAGE_NAMESPACE", "ml-platform-data")


def region() -> str:
    return os.environ.get("GARAGE_S3_REGION", "garage")
