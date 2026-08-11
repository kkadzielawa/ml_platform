from __future__ import annotations

import base64
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CLOUDNATIVEPG_INTEGRATION") != "1",
    reason="CloudNativePG integration tests require a running kind cluster and study database",
)


def test_database_manifest_references_secret_without_embedded_credentials():
    manifest = yaml.safe_load((repo_root() / "clusters/dev/databases/study-postgres.yaml").read_text(encoding="utf-8"))

    assert manifest["kind"] == "Cluster"
    initdb = manifest["spec"]["bootstrap"]["initdb"]
    assert initdb["secret"]["name"] == f"{cluster_name()}-app"

    rendered = json.dumps(manifest)
    assert "password" not in rendered.lower()
    assert "local-dev-cluster-postgres-password" not in rendered


def test_cluster_is_ready_and_accepts_sql():
    cluster = kubectl_json(
        "get",
        "cluster",
        cluster_name(),
        "--namespace",
        namespace(),
        "-o",
        "json",
    )

    assert_condition(cluster["status"]["conditions"], "Ready", "True")

    result = psql("SELECT current_database(), current_user;")
    assert database_name() in result.stdout
    assert database_user() in result.stdout


def test_data_survives_database_pod_restart():
    marker = f"restart-{int(time.time())}"
    psql(
        "CREATE TABLE IF NOT EXISTS platform_persistence_smoke "
        "(id text PRIMARY KEY, created_at timestamptz DEFAULT now());"
    )
    psql(
        "INSERT INTO platform_persistence_smoke (id) "
        f"VALUES ('{marker}') ON CONFLICT (id) DO NOTHING;"
    )

    original_pod = primary_pod()
    original_pod_name = original_pod["metadata"]["name"]
    original_pod_uid = original_pod["metadata"]["uid"]
    kubectl("delete", "pod", original_pod_name, "--namespace", namespace())
    wait_for_cluster_ready()
    wait_for_primary_pod_recreated(original_pod_uid)

    result = psql(f"SELECT count(*) FROM platform_persistence_smoke WHERE id = '{marker}';")
    assert result.stdout.strip().endswith("1")


def psql(sql: str) -> subprocess.CompletedProcess[str]:
    password = secret_value(f"{cluster_name()}-app", "password")
    return kubectl(
        "exec",
        primary_pod_name(),
        "--namespace",
        namespace(),
        "--",
        "env",
        f"PGPASSWORD={password}",
        "psql",
        "-h",
        "127.0.0.1",
        "-U",
        database_user(),
        "-d",
        database_name(),
        "-At",
        "-c",
        sql,
    )


def wait_for_cluster_ready() -> None:
    kubectl(
        "wait",
        "--timeout=5m",
        "--namespace",
        namespace(),
        f"cluster/{cluster_name()}",
        "--for=condition=Ready",
    )


def wait_for_primary_pod_recreated(original_pod_uid: str) -> None:
    for _ in range(60):
        pod = primary_pod()
        if pod["metadata"]["uid"] != original_pod_uid and pod_is_ready(pod["metadata"]["name"]):
            return
        time.sleep(5)
    raise AssertionError("database primary pod was not recreated and ready within timeout")


def pod_is_ready(name: str) -> bool:
    pod = kubectl_json("get", "pod", name, "--namespace", namespace(), "-o", "json")
    conditions = pod.get("status", {}).get("conditions", [])
    return any(item.get("type") == "Ready" and item.get("status") == "True" for item in conditions)


def primary_pod_name() -> str:
    return primary_pod()["metadata"]["name"]


def primary_pod() -> dict[str, Any]:
    result = kubectl_json(
        "get",
        "pod",
        "--namespace",
        namespace(),
        "-l",
        f"cnpg.io/cluster={cluster_name()},role=primary",
        "-o",
        "json",
    )
    items = result["items"]
    assert len(items) == 1, items
    return items[0]


def secret_value(secret_name: str, key: str) -> str:
    secret = kubectl_json("get", "secret", secret_name, "--namespace", namespace(), "-o", "json")
    return base64.b64decode(secret["data"][key]).decode("utf-8")


def kubectl_json(*args: str) -> dict[str, Any]:
    result = kubectl(*args)
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict)
    return parsed


def kubectl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def assert_condition(conditions: list[dict[str, Any]], condition_type: str, status: str) -> None:
    condition = next((item for item in conditions if item.get("type") == condition_type), None)
    assert condition is not None, f"missing condition {condition_type!r}"
    assert condition["status"] == status, condition


def repo_root():
    return Path(__file__).resolve().parents[3]


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def cluster_name() -> str:
    return os.environ.get("CLUSTER_POSTGRES_NAME", "study-postgres")


def namespace() -> str:
    return os.environ.get("CLUSTER_POSTGRES_NAMESPACE", "ml-platform-data")


def database_name() -> str:
    return os.environ.get("CLUSTER_POSTGRES_DATABASE", "study_app")


def database_user() -> str:
    return os.environ.get("CLUSTER_POSTGRES_USER", "study_app")
