"""Automated Phase 3 proof over the deployed study services.

This test intentionally coordinates existing, independently tested Phase 3
components. It does not introduce an orchestrator or rely on browser actions.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ml_platform.ingestion import run_baseline_ingestion
from ml_platform.ingestion.baseline import CURATED_PREFIX, DEFAULT_INPUT_PATHS
from ml_platform.ingestion.lakefs_client import LakeFSClient, LakeFSNotFoundError, lakefs_port_forward
from ml_platform.lineage import InMemoryLineageCollector
from scripts.phase_03.data_reproducibility import delete_repository_if_exists, wait_for_lakefs


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PHASE_03_E2E") != "1",
    reason="requires deployed lakeFS and OpenMetadata and is run by make e2e-phase-03",
)


REPORT_PATH = Path(os.environ.get("PHASE_03_E2E_REPORT", "/tmp/ml-platform-phase-03/latest.json"))
REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_SECRET_VALUES = {
    "local-dev-openmetadata-admin-password",
    "local-dev-cluster-postgres-password",
    "lakefs-admin-secret-033333333333333333333333333333333333333333",
}


def test_phase_three_versioned_data_path() -> None:
    """Run good/bad ingestion plus snapshot, catalog, lineage, and old-read proofs."""

    report: dict[str, Any] = {
        "issue": "03.13",
        "status": "running",
        "generated_at": datetime.now(UTC).isoformat(),
        "steps": [],
        "checks": {},
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        good_and_bad = exercise_live_ingestion_paths()
        report["steps"].append({"name": "ingest_good_transform_quality_lineage", "status": "passed", **good_and_bad["good"]})
        report["steps"].append({"name": "reject_bad_before_commit", "status": "passed", **good_and_bad["bad"]})
        run_make_step(report, "snapshot_read_by_commit", ["make", "test-table-route"])
        run_make_step(
            report,
            "catalog_owner_quality_and_lineage",
            ["make", "test-openmetadata"],
            extra_env={"RUN_OPENMETADATA_INTEGRATION": "1"},
        )
        reproduction_report = REPORT_PATH.with_name("data-reproducibility.json")
        run_make_step(
            report,
            "reproduce_old_curated_release",
            ["make", "e2e-data-reproducibility"],
            extra_env={"DATA_REPRODUCIBILITY_REPORT": str(reproduction_report)},
        )
        reproduction = json.loads(reproduction_report.read_text(encoding="utf-8"))
        assert reproduction["status"] == "passed"
        assert all(reproduction["checks"].values())
        report["checks"] = {
            "good_ingestion_committed_after_transform_and_quality": True,
            "bad_input_rejected_without_curated_commit": True,
            "lineage_emits_start_complete_and_sanitized_fail": True,
            "snapshot_read_by_commit": step_passed(report, "snapshot_read_by_commit"),
            "catalog_owner_quality_and_lineage": step_passed(report, "catalog_owner_quality_and_lineage"),
            "old_release_reproduced": True,
        }
        report["reproducibility_report"] = str(reproduction_report)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        write_report(report)


def exercise_live_ingestion_paths() -> dict[str, dict[str, Any]]:
    """Exercise the actual lakeFS-backed success and validation failure paths."""

    good_repository = f"study-phase-03-good-{uuid.uuid4().hex[:12]}"
    bad_repository = f"study-phase-03-bad-{uuid.uuid4().hex[:12]}"
    client = LakeFSClient.from_environment()
    with tempfile.TemporaryDirectory(prefix="ml-platform-phase-03-") as temporary_directory:
        work_dir = Path(temporary_directory)
        good_manifest_path = work_dir / "good-manifest.json"
        malformed_train = work_dir / "malformed-train.csv"
        malformed_train.write_text(
            "listing_id,listing_price_usd,square_feet\nlisting-0001,425000,1000\n",
            encoding="utf-8",
        )
        valid_test = work_dir / "test.csv"
        shutil.copyfile(DEFAULT_INPUT_PATHS["test"], valid_test)
        good_collector = InMemoryLineageCollector()
        bad_collector = InMemoryLineageCollector()

        with lakefs_port_forward():
            wait_for_lakefs(client)
            client.setup()
            try:
                good_result = run_baseline_ingestion(
                    repository=good_repository,
                    output_manifest_path=good_manifest_path,
                    client=client,
                    lineage_collector=good_collector,
                )
                good_manifest = json.loads(good_manifest_path.read_text(encoding="utf-8"))
                assert good_result.no_op is False
                assert good_result.lakefs_commit_id
                assert good_collector.event_types() == ["START", "COMPLETE"]
                metadata = json.loads(
                    client.get_object(good_repository, good_result.lakefs_commit_id, f"{CURATED_PREFIX}/_metadata.json")
                )
                assert metadata["total_rows"] == 240
                assert good_manifest["artifacts"]["outputs"][0]["data_revision"]["id"] == good_result.lakefs_commit_id

                with pytest.raises(ValueError):
                    run_baseline_ingestion(
                        input_paths={"train": malformed_train, "test": valid_test},
                        repository=bad_repository,
                        output_manifest_path=work_dir / "bad-manifest.json",
                        client=client,
                        lineage_collector=bad_collector,
                    )
                assert bad_collector.event_types() == ["START", "FAIL"]
                assert not (work_dir / "bad-manifest.json").exists()
                with pytest.raises(LakeFSNotFoundError):
                    client.get_object(bad_repository, "main", f"{CURATED_PREFIX}/_metadata.json")
                failure_events = json.dumps(bad_collector.events, sort_keys=True)
                assert "listing-0001" not in failure_events
                assert "425000" not in failure_events

                return {
                    "good": {
                        "repository": good_repository,
                        "data_commit": good_result.lakefs_commit_id,
                        "run_id": good_result.run_id,
                        "curated_row_count": metadata["total_rows"],
                        "lineage_events": good_collector.event_types(),
                    },
                    "bad": {
                        "repository": bad_repository,
                        "committed": False,
                        "manifest_written": False,
                        "lineage_events": bad_collector.event_types(),
                    },
                }
            finally:
                delete_repository_if_exists(client, good_repository)
                delete_repository_if_exists(client, bad_repository)


def run_make_step(
    report: dict[str, Any],
    name: str,
    command: list[str],
    *,
    extra_env: dict[str, str] | None = None,
) -> None:
    """Run a prior component's public target and retain only redacted compact evidence."""

    environment = os.environ.copy()
    environment["PATH"] = f"{REPO_ROOT / '.venv' / 'bin'}:{environment.get('PATH', '')}"
    environment.update(extra_env or {})
    result = subprocess.run(command, cwd=REPO_ROOT, env=environment, capture_output=True, text=True, check=False)
    record = {
        "name": name,
        "command": command,
        "returncode": result.returncode,
        "stdout_tail": redact(tail(result.stdout)),
        "stderr_tail": redact(tail(result.stderr)),
    }
    report["steps"].append(record)
    if result.returncode != 0:
        raise AssertionError(f"Phase 3 step failed: {name}")


def step_passed(report: dict[str, Any], name: str) -> bool:
    return next(step for step in report["steps"] if step["name"] == name)["returncode"] == 0


def write_report(report: dict[str, Any]) -> None:
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tail(value: str, *, max_lines: int = 25) -> str:
    return "\n".join(value.splitlines()[-max_lines:])


def redact(value: str) -> str:
    redacted = value
    for secret in sorted(LOCAL_SECRET_VALUES, key=len, reverse=True):
        redacted = redacted.replace(secret, "<redacted>")
    return redacted
