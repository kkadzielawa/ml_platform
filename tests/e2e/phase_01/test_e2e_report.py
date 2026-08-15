from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PHASE_01_E2E") != "1",
    reason="Phase 1 e2e verification requires a generated e2e report",
)


REPORT_PATH = Path("tests/e2e/phase_01/reports/latest.json")


def test_phase_01_e2e_report_passed_and_started_from_absent_cluster():
    report = load_report()

    assert report["issue"] == "01.13"
    assert report["status"] == "passed"
    assert report["cluster_name"] == "ml-platform-study-dev"
    assert report["reports"]["timestamped"].startswith("tests/e2e/phase_01/reports/phase-01-e2e-")

    steps = steps_by_name(report)
    assert steps["delete_existing_exact_cluster"]["returncode"] == 0
    assert steps["create_cluster_from_absent_state"]["returncode"] == 0
    assert steps["confirm_cluster_absent"]["returncode"] == 0


def test_phase_01_e2e_report_includes_required_smokes():
    report = load_report()
    steps = steps_by_name(report)

    for name in [
        "apply_tls_foundation",
        "apply_network_policies",
        "test_network_policies",
        "apply_postgres",
        "test_postgres_persistence",
        "apply_object_storage",
        "test_object_storage_persistence",
        "backup_and_restore_fixture",
    ]:
        assert steps[name]["returncode"] == 0

    assert "3 passed" in steps["backup_and_restore_fixture"]["stdout_tail"]


def test_phase_01_e2e_report_proves_safe_deletion_guard_and_cleanup():
    report = load_report()
    steps = steps_by_name(report)

    assert report["safe_delete_guard"]["unexpected_cluster_name_refused"] is True
    assert steps["delete_guard_refuses_unexpected_cluster_name"]["returncode"] != 0
    assert "refusing unexpected cluster name" in steps["delete_guard_refuses_unexpected_cluster_name"]["stderr_tail"]

    assert steps["delete_exact_cluster_after_drill"]["returncode"] == 0
    assert steps["confirm_cluster_absent"]["returncode"] == 0
    assert "does not exist" in steps["confirm_cluster_absent"]["stdout_tail"]


def test_phase_01_e2e_report_redacts_local_secret_values():
    rendered = REPORT_PATH.read_text(encoding="utf-8")

    for forbidden in [
        "local-dev-postgres-password",
        "local-dev-garage-admin-token",
        "local-dev-grafana-password",
        "local-dev-harbor-password",
        "local-dev-cluster-postgres-password",
        "1111111111111111111111111111111111111111111111111111111111111111",
        "2222222222222222222222222222222222222222222222222222222222222222",
    ]:
        assert forbidden not in rendered


def load_report() -> dict:
    assert REPORT_PATH.exists(), f"missing e2e report: {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def steps_by_name(report: dict) -> dict[str, dict]:
    return {step["name"]: step for step in report["steps"]}
