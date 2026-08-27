from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_CLUSTER_NAME = "ml-platform-study-dev"
REPORT_DIR = Path(os.environ.get("PHASE_02_E2E_REPORT_DIR", "tests/e2e/phase_02/reports"))
LATEST_REPORT_PATH = REPORT_DIR / "latest.json"
SIGNED_DIGEST_PATH = Path("config/cosign/build-fixture.digest.txt")

DEFAULT_LOCAL_SECRET_VALUES = {
    "local-dev-postgres-password",
    "local-dev-garage-admin-token",
    "local-dev-garage-metrics-token",
    "local-dev-grafana-password",
    "local-dev-harbor-password",
    "local-dev-cluster-postgres-password",
    "local-dev-argocd-oidc-secret",
    "local-dev-openbao-password",
    "local-dev-forgejo-password",
    "local-dev-woodpecker-agent-secret",
    "local-dev-forgejo-client",
    "local-dev-forgejo-secret",
    "local-dev-woodpecker-server-secret",
    "fixture-build-secret-value",
    "1111111111111111111111111111111111111111111111111111111111111111",
    "2222222222222222222222222222222222222222222222222222222222222222",
}
SECRET_ENV_NAMES = {
    "POSTGRES_PASSWORD",
    "GARAGE_RPC_SECRET",
    "GARAGE_ADMIN_TOKEN",
    "GARAGE_METRICS_TOKEN",
    "GARAGE_SECRET_KEY",
    "GRAFANA_ADMIN_PASSWORD",
    "HARBOR_ADMIN_PASSWORD",
    "CLUSTER_POSTGRES_PASSWORD",
    "KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD",
    "KEYCLOAK_DB_PASSWORD",
    "OIDC_ECHO_CLIENT_SECRET",
    "OIDC_ECHO_VIEWER_PASSWORD",
    "OIDC_ECHO_ADMIN_PASSWORD",
    "ARGOCD_OIDC_CLIENT_SECRET",
    "OPENBAO_TOKEN",
    "FORGEJO_ADMIN_PASSWORD",
    "WOODPECKER_AGENT_SECRET",
    "WOODPECKER_FORGEJO_SECRET",
    "WOODPECKER_SECRET",
    "BUILD_FIXTURE_SECRET_VALUE",
}


