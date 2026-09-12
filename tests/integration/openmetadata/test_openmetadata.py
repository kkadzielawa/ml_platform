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

from clusters.dev.openmetadata.register_baseline_metadata import (
    get_lineage_by_name,
    get_quality_test_case_by_name,
    get_table_by_name,
    load_seed,
    local_openmetadata_session,
    table_fully_qualified_name,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE_PATH = REPO_ROOT / "Makefile"
VALUES_PATH = REPO_ROOT / "platform/charts/openmetadata/values-dev-kind.yaml"
DEPENDENCY_VALUES_PATH = REPO_ROOT / "platform/charts/openmetadata/values-dependencies-dev-kind.yaml"
OIDC_ADAPTER_PATH = REPO_ROOT / "clusters/dev/openmetadata/oidc-discovery-adapter.yaml"
BROWSER_AUTHORITY = "http://127.0.0.1:18081/realms/ml-platform-study"
OIDC_ADAPTER_BASE_URL = "http://openmetadata-oidc-discovery-adapter.ml-platform-data.svc.cluster.local:8080"


def test_openmetadata_values_are_sized_for_study_and_use_existing_identity():
    values = yaml.safe_load(VALUES_PATH.read_text(encoding="utf-8"))
    deps = yaml.safe_load(DEPENDENCY_VALUES_PATH.read_text(encoding="utf-8"))

    assert values["replicaCount"] == 1
    assert values["openmetadata"]["config"]["database"]["dbScheme"] == "postgresql"
    assert values["openmetadata"]["config"]["database"]["host"] == "openmetadata-postgres-rw.ml-platform-data.svc.cluster.local"
    assert values["openmetadata"]["config"]["database"]["auth"]["password"]["secretRef"] == "openmetadata-postgres-app"
    assert values["openmetadata"]["config"]["elasticsearch"]["searchType"] == "opensearch"
    assert values["openmetadata"]["config"]["authentication"]["provider"] == "custom-oidc"
    assert values["openmetadata"]["config"]["authentication"]["oidcConfiguration"]["oidcType"] == "Keycloak"
    assert values["openmetadata"]["config"]["authentication"]["authority"] == (
        BROWSER_AUTHORITY
    )
    assert values["openmetadata"]["config"]["authentication"]["oidcConfiguration"]["discoveryUri"] == (
        f"{OIDC_ADAPTER_BASE_URL}/realms/ml-platform-study/.well-known/openid-configuration"
    )
    assert values["resources"]["limits"] == {"cpu": "400m", "memory": "1440Mi"}

    assert deps["mysql"]["enabled"] is False
    assert deps["airflow"]["enabled"] is False
    assert deps["opensearch"]["enabled"] is True
    assert deps["opensearch"]["singleNode"] is True


def test_oidc_discovery_adapter_keeps_front_and_back_channel_routes_separate():
    documents = list(yaml.safe_load_all(OIDC_ADAPTER_PATH.read_text(encoding="utf-8")))
    configmap, deployment, service = documents
    nginx_config = configmap["data"]["default.conf"]
    container = deployment["spec"]["template"]["spec"]["containers"][0]

    assert deployment["metadata"]["name"] == "openmetadata-oidc-discovery-adapter"
    assert service["metadata"]["name"] == "openmetadata-oidc-discovery-adapter"
    assert container["image"].startswith("docker.io/nginxinc/nginx-unprivileged:1.27.5-alpine@sha256:")
    assert container["resources"]["limits"] == {"cpu": "100m", "memory": "96Mi"}
    assert "proxy_set_header Host 127.0.0.1:18081;" in nginx_config
    assert "sub_filter_types application/json;" in nginx_config
    assert "protocol/openid-connect/token" in nginx_config
    assert OIDC_ADAPTER_BASE_URL in nginx_config


def test_openmetadata_manifests_do_not_embed_runtime_secrets():
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in openmetadata_paths())

    forbidden = [
        "local-dev-openmetadata-password",
        "openmetadata-postgres-password",
        "OPENMETADATA_JWT_TOKEN=",
        "clientSecret: local",
        "jwtToken",
    ]
    for value in forbidden:
        assert value not in rendered

    assert "secretRef: openmetadata-oidc-client" in rendered
    assert "secretRef: openmetadata-postgres-app" in rendered


