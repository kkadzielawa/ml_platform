from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PHASE_02_E2E") != "1",
    reason="Phase 2 e2e verification requires a generated e2e report",
)


REPORT_PATH = Path("tests/e2e/phase_02/reports/latest.json")


def test_phase_02_e2e_report_passed_and_contains_evidence_keys() -> None:
    report = load_report()

    assert report["issue"] == "02.15"
    assert report["status"] == "passed"
    assert report["cluster_name"] == "ml-platform-study-dev"
    assert len(report["git_commit"]) == 40
    assert report["evidence"]["signed_fixture_digest"].startswith("sha256:")
    assert report["reports"]["timestamped"].startswith("tests/e2e/phase_02/reports/phase-02-e2e-")


def test_phase_02_e2e_report_includes_required_steps() -> None:
    steps = steps_by_name(load_report())

    for name in [
        "apply_rbac",
        "test_negative_access_checks",
        "apply_secret_backend",
        "apply_oidc_fixture",
        "reset_stale_oidc_rotation_externalsecret",
        "reset_stale_oidc_rotation_secretstore",
        "test_secret_rotation",
        "apply_gitops_reconciliation",
        "test_gitops_reconciliation",
        "sign_fixture",
        "verify_fixture_signature",
        "apply_admission_policy",
        "test_signed_allow_unsigned_deny",
    ]:
        assert steps[name]["returncode"] == 0


def test_phase_02_e2e_report_proves_deny_cases_fail_closed() -> None:
    report = load_report()
    steps = steps_by_name(report)

    assert report["checks"]["deny_cases_fail_closed"] is True
    assert "passed" in steps["test_negative_access_checks"]["stdout_tail"]
    assert "passed" in steps["test_signed_allow_unsigned_deny"]["stdout_tail"]
    assert "passed" in steps["test_secret_rotation"]["stdout_tail"]


def test_phase_02_e2e_report_redacts_local_secret_values() -> None:
    rendered = REPORT_PATH.read_text(encoding="utf-8")

    for forbidden in [
        "local-dev-postgres-password",
        "local-dev-garage-admin-token",
        "local-dev-garage-metrics-token",
        "local-dev-grafana-password",
        "local-dev-harbor-password",
        "local-dev-cluster-postgres-password",
        "local-dev-argocd-oidc-secret",
        "local-dev-forgejo-password",
        "local-dev-woodpecker-agent-secret",
        "local-dev-forgejo-client",
        "local-dev-forgejo-secret",
        "local-dev-woodpecker-server-secret",
        "fixture-build-secret-value",
        "1111111111111111111111111111111111111111111111111111111111111111",
        "2222222222222222222222222222222222222222222222222222222222222222",
    ]:
        assert forbidden not in rendered


def load_report() -> dict:
    assert REPORT_PATH.exists(), f"missing e2e report: {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def steps_by_name(report: dict) -> dict[str, dict]:
    return {step["name"]: step for step in report["steps"]}
