from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PHASE_01_BACKUP_VERIFY") != "1",
    reason="Phase 1 backup verification requires a running kind cluster and Velero backup",
)


EXPECTED_NAMESPACES = {
    "ml-platform-system",
    "ml-platform-data",
    "ml-platform-observability",
    "ml-platform-project-housing",
}


def test_latest_phase_01_backup_completed_and_has_expected_scope():
    backup = latest_phase_01_backup()

    assert backup["metadata"]["labels"]["ml-platform.local/phase"] == "01"
    assert backup["metadata"]["labels"]["ml-platform.local/backup-scope"] == "phase-01"
    assert backup["status"]["phase"] == "Completed"

    spec = backup["spec"]
    assert set(spec["includedNamespaces"]) == EXPECTED_NAMESPACES
    assert spec["storageLocation"] == "default"
    assert spec["snapshotVolumes"] is False
    assert spec["defaultVolumesToFsBackup"] is False
    assert "secrets" in spec["excludedResources"]
    assert "events" in spec["excludedResources"]


def test_backup_storage_location_is_garage_and_writable():
    location = kubectl_json(
        "get",
        "backupstoragelocation",
        "default",
        "--namespace",
        velero_namespace(),
        "-o",
        "json",
    )

    assert location["spec"]["provider"] == "aws"
    assert location["spec"]["objectStorage"]["bucket"] == garage_bucket()
    assert location["spec"]["objectStorage"]["prefix"] == "velero/phase-01"
    assert location["spec"]["config"]["s3ForcePathStyle"] == "true"
    assert location["spec"]["config"]["s3Url"] == "http://garage-s3.ml-platform-data.svc.cluster.local:3900"
    assert location["status"]["phase"] == "Available"


def test_velero_logs_do_not_expose_local_secret_values():
    logs = kubectl(
        "logs",
        "--namespace",
        velero_namespace(),
        "deployment/velero",
        "--since=30m",
    ).stdout

    forbidden_values = {
        value
        for value in [
            os.environ.get("GARAGE_SECRET_KEY"),
            os.environ.get("GARAGE_KEY_ID"),
            os.environ.get("HARBOR_ADMIN_PASSWORD"),
            os.environ.get("CLUSTER_POSTGRES_PASSWORD"),
        ]
        if value
    }
    for forbidden in forbidden_values:
        assert forbidden not in logs


def latest_phase_01_backup() -> dict[str, Any]:
    backup_name_file = Path(os.environ.get("BACKUP_NAME_FILE", "/tmp/ml-platform-phase-01-backup-name"))
    if backup_name_file.exists():
        name = backup_name_file.read_text().strip()
        return kubectl_json("get", "backups.velero.io", name, "--namespace", velero_namespace(), "-o", "json")

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
    assert backups, "no Phase 1 backups found"
    return sorted(backups, key=lambda item: item["metadata"]["creationTimestamp"])[-1]


def kubectl_json(*args: str) -> dict[str, Any]:
    parsed = json.loads(kubectl(*args).stdout)
    assert isinstance(parsed, dict)
    return parsed


def kubectl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def velero_namespace() -> str:
    return os.environ.get("VELERO_NAMESPACE", "velero")


def garage_bucket() -> str:
    return os.environ.get("GARAGE_BUCKET", "ml-platform-artifacts")