def test_openmetadata_helm_routes_pin_the_kind_context():
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
    openmetadata_recipe = makefile.split("apply-openmetadata:", 1)[1].split(
        "apply-registry:", 1
    )[0]

    assert openmetadata_recipe.count("--kube-context kind-$(KIND_CLUSTER_NAME)") == 4
    assert (
        "rollout restart --namespace $(OPENMETADATA_NAMESPACE) "
        "deployment/openmetadata-oidc-discovery-adapter"
    ) in openmetadata_recipe


def test_openmetadata_test_target_passes_the_local_token_password_without_echoing_it():
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
    test_recipe = makefile.split("test-openmetadata:", 1)[1].split("test-manifests:", 1)[0]

    assert test_recipe.startswith('\n\t@OPENMETADATA_ADMIN_PASSWORD="$(OPENMETADATA_ADMIN_PASSWORD)"')


def test_baseline_catalog_seed_contains_owner_schema_quality_and_lineage():
    seed = load_seed()

    assert seed["owner"] == {"name": "platform-learners", "type": "team"}
    assert seed["table"]["name"] == "housing-sale-features-v0001"
    assert seed["table"]["databaseSchema"] == "ml-platform-lakefs.housing-sale-ingestion.curated"
    assert len(seed["table"]["columns"]) == 16
    assert seed["rawSchema"]["name"] == "raw"
    assert {table["name"] for table in seed["rawTables"]} == {
        "housing-sale-train-v0001",
        "housing-sale-test-v0001",
    }
    assert seed["quality"]["suite"] == "housing_sale_features_quality"
    assert seed["quality"]["testCaseName"] == "housing_sale_features_quality_fixture"
    assert seed["quality"]["result"] == "pass"
    assert seed["quality"]["evidence"] == "fixture"
    assert seed["pipeline"]["name"] == seed["lineage"]["run"]
    assert seed["lineage"]["commit"] == "fixture-commit-0001"
    assert seed["lineage"]["run"] == "baseline-versioned-ingestion"
    assert len(seed["lineage"]["inputs"]) == 2
    assert seed["lineage"]["outputs"] == [
        "s3://ml-platform-artifacts/lakefs/housing-sale-ingestion/curated/housing-sale-features/v0001/"
    ]


