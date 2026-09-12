from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DATA_REPRODUCIBILITY_E2E") != "1",
    reason="requires a lakeFS deployment and is run by make e2e-data-reproducibility",
)


REPORT_PATH = Path(os.environ.get("DATA_REPRODUCIBILITY_REPORT", "/tmp/ml-platform-data-reproducibility/latest.json"))
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_first_curated_release_is_reproduced_by_immutable_lakefs_commit() -> None:
    report = load_report()
    first = report["releases"]["first"]
    second = report["releases"]["second"]
    reproduced = report["reproduction"]

    assert report["issue"] == "03.12"
    assert report["status"] == "passed"
    assert report["table_route"] == "parquet-lakefs"
    assert first["data_commit"] != second["data_commit"]
    assert reproduced["read_ref"] == first["data_commit"]
    assert reproduced["schema"] == first["schema"]
    assert reproduced["row_count"] == first["row_count"]
    assert reproduced["content_checksum"] == first["content_checksum"]
    assert first["content_checksum"] != second["content_checksum"]
    assert all(report["checks"].values())


def test_report_links_run_manifests_and_lineage_events_by_repository_ref_and_path() -> None:
    report = load_report()

    for release in report["releases"].values():
        for evidence_key in ("run_manifest", "lineage_events"):
            evidence = release[evidence_key]
            assert evidence["repository"] == report["repository"]
            assert evidence["ref"] == release["evidence_commit"]
            assert evidence["path"].startswith("evidence/data-reproducibility/runs/")
        assert release["run_manifest"]["path"].endswith("run-manifest.json")
        assert release["lineage_events"]["path"].endswith("openlineage-events.jsonl")


def test_data_reproducibility_report_documents_retained_evidence_option() -> None:
    document = (REPO_ROOT / "docs/reports/data-reproducibility.md").read_text(encoding="utf-8")

    assert "make e2e-data-reproducibility" in document
    assert "KEEP_DATA_REPRODUCIBILITY_REPOSITORY=1" in document
    assert "run manifest" in document.lower()
    assert "lineage" in document.lower()


def load_report() -> dict:
    assert REPORT_PATH.exists(), f"missing data reproducibility report: {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
