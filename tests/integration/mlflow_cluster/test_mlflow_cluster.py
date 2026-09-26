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

import pytest
import yaml

from tests.integration.object_store.smoke_s3 import request as signed_s3_request


REPO_ROOT = Path(__file__).resolve().parents[3]
MLFLOW_DIR = REPO_ROOT / "clusters/dev/mlflow"
MLFLOW_MANIFEST = MLFLOW_DIR / "mlflow.yaml"
PROXY_MANIFEST = MLFLOW_DIR / "mlflow-proxy.yaml"
KUSTOMIZATION = MLFLOW_DIR / "kustomization.yaml"


def test_cluster_mlflow_manifest_uses_own_database_and_artifact_scope():
    documents = list(yaml.safe_load_all(MLFLOW_MANIFEST.read_text(encoding="utf-8")))
    deployment, service = documents
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    env = {item["name"]: item for item in container["env"]}

    assert container["image"].startswith("ghcr.io/mlflow/mlflow:v3.13.0@sha256:")
    assert env["MLFLOW_BACKEND_STORE_URI"]["valueFrom"]["secretKeyRef"]["name"] == "mlflow-backend"
    assert env["AWS_ACCESS_KEY_ID"]["valueFrom"]["secretKeyRef"]["key"] == "artifacts-access-key-id"
    assert env["AWS_SECRET_ACCESS_KEY"]["valueFrom"]["secretKeyRef"]["key"] == "artifacts-secret-access-key"
    assert env["MLFLOW_DEFAULT_ARTIFACT_ROOT"]["value"].startswith(
        "s3://ml-platform-artifacts/projects/ml-platform/artifacts/mlflow"
    )
    command = " ".join(container["args"])
    assert "--allowed-hosts" in command
    assert "mlflow.ml-platform-data.svc.cluster.local:5000" in command
    assert "--cors-allowed-origins" in command
    assert "models-access-key-id" not in MLFLOW_MANIFEST.read_text(encoding="utf-8")
    assert service["spec"]["ports"][0]["port"] == 5000


def test_cluster_mlflow_proxy_requires_keycloak_and_does_not_embed_credentials():
    documents = list(yaml.safe_load_all(PROXY_MANIFEST.read_text(encoding="utf-8")))
    deployment, service = documents
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    args = container["args"]
    env = {item["name"]: item for item in container["env"]}

    assert "--provider=keycloak-oidc" in args
    assert "--cookie-secure=false" in args
    assert "--upstream=http://mlflow.ml-platform-data.svc.cluster.local:5000" in args
    assert any(item.startswith("--oidc-issuer-url=http://keycloak.") for item in args)
    assert any(item.startswith("--login-url=http://127.0.0.1:18081/") for item in args)
    assert env["OAUTH2_PROXY_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"]["name"] == "mlflow-oidc-client"
    assert env["OAUTH2_PROXY_COOKIE_SECRET"]["valueFrom"]["secretKeyRef"]["key"] == "cookie-secret"
    assert service["spec"]["ports"][0]["port"] == 4180
    rendered = PROXY_MANIFEST.read_text(encoding="utf-8")
    assert "local-dev-mlflow" not in rendered


def test_cluster_mlflow_kustomization_keeps_migration_jobs_explicit():
    kustomization = yaml.safe_load(KUSTOMIZATION.read_text(encoding="utf-8"))
    assert kustomization["resources"] == ["mlflow-postgres.yaml", "mlflow.yaml", "mlflow-proxy.yaml"]
    generated = {item["name"]: item for item in kustomization["configMapGenerator"]}
    assert generated["mlflow-oidc-registration"]["files"] == ["register_mlflow_oidc.py"]
    assert generated["mlflow-baseline-recreation"]["files"] == [
        "recreate_baseline.py",
        "phase-0-baseline-export.json",
    ]
    registration = yaml.safe_load((MLFLOW_DIR / "mlflow-oidc-registration.yaml").read_text(encoding="utf-8"))
    assert registration["metadata"]["namespace"] == "ml-platform-system"