@pytest.mark.skipif(
    os.environ.get("RUN_OPENMETADATA_INTEGRATION") != "1",
    reason="OpenMetadata live tests require a running kind cluster and OpenMetadata deployment",
)
def test_openmetadata_server_is_available_and_catalog_seed_configmap_exists():
    deployment = kubectl_json("get", "deployment", "openmetadata", "--namespace", namespace(), "-o", "json")
    adapter = kubectl_json(
        "get", "deployment", "openmetadata-oidc-discovery-adapter", "--namespace", namespace(), "-o", "json"
    )
    configmap = kubectl_json("get", "configmap", "openmetadata-baseline-catalog-seed", "--namespace", namespace(), "-o", "json")
    seed = load_seed()

    assert deployment["status"].get("availableReplicas") == 1
    assert adapter["status"].get("availableReplicas") == 1
    assert "baseline-catalog.json" in configmap["data"]

    with port_forward("svc/openmetadata", local_port(), 8585):
        health = get_text(f"http://127.0.0.1:{local_port()}/api/v1/system/health")
        auth = get_json(f"http://127.0.0.1:{local_port()}/api/v1/system/config/auth")
        login_location = get_redirect(
            f"http://127.0.0.1:{local_port()}/api/v1/auth/login?"
            + urllib.parse.urlencode({"redirectUri": f"http://127.0.0.1:{local_port()}/auth/callback"})
        )

    assert health == "OK"
    assert auth["authority"] == BROWSER_AUTHORITY
    assert login_location.startswith(f"{BROWSER_AUTHORITY}/protocol/openid-connect/auth?")

    with port_forward("svc/openmetadata-oidc-discovery-adapter", adapter_port(), 8080):
        discovery = get_json(
            f"http://127.0.0.1:{adapter_port()}/realms/ml-platform-study/.well-known/openid-configuration"
        )
        jwks = get_json(
            f"http://127.0.0.1:{adapter_port()}/realms/ml-platform-study/protocol/openid-connect/certs"
        )

    assert discovery["issuer"] == BROWSER_AUTHORITY
    assert discovery["authorization_endpoint"].startswith(
        f"{BROWSER_AUTHORITY}/protocol/openid-connect/auth"
    )
    assert discovery["token_endpoint"].startswith(OIDC_ADAPTER_BASE_URL)
    assert discovery["jwks_uri"].startswith(OIDC_ADAPTER_BASE_URL)
    assert jwks["keys"]

    with local_openmetadata_session() as session:
        table_fqn = table_fully_qualified_name(seed["table"])
        table = get_table_by_name(
            session.base_url,
            session.token,
            table_fqn,
            fields="owners",
        )
        quality = get_quality_test_case_by_name(
            session.base_url,
            session.token,
            f"{table_fqn}.{seed['quality']['testCaseName']}",
        )
        lineage = get_lineage_by_name(session.base_url, session.token, table_fqn)

    assert table["name"] == seed["table"]["name"]
    assert table["owners"][0]["name"] == seed["owner"]["name"]
    assert len(table["columns"]) == len(seed["table"]["columns"])
    assert quality["testCaseResult"]["testCaseStatus"] == "Success"
    assert {item["name"]: item["value"] for item in quality["testCaseResult"]["testResultValue"]} == {
        "evidence": "fixture",
        "suite": seed["quality"]["suite"],
        "dataset_revision": seed["lineage"]["commit"],
        "run": seed["lineage"]["run"],
    }

    upstream_names = {node["name"] for node in lineage.get("nodes", [])}
    assert upstream_names >= {table["name"] for table in seed["rawTables"]}
    upstream_edges = lineage.get("upstreamEdges", [])
    assert any(
        seed["lineage"]["run"] in edge.get("lineageDetails", {}).get("description", "")
        and seed["lineage"]["commit"] in edge.get("lineageDetails", {}).get("description", "")
        and edge.get("lineageDetails", {}).get("pipeline", {}).get("name") == seed["pipeline"]["name"]
        for edge in upstream_edges
    )


def openmetadata_paths() -> list[Path]:
    return sorted((REPO_ROOT / "platform/charts/openmetadata").glob("*.yaml")) + sorted(
        (REPO_ROOT / "clusters/dev/openmetadata").glob("*.yaml")
    )


@contextmanager
def port_forward(resource: str, local_port: int, remote_port: int):
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "port-forward",
            "--namespace",
            namespace(),
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
    raise AssertionError(f"OpenMetadata port-forward did not open 127.0.0.1:{port}")


def get_text(url: str) -> str:
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def get_json(url: str) -> dict[str, Any]:
    return json.loads(get_text(url))


def get_redirect(url: str) -> str:
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, headers, newurl):  # type: ignore[no-untyped-def]
            return None

    opener = urllib.request.build_opener(NoRedirect())
    try:
        opener.open(url, timeout=20)
    except urllib.error.HTTPError as error:
        assert error.code in {301, 302, 303, 307, 308}
        location = error.headers.get("Location")
        assert location
        return location
    raise AssertionError("OpenMetadata login endpoint did not redirect to Keycloak")


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


def namespace() -> str:
    return os.environ.get("OPENMETADATA_NAMESPACE", "ml-platform-data")


def local_port() -> int:
    return int(os.environ.get("OPENMETADATA_PORT", "8585"))


def adapter_port() -> int:
    return int(os.environ.get("OPENMETADATA_OIDC_ADAPTER_PORT", "18586"))


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
