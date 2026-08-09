from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_GATEWAY_INTEGRATION") != "1",
    reason="gateway integration tests require a running kind cluster and Envoy Gateway",
)


def test_gateway_and_route_are_accepted_and_programmed():
    gateway_class = kubectl_json("get", "gatewayclass", "ml-platform-envoy", "-o", "json")
    assert_condition(gateway_class["status"]["conditions"], "Accepted", "True")

    gateway = kubectl_json(
        "get",
        "gateway",
        "ml-platform-local",
        "--namespace",
        "ml-platform-system",
        "-o",
        "json",
    )
    assert_condition(gateway["status"]["conditions"], "Accepted", "True")
    assert_condition(gateway["status"]["conditions"], "Programmed", "True")

    route = kubectl_json(
        "get",
        "httproute",
        "gateway-echo",
        "--namespace",
        "ml-platform-project-housing",
        "-o",
        "json",
    )
    parent_conditions = route["status"]["parents"][0]["conditions"]
    assert_condition(parent_conditions, "Accepted", "True")
    assert_condition(parent_conditions, "ResolvedRefs", "True")


def test_gateway_routes_expected_host_and_path():
    response = gateway_get("/gateway-echo", host=gateway_host())

    assert response.status == 200
    assert "gateway-echo" in response.body


def test_gateway_rejects_unknown_host_and_path():
    unknown_path = gateway_get("/not-a-platform-route", host=gateway_host(), allow_http_error=True)
    unknown_host = gateway_get("/gateway-echo", host="unknown.ml-platform.local", allow_http_error=True)

    assert unknown_path.status == 404
    assert unknown_host.status == 404
    assert "gateway-echo" not in unknown_path.body
    assert "gateway-echo" not in unknown_host.body


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


def gateway_get(path: str, *, host: str, allow_http_error: bool = False) -> GatewayResponse:
    request = urllib.request.Request(
        f"http://127.0.0.1:{gateway_http_port()}{path}",
        headers={"Host": host},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return GatewayResponse(
                status=response.status,
                body=response.read().decode("utf-8", errors="replace"),
            )
    except urllib.error.HTTPError as error:
        if not allow_http_error:
            raise
        return GatewayResponse(
            status=error.code,
            body=error.read().decode("utf-8", errors="replace"),
        )


class GatewayResponse:
    def __init__(self, *, status: int, body: str) -> None:
        self.status = status
        self.body = body


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def gateway_host() -> str:
    return os.environ.get("GATEWAY_HOST", "gateway.ml-platform.local")


def gateway_http_port() -> str:
    return os.environ.get("GATEWAY_HTTP_PORT", "8080")
