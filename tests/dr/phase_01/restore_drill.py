from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.integration.object_store.smoke_s3 import request


REPORT_PATH = Path("docs/reports/phase-01-restore-drill.json")
SOURCE_NAMESPACE = "ml-platform-project-housing"
RESTORED_NAMESPACE = "ml-platform-project-housing-restored-01-12"
RESTORE_LABEL_SELECTOR = "ml-platform.local/restore-drill=phase-01"
SQL_ROW_ID = "phase-01-restore-drill"
SQL_SOURCE_TABLE = "public.restore_drill_fixture"
SQL_RESTORED_TABLE = "public.restore_drill_fixture_restored_01_12"
OBJECT_SOURCE_KEY = "restore-drill/source/phase-01-restore-drill.txt"
OBJECT_RESTORED_KEY = "restore-drill/restored-01-12/phase-01-restore-drill.txt"
OBJECT_BODY = b"phase 1 restore drill object fixture\n"


def main() -> None:
    started = time.monotonic()
    generated_at = datetime.now(timezone.utc).isoformat()

    original_deployment = kubectl_json(
        "get",
        "deployment",
        "gateway-echo",
        "--namespace",
        SOURCE_NAMESPACE,
        "-o",
        "json",
    )
    original_uid = original_deployment["metadata"]["uid"]
    backup_name = latest_completed_backup_name()

    restore_name = restore_namespace_from_velero_backup(backup_name)
    restored_resources = restored_namespace_resources()
    sql_result = restore_sql_fixture()
    object_result = restore_object_fixture()

    original_after = kubectl_json(
        "get",
        "deployment",
        "gateway-echo",
        "--namespace",
        SOURCE_NAMESPACE,
        "-o",
        "json",
    )

    report = {
        "generated_at": generated_at,
        "issue": "01.12",
        "backup_name": backup_name,
        "restore_name": restore_name,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "original_resources_untouched": original_after["metadata"]["uid"] == original_uid,
        "kubernetes": {
            "source_namespace": SOURCE_NAMESPACE,
            "restored_namespace": RESTORED_NAMESPACE,
            "restore_pvs": False,
            "resources": restored_resources,
        },
        "sql": sql_result,
        "object": object_result,
        "gaps": [
            "This drill restores a scoped namespace, not the whole cluster.",
            "Kubernetes Secrets remain excluded from the Velero backup and restore.",
            "The SQL check restores a fixture row into a suffixed table; it is not point-in-time database recovery.",
            "The object check restores a fixture object into a suffixed key; it is not native Garage disaster recovery.",
            "Harbor image blob recovery is not exercised by this drill.",
        ],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Phase 1 restore drill report written to {REPORT_PATH}")


def latest_completed_backup_name() -> str:
    backup_name_file = Path(os.environ.get("BACKUP_NAME_FILE", "/tmp/ml-platform-phase-01-backup-name"))
    if backup_name_file.exists():
        name = backup_name_file.read_text(encoding="utf-8").strip()
        backup = kubectl_json("get", "backups.velero.io", name, "--namespace", velero_namespace(), "-o", "json")
        if backup.get("status", {}).get("phase") == "Completed":
            return name

    backups = kubectl_json(
        "get",
        "backups.velero.io",
        "--namespace",
        velero_namespace(),
        "-l",
        "ml-platform.local/phase=01,ml-platform.local/backup-scope=phase-01",
        "-o",
        "json",
    )["items"]
    completed = [item for item in backups if item.get("status", {}).get("phase") == "Completed"]
    if not completed:
        raise RuntimeError("No completed Phase 1 Velero backup found")
    return sorted(completed, key=lambda item: item["metadata"]["creationTimestamp"])[-1]["metadata"]["name"]


def restore_namespace_from_velero_backup(backup_name: str) -> str:
    kubectl("delete", "namespace", RESTORED_NAMESPACE, "--ignore-not-found=true")
    wait_for_namespace_deleted(RESTORED_NAMESPACE)

    restore_name = f"phase-01-restore-drill-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    manifest = f"""
apiVersion: velero.io/v1
kind: Restore
metadata:
  name: {restore_name}
  namespace: {velero_namespace()}
  labels:
    ml-platform.local/phase: "01"
    ml-platform.local/restore-drill: phase-01
spec:
  backupName: {backup_name}
  includedNamespaces:
    - {SOURCE_NAMESPACE}
  namespaceMapping:
    {SOURCE_NAMESPACE}: {RESTORED_NAMESPACE}
  excludedResources:
    - events
    - events.events.k8s.io
    - secrets
  restorePVs: false
"""
    kubectl("create", "-f", "-", input_text=manifest)

    for _ in range(120):
        restore = kubectl_json("get", "restores.velero.io", restore_name, "--namespace", velero_namespace(), "-o", "json")
        phase = restore.get("status", {}).get("phase")
        if phase == "Completed":
            kubectl(
                "wait",
                "--timeout=3m",
                "--namespace",
                RESTORED_NAMESPACE,
                "deployment/gateway-echo",
                "--for=condition=Available",
            )
            return restore_name
        if phase in {"Failed", "PartiallyFailed"}:
            raise RuntimeError(json.dumps(restore.get("status", {}), indent=2, sort_keys=True))
        time.sleep(5)

    restore = kubectl_json("get", "restores.velero.io", restore_name, "--namespace", velero_namespace(), "-o", "json")
    raise TimeoutError(f"Timed out waiting for Velero restore {restore_name}: {restore.get('status', {})}")


def restored_namespace_resources() -> list[dict[str, str]]:
    resources = []
    for kind in ["deployments", "services", "httproutes.gateway.networking.k8s.io", "resourcequotas", "limitranges"]:
        items = kubectl_json("get", kind, "--namespace", RESTORED_NAMESPACE, "-o", "json")["items"]
        for item in items:
            resources.append(
                {
                    "kind": item["kind"],
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                }
            )
    return sorted(resources, key=lambda item: (item["kind"], item["name"]))


def restore_sql_fixture() -> dict[str, Any]:
    payload = "phase 1 restore drill sql fixture"
    payload_checksum = sha256_text(payload)

    psql(
        f"""
CREATE TABLE IF NOT EXISTS {SQL_SOURCE_TABLE} (
  id text PRIMARY KEY,
  payload text NOT NULL,
  checksum text NOT NULL
);
INSERT INTO {SQL_SOURCE_TABLE} (id, payload, checksum)
VALUES ({sql_literal(SQL_ROW_ID)}, {sql_literal(payload)}, {sql_literal(payload_checksum)})
ON CONFLICT (id) DO UPDATE
SET payload = EXCLUDED.payload, checksum = EXCLUDED.checksum;
DROP TABLE IF EXISTS {SQL_RESTORED_TABLE};
CREATE TABLE {SQL_RESTORED_TABLE} (LIKE {SQL_SOURCE_TABLE} INCLUDING ALL);
"""
    )

    backup_row = psql(
        f"""
SELECT id || E'\\t' || payload || E'\\t' || checksum
FROM {SQL_SOURCE_TABLE}
WHERE id = {sql_literal(SQL_ROW_ID)};
"""
    ).stdout.strip()
    backup_checksum = sha256_text(backup_row + "\n")
    row_id, restored_payload, restored_payload_checksum = backup_row.split("\t")

    psql(
        f"""
INSERT INTO {SQL_RESTORED_TABLE} (id, payload, checksum)
VALUES ({sql_literal(row_id)}, {sql_literal(restored_payload)}, {sql_literal(restored_payload_checksum)});
"""
    )
    restored_row = psql(
        f"""
SELECT id || E'\\t' || payload || E'\\t' || checksum
FROM {SQL_RESTORED_TABLE}
WHERE id = {sql_literal(SQL_ROW_ID)};
"""
    ).stdout.strip()
    restored_checksum = sha256_text(restored_row + "\n")

    return {
        "database": database_name(),
        "source_table": SQL_SOURCE_TABLE,
        "restored_table": SQL_RESTORED_TABLE,
        "row_id": SQL_ROW_ID,
        "backup_checksum": backup_checksum,
        "restored_checksum": restored_checksum,
        "matches_backup": restored_checksum == backup_checksum,
    }


def restore_object_fixture() -> dict[str, Any]:
    with garage_port_forward():
        s3_request("PUT", OBJECT_SOURCE_KEY, body=OBJECT_BODY)
        backup_bytes = s3_request("GET", OBJECT_SOURCE_KEY)
        backup_checksum = sha256_bytes(backup_bytes)
        s3_request("PUT", OBJECT_RESTORED_KEY, body=backup_bytes)
        restored_bytes = s3_request("GET", OBJECT_RESTORED_KEY)
        restored_checksum = sha256_bytes(restored_bytes)

    return {
        "bucket": garage_bucket(),
        "source_key": OBJECT_SOURCE_KEY,
        "restored_key": OBJECT_RESTORED_KEY,
        "backup_checksum": backup_checksum,
        "restored_checksum": restored_checksum,
        "matches_backup": restored_checksum == backup_checksum,
    }


def psql(sql: str) -> subprocess.CompletedProcess[str]:
    password = secret_value(f"{cluster_postgres_name()}-app", "password")
    return kubectl(
        "exec",
        primary_pod_name(),
        "--namespace",
        cluster_postgres_namespace(),
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
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        sql,
    )


def primary_pod_name() -> str:
    pods = kubectl_json(
        "get",
        "pod",
        "--namespace",
        cluster_postgres_namespace(),
        "-l",
        f"cnpg.io/cluster={cluster_postgres_name()},role=primary",
        "-o",
        "json",
    )["items"]
    if len(pods) != 1:
        raise RuntimeError(f"Expected one primary pod, found {len(pods)}")
    return pods[0]["metadata"]["name"]


def secret_value(secret_name: str, key: str) -> str:
    secret = kubectl_json("get", "secret", secret_name, "--namespace", cluster_postgres_namespace(), "-o", "json")
    return base64.b64decode(secret["data"][key]).decode("utf-8")


def s3_request(method: str, key: str, *, body: bytes = b"") -> bytes:
    return request(
        method,
        garage_endpoint(),
        garage_bucket(),
        key,
        garage_key_id(),
        garage_secret_key(),
        garage_region(),
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
            garage_namespace(),
            "svc/garage-s3",
            f"{garage_local_port()}:3900",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_local_port(garage_local_port())
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for_local_port(port: int) -> None:
    for _ in range(60):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise RuntimeError(f"Port-forward did not open 127.0.0.1:{port}")


def wait_for_namespace_deleted(namespace: str) -> None:
    for _ in range(60):
        result = kubectl("get", "namespace", namespace, check=False)
        if result.returncode != 0:
            return
        time.sleep(2)
    raise TimeoutError(f"Namespace {namespace} was not deleted within timeout")


def kubectl_json(*args: str) -> dict[str, Any]:
    result = kubectl(*args)
    parsed = json.loads(result.stdout)
    if not isinstance(parsed, dict):
        raise TypeError(f"Expected JSON object from kubectl, got {type(parsed)}")
    return parsed


def kubectl(*args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args],
        input=input_text,
        check=check,
        capture_output=True,
        text=True,
    )


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def velero_namespace() -> str:
    return os.environ.get("VELERO_NAMESPACE", "velero")


def cluster_postgres_name() -> str:
    return os.environ.get("CLUSTER_POSTGRES_NAME", "study-postgres")


def cluster_postgres_namespace() -> str:
    return os.environ.get("CLUSTER_POSTGRES_NAMESPACE", "ml-platform-data")


def database_name() -> str:
    return os.environ.get("CLUSTER_POSTGRES_DATABASE", "study_app")


def database_user() -> str:
    return os.environ.get("CLUSTER_POSTGRES_USER", "study_app")


def garage_namespace() -> str:
    return os.environ.get("CLUSTER_GARAGE_NAMESPACE", "ml-platform-data")


def garage_local_port() -> int:
    return int(os.environ.get("CLUSTER_GARAGE_PORT", "13900"))


def garage_endpoint() -> str:
    return f"http://127.0.0.1:{garage_local_port()}"


def garage_bucket() -> str:
    return os.environ.get("GARAGE_BUCKET", "ml-platform-artifacts")


def garage_key_id() -> str:
    return os.environ.get("GARAGE_KEY_ID", "GK111111111111111111111111")


def garage_secret_key() -> str:
    return os.environ.get("GARAGE_SECRET_KEY", "2222222222222222222222222222222222222222222222222222222222222222")


def garage_region() -> str:
    return os.environ.get("GARAGE_S3_REGION", "garage")


if __name__ == "__main__":
    main()
