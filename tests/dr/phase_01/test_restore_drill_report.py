from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PHASE_01_RESTORE_DRILL") != "1",
    reason="Phase 1 restore drill verification requires a generated restore drill report",
)


REPORT_PATH = Path("docs/reports/phase-01-restore-drill.json")


def test_restore_drill_report_records_successful_scoped_restore():
    report = load_report()

    assert report["issue"] == "01.12"
    assert report["backup_name"].startswith("phase-01-")
    assert report["restore_name"].startswith("phase-01-restore-drill-")
    assert report["original_resources_untouched"] is True

    kubernetes = report["kubernetes"]
    assert kubernetes["source_namespace"] == "ml-platform-project-housing"
    assert kubernetes["restored_namespace"] == "ml-platform-project-housing-restored-01-12"
    assert kubernetes["restore_pvs"] is False

    restored = {(item["kind"], item["name"], item["namespace"]) for item in kubernetes["resources"]}
    assert ("Deployment", "gateway-echo", "ml-platform-project-housing-restored-01-12") in restored
    assert ("Service", "gateway-echo", "ml-platform-project-housing-restored-01-12") in restored


def test_restore_drill_report_records_matching_sql_and_object_checksums():
    report = load_report()

    assert report["sql"]["restored_table"].endswith("_restored_01_12")
    assert report["sql"]["matches_backup"] is True
    assert report["sql"]["restored_checksum"] == report["sql"]["backup_checksum"]

    assert "/restored-01-12/" in report["object"]["restored_key"]
    assert report["object"]["matches_backup"] is True
    assert report["object"]["restored_checksum"] == report["object"]["backup_checksum"]


def test_restore_drill_report_names_remaining_gaps():
    report = load_report()

    gaps = "\n".join(report["gaps"]).lower()
    assert "whole cluster" in gaps
    assert "secrets" in gaps
    assert "point-in-time database recovery" in gaps
    assert "garage disaster recovery" in gaps


def load_report() -> dict:
    assert REPORT_PATH.exists(), f"missing restore drill report: {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