@pytest.mark.skipif(
    os.environ.get("RUN_CLUSTER_MLFLOW_INTEGRATION") != "1",
    reason="MLflow cluster tests require a running kind cluster and deployment",
)
def test_cluster_mlflow_health_proxy_and_recreated_baseline():
    namespace = os.environ.get("MLFLOW_CLUSTER_NAMESPACE", "ml-platform-data")
    direct_port = int(os.environ.get("MLFLOW_CLUSTER_DIRECT_PORT", "15002"))
    auth_port = int(os.environ.get("MLFLOW_CLUSTER_PORT", "15001"))
    experiment = os.environ.get("MLFLOW_BASELINE_EXPERIMENT", "housing-sale-baseline-cluster")

    deployment = kubectl_json("get", "deployment", "mlflow", "-n", namespace, "-o", "json")
    proxy = kubectl_json("get", "deployment", "mlflow-auth", "-n", namespace, "-o", "json")
    assert deployment["status"].get("availableReplicas") == 1
    assert proxy["status"].get("availableReplicas") == 1

    with port_forward("svc/mlflow", direct_port, namespace, 5000):
        assert get_text(f"http://127.0.0.1:{direct_port}/health") == "OK"
        experiments = post_json(
            f"http://127.0.0.1:{direct_port}/api/2.0/mlflow/experiments/search",
            {"max_results": 100},
        )
        assert any(item["name"] == experiment for item in experiments.get("experiments", []))

    with port_forward("svc/mlflow-auth", auth_port, namespace, 4180):
        opener = urllib.request.build_opener(NoRedirect())
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            opener.open(f"http://127.0.0.1:{auth_port}/", timeout=20)
        assert exc_info.value.code in {302, 303, 307, 308}
        location = exc_info.value.headers.get("Location", "")
        if "/oauth2/start" in location:
            with pytest.raises(urllib.error.HTTPError) as start_info:
                opener.open(urllib.parse.urljoin(f"http://127.0.0.1:{auth_port}/", location), timeout=20)
            location = start_info.value.headers.get("Location", "")
        assert "/protocol/openid-connect/auth" in location


@pytest.mark.skipif(
    os.environ.get("RUN_CLUSTER_MLFLOW_INTEGRATION") != "1",
    reason="MLflow cluster tests require a running kind cluster and Garage",
)
def test_artifact_scope_cannot_write_to_models_bucket():
    namespace = os.environ.get("MLFLOW_CLUSTER_NAMESPACE", "ml-platform-data")
    local_port = int(os.environ.get("CLUSTER_GARAGE_PORT", "13900"))
    endpoint = f"http://127.0.0.1:{local_port}"
    object_key = f"projects/ml-platform/models/negative/mlflow-{int(time.time())}.txt"

    with port_forward("svc/garage-s3", local_port, namespace, 3900), pytest.raises(urllib.error.HTTPError) as exc_info:
        signed_s3_request(
            "PUT",
            endpoint,
            "ml-platform-models",
            object_key,
            "GK555555555555555555555555",
            "5555555555555555555555555555555555555555555555555555555555555555",
            "garage",
            body=b"cross-project artifact write must fail\n",
        )
    assert exc_info.value.code in {403, 404}


def kubectl_json(*args: str) -> dict[str, Any]:
    command = ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "command returned no diagnostic output").strip()
        pytest.fail(
            "MLflow cluster is not deployed; run `make apply-mlflow` successfully before "
            f"`make test-cluster-mlflow`. Command: {' '.join(command)}. Diagnostic: {detail}"
        )
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


@contextmanager
def port_forward(resource: str, local_port: int, namespace: str, remote_port: int):
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
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
    raise AssertionError(f"port-forward did not open 127.0.0.1:{port}")


def get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read().decode("utf-8")


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
