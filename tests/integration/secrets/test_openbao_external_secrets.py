from __future__ import annotations

import base64
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SECRETS_INTEGRATION") != "1",
    reason="secrets integration tests require OpenBao and External Secrets in the kind cluster",
)


TARGET_SECRET = "housing-database-credential"
SECRET_STORE = "openbao-housing"
EXTERNAL_SECRET = "housing-database-credential"
UNAUTHORIZED_SA = "unauthorized-secret-reader"


def test_openbao_and_external_secrets_are_ready():
    pod = kubectl_json("get", "pod", "openbao-0", "--namespace", openbao_namespace(), "-o", "json")
    assert_condition(pod["status"]["conditions"], "Ready", "True")

    for deployment in ("external-secrets", "external-secrets-webhook", "external-secrets-cert-controller"):
        item = kubectl_json("get", "deployment", deployment, "--namespace", openbao_namespace(), "-o", "json")
        assert item["status"].get("availableReplicas") == 1


def test_external_secret_syncs_scoped_database_credential_from_openbao():
    store = kubectl_json("get", "secretstore", SECRET_STORE, "--namespace", example_namespace(), "-o", "json")
    external = kubectl_json("get", "externalsecret", EXTERNAL_SECRET, "--namespace", example_namespace(), "-o", "json")
    target = kubectl_json("get", "secret", TARGET_SECRET, "--namespace", example_namespace(), "-o", "json")

    assert_condition(store["status"]["conditions"], "Ready", "True")
    assert_condition(external["status"]["conditions"], "Ready", "True")

    synced = {key: decode_secret_value(target, key) for key in ("username", "password", "database")}
    source = openbao_secret()
    assert synced == {
        "username": source["username"],
        "password": source["password"],
        "database": source["database"],
    }


def test_secret_value_is_absent_from_git_and_rendered_manifests():
    password = decode_secret_value(
        kubectl_json("get", "secret", TARGET_SECRET, "--namespace", example_namespace(), "-o", "json"),
        "password",
    )
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in (repo_root() / "clusters/dev/secrets").glob("*.yaml"))
    rendered += "\n"
    rendered += "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            repo_root() / "platform/charts/openbao",
            repo_root() / "platform/charts/external-secrets",
        )
        for path in path.glob("*.yaml")
    )

    assert len(password) >= 32
    assert password not in rendered


def test_unauthorized_service_account_cannot_read_synced_or_provider_token_secrets():
    subject = f"system:serviceaccount:{example_namespace()}:{UNAUTHORIZED_SA}"

    assert not can_i(subject, "get", f"secret/{TARGET_SECRET}", namespace=example_namespace())
    assert not can_i(subject, "get", "secret/openbao-housing-reader-token", namespace=example_namespace())


def openbao_secret() -> dict[str, str]:
    root_token = decode_secret_value(
        kubectl_json("get", "secret", "openbao-bootstrap", "--namespace", openbao_namespace(), "-o", "json"),
        "root-token",
    )
    result = kubectl(
        "exec",
        "--namespace",
        openbao_namespace(),
        "openbao-0",
        "--",
        "sh",
        "-ec",
        f"BAO_TOKEN={root_token!r} bao kv get -format=json kv/projects/housing/database/study-reader",
    )
    payload = json.loads(result.stdout)
    data = payload["data"]["data"]
    return {key: str(data[key]) for key in ("username", "password", "database")}


def can_i(subject: str, verb: str, resource: str, *, namespace: str) -> bool:
    result = subprocess.run(
        [
            "kubectl",
            "--context",
            f"kind-{kind_cluster_name()}",
            "auth",
            "can-i",
            verb,
            resource,
            "--namespace",
            namespace,
            "--as",
            subject,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode in {0, 1}, result.stderr
    answer = result.stdout.strip()
    assert answer in {"yes", "no"}, result.stdout
    return answer == "yes"


def decode_secret_value(secret: dict[str, Any], key: str) -> str:
    return base64.b64decode(secret["data"][key]).decode("utf-8")


def assert_condition(conditions: list[dict[str, Any]], condition_type: str, status: str) -> None:
    condition = next((item for item in conditions if item.get("type") == condition_type), None)
    assert condition is not None, f"missing condition {condition_type!r}"
    assert condition["status"] == status, condition


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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def openbao_namespace() -> str:
    return os.environ.get("OPENBAO_NAMESPACE", "ml-platform-system")


def example_namespace() -> str:
    return os.environ.get("SECRETS_EXAMPLE_NAMESPACE", "ml-platform-project-housing")
