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
REPORT_DIR = Path(os.environ.get("PHASE_01_E2E_REPORT_DIR", "tests/e2e/phase_01/reports"))
LATEST_REPORT_PATH = REPORT_DIR / "latest.json"
DEFAULT_LOCAL_SECRET_VALUES = {
    "local-dev-postgres-password",
    "local-dev-garage-admin-token",
    "local-dev-grafana-password",
    "local-dev-harbor-password",
    "local-dev-cluster-postgres-password",
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
}


def main() -> None:
    started = time.monotonic()
    generated_at = datetime.now(timezone.utc)
    timestamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORT_DIR / f"phase-01-e2e-{timestamp}.json"

    report: dict[str, Any] = {
        "issue": "01.13",
        "generated_at": generated_at.isoformat(),
        "cluster_name": expected_cluster_name(),
        "status": "running",
        "steps": [],
        "reports": {
            "timestamped": str(report_path),
            "latest": str(LATEST_REPORT_PATH),
        },
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        assert_expected_cluster_name()
        report["safe_delete_guard"] = verify_delete_refuses_unexpected_cluster_name(report)

        run_step(report, "delete_existing_exact_cluster", ["bash", "scripts/cluster/delete-kind.sh"])
        run_step(report, "create_cluster_from_absent_state", ["make", "cluster-create"])
        run_step(report, "apply_tls_foundation", ["make", "apply-tls"])
        run_step(report, "apply_network_policies", ["make", "apply-network-policy"])
        run_step(report, "test_network_policies", ["make", "test-network-policy"])
        run_step(report, "apply_postgres", ["make", "apply-postgres"])
        run_step(report, "test_postgres_persistence", ["make", "test-cluster-postgres"])
        run_step(report, "apply_object_storage", ["make", "apply-object-storage"])
        run_step(report, "test_object_storage_persistence", ["make", "test-cluster-object-storage"])
        run_step(report, "backup_and_restore_fixture", ["make", "restore-drill-phase-01"])
        run_step(report, "delete_exact_cluster_after_drill", ["bash", "scripts/cluster/delete-kind.sh"])
        run_step(report, "confirm_cluster_absent", ["bash", "scripts/cluster/delete-kind.sh"])

        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_report(report, report_path)
        print(f"Phase 1 e2e report written to {report_path}")


def verify_delete_refuses_unexpected_cluster_name(report: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    env = base_env()
    env["KIND_CLUSTER_NAME"] = "not-the-study-cluster"
    result = subprocess.run(
        ["bash", "scripts/cluster/delete-kind.sh"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    record = {
        "name": "delete_guard_refuses_unexpected_cluster_name",
        "command": "KIND_CLUSTER_NAME=not-the-study-cluster bash scripts/cluster/delete-kind.sh",
        "expected_failure": True,
        "returncode": result.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "stdout_tail": tail(result.stdout),
        "stderr_tail": tail(result.stderr),
    }
    report["steps"].append(record)
    if result.returncode == 0:
        raise RuntimeError("cluster delete guard accepted an unexpected cluster name")
    if "refusing unexpected cluster name" not in result.stderr:
        raise RuntimeError("cluster delete guard failed for the wrong reason")
    return {
        "unexpected_cluster_name_refused": True,
        "validated_by_step": record["name"],
    }


def run_step(report: dict[str, Any], name: str, command: list[str]) -> None:
    print(f"[phase-01-e2e] {name}: {' '.join(command)}", flush=True)
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


def write_report(report: dict[str, Any], report_path: Path) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    report_path.write_text(payload, encoding="utf-8")
    LATEST_REPORT_PATH.write_text(payload, encoding="utf-8")


def tail(value: str, *, max_lines: int = 40) -> str:
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
