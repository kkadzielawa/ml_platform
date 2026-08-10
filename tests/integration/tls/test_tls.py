from __future__ import annotations

import json
import os
import socket
import ssl
import subprocess
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_TLS_INTEGRATION") != "1",
    reason="TLS integration tests require a running kind cluster, cert-manager, and Envoy Gateway",
)


def test_certificates_are_ready():
    local_ca = kubectl_json(
        "get",
        "certificate",
        "ml-platform-local-ca",
        "--namespace",
        "ml-platform-system",
        "-o",
        "json",
    )
    gateway_certificate = kubectl_json(
        "get",
        "certificate",
        "gateway-echo-tls",
        "--namespace",
        "ml-platform-system",
        "-o",
        "json",
    )

    assert_condition(local_ca["status"]["conditions"], "Ready", "True")
    assert_condition(gateway_certificate["status"]["conditions"], "Ready", "True")


def test_https_route_uses_configured_local_ca():
    response = https_get("/gateway-echo")

    assert response.status_line.startswith("HTTP/1.1 200"), response.raw
    assert "gateway-echo" in response.body


def test_plain_http_redirects_to_https():
    response = http_get("/gateway-echo")

    assert response.status_line.startswith("HTTP/1.1 301"), response.raw
    assert response.headers["location"] == f"https://{gateway_host()}:{gateway_https_port()}/gateway-echo"
    assert "gateway-echo" not in response.body


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
    condition = next(
        (item for item in conditions if item.get("type") == condition_type),
        None,
    )
    assert condition is not None, f"missing condition {condition_type!r}"
    assert condition["status"] == status, condition


def https_get(path: str) -> HttpResponse:
    ca_bundle = Path(os.environ.get("TLS_CA_BUNDLE", "/tmp/ml-platform-local-ca.crt"))
    assert ca_bundle.is_file(), f"missing CA bundle: {ca_bundle}"

    context = ssl.create_default_context(cafile=str(ca_bundle))
    with socket.create_connection(("127.0.0.1", gateway_https_port()), timeout=10) as raw_socket:
        with context.wrap_socket(raw_socket, server_hostname=gateway_host()) as tls_socket:
            return send_http_request(tls_socket, path)


def http_get(path: str) -> HttpResponse:
    with socket.create_connection(("127.0.0.1", gateway_http_port()), timeout=10) as raw_socket:
        return send_http_request(raw_socket, path)


def send_http_request(connection: socket.socket, path: str) -> HttpResponse:
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {gateway_host()}\r\n"
        "User-Agent: ml-platform-study-tls-test\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    connection.sendall(request.encode("ascii"))

    chunks = []
    while True:
        chunk = connection.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)

    raw = b"".join(chunks).decode("utf-8", errors="replace")
    header_block, _, body = raw.partition("\r\n\r\n")
    header_lines = header_block.split("\r\n")
    status_line = header_lines[0]
    headers = {}
    for line in header_lines[1:]:
        name, _, value = line.partition(":")
        headers[name.lower()] = value.strip()
    return HttpResponse(status_line=status_line, headers=headers, body=body, raw=raw)


class HttpResponse:
    def __init__(self, *, status_line: str, headers: dict[str, str], body: str, raw: str) -> None:
        self.status_line = status_line
        self.headers = headers
        self.body = body
        self.raw = raw


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def gateway_host() -> str:
    return os.environ.get("GATEWAY_HOST", "gateway.ml-platform.local")


def gateway_http_port() -> int:
    return int(os.environ.get("GATEWAY_HTTP_PORT", "8080"))


def gateway_https_port() -> int:
    return int(os.environ.get("GATEWAY_HTTPS_PORT", "8443"))