def main() -> None:
    started = time.monotonic()
    generated_at = datetime.now(timezone.utc)
    timestamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORT_DIR / f"phase-02-e2e-{timestamp}.json"

    report: dict[str, Any] = {
        "issue": "02.15",
        "generated_at": generated_at.isoformat(),
        "cluster_name": expected_cluster_name(),
        "git_commit": git_commit(),
        "status": "running",
        "steps": [],
        "checks": {
            "deny_cases_fail_closed": False,
            "report_contains_no_secret_values": False,
        },
        "evidence": {
            "signed_fixture_digest": None,
            "signed_fixture_digest_source": str(SIGNED_DIGEST_PATH),
        },
        "reports": {
            "timestamped": str(report_path),
            "latest": str(LATEST_REPORT_PATH),
        },
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        assert_expected_cluster_name()
        run_step(report, "apply_rbac", ["make", "apply-rbac"])
        run_step(report, "test_negative_access_checks", ["make", "test-rbac"])
        run_step(report, "apply_secret_backend", ["make", "apply-secrets"])
        run_step(report, "apply_oidc_fixture", ["make", "apply-oidc-fixture"])
        run_step(
            report,
            "reset_stale_oidc_rotation_externalsecret",
            [
                "kubectl",
                "--context",
                f"kind-{expected_cluster_name()}",
                "delete",
                "externalsecret",
                "oidc-echo-test-users",
                "--namespace",
                "ml-platform-system",
                "--ignore-not-found=true",
            ],
        )
        run_step(
            report,
            "reset_stale_oidc_rotation_secretstore",
            [
                "kubectl",
                "--context",
                f"kind-{expected_cluster_name()}",
                "delete",
                "secretstore",
                "openbao-oidc-echo",
                "--namespace",
                "ml-platform-system",
                "--ignore-not-found=true",
            ],
        )
        run_step(report, "test_secret_rotation", ["make", "test-secret-rotation"])
        run_step(report, "apply_gitops_reconciliation", ["make", "apply-gitops"])
        run_step(report, "test_gitops_reconciliation", ["make", "test-gitops"])
        run_step(report, "sign_fixture", ["make", "sign-fixture"])
        report["evidence"]["signed_fixture_digest"] = read_signed_digest()
        run_step(report, "verify_fixture_signature", ["make", "verify-fixture"])
        run_step(report, "apply_admission_policy", ["make", "apply-admission-policy"])
        run_step(report, "test_signed_allow_unsigned_deny", ["make", "test-admission-policy"])

        report["checks"]["deny_cases_fail_closed"] = deny_cases_fail_closed(report)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["checks"]["report_contains_no_secret_values"] = True
        write_report(report, report_path)
        print(f"Phase 2 e2e report written to {report_path}")


def run_step(report: dict[str, Any], name: str, command: list[str]) -> None:
    print(f"[phase-02-e2e] {name}: {' '.join(command)}", flush=True)
    started = time.monotonic()
    result = subprocess.run(
        command,
        env=base_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    step = {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout_tail": tail(result.stdout),
        "stderr_tail": tail(result.stderr),
    }
    report["steps"].append(step)
    if result.stdout:
        sys.stdout.write(redact(result.stdout))
    if result.stderr:
        sys.stderr.write(redact(result.stderr))
    if result.returncode != 0:
        raise RuntimeError(f"step failed: {name}")


def deny_cases_fail_closed(report: dict[str, Any]) -> bool:
    steps = {step["name"]: step for step in report["steps"]}
    rbac = steps["test_negative_access_checks"]["stdout_tail"]
    admission = steps["test_signed_allow_unsigned_deny"]["stdout_tail"]
    rotation = steps["test_secret_rotation"]["stdout_tail"]

    return (
        steps["test_negative_access_checks"]["returncode"] == 0
        and steps["test_signed_allow_unsigned_deny"]["returncode"] == 0
        and steps["test_secret_rotation"]["returncode"] == 0
        and "passed" in rbac
        and "passed" in admission
        and "passed" in rotation
    )


def read_signed_digest() -> str:
    if not SIGNED_DIGEST_PATH.exists():
        raise RuntimeError(f"missing signed fixture digest: {SIGNED_DIGEST_PATH}")
    digest = SIGNED_DIGEST_PATH.read_text(encoding="utf-8").strip()
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"signed fixture digest is not a sha256 digest: {digest!r}")
    return digest


def write_report(report: dict[str, Any], report_path: Path) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    payload = redact(payload)
    report_path.write_text(payload, encoding="utf-8")
    LATEST_REPORT_PATH.write_text(payload, encoding="utf-8")


def tail(value: str, *, max_lines: int = 50) -> str:
    lines = value.splitlines()
    return redact("\n".join(lines[-max_lines:]))


def redact(value: str) -> str:
    redacted = value
    for secret in sorted(secret_values(), key=len, reverse=True):
        redacted = redacted.replace(secret, "<redacted>")
    return redacted


def secret_values() -> set[str]:
    values = set(DEFAULT_LOCAL_SECRET_VALUES)
    values.update(os.environ[name] for name in SECRET_ENV_NAMES if os.environ.get(name))
    return {value for value in values if value}


def git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def assert_expected_cluster_name() -> None:
    if expected_cluster_name() != EXPECTED_CLUSTER_NAME:
        raise RuntimeError(
            f"refusing unexpected cluster name {expected_cluster_name()!r}; "
            f"expected {EXPECTED_CLUSTER_NAME!r}"
        )


def expected_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", EXPECTED_CLUSTER_NAME)


def base_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("KIND_CLUSTER_NAME", EXPECTED_CLUSTER_NAME)
    env["PATH"] = f"{Path.cwd() / '.venv' / 'bin'}:{env.get('PATH', '')}"
    return env


if __name__ == "__main__":
    main()
