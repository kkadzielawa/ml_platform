from __future__ import annotations

import json
from pathlib import Path

import pytest

from components.transform import TransformError, TransformRequest, run_transform_component
from components.transform import transform as transform_module


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DATA = REPO_ROOT / "examples/sklearn_baseline/data"
INPUT_PATHS = {
    "train": BASELINE_DATA / "train.csv",
    "test": BASELINE_DATA / "test.csv",
}
RUN_ID = "run-20260927t120000z-00000001"


def test_repeated_input_and_config_produce_equivalent_content(tmp_path: Path) -> None:
    first = run_transform_component(
        TransformRequest(RUN_ID, INPUT_PATHS, tmp_path / "first", {"format": "parquet"})
    )
    second = run_transform_component(
        TransformRequest(RUN_ID, INPUT_PATHS, tmp_path / "second", {"format": "parquet"})
    )

    first_files = sorted(path.relative_to(first.output_dir) for path in first.output_dir.rglob("*") if path.is_file())
    second_files = sorted(path.relative_to(second.output_dir) for path in second.output_dir.rglob("*") if path.is_file())
    assert first_files == second_files
    for relative_path in first_files:
        assert (first.output_dir / relative_path).read_bytes() == (second.output_dir / relative_path).read_bytes()
    assert first.manifest["config_sha256"] == second.manifest["config_sha256"]
    assert first.manifest["schema_hash"] == second.manifest["schema_hash"]


def test_forced_failure_does_not_publish_partial_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_after_partial_output(input_paths, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "partial.parquet").write_bytes(b"not complete")
        raise RuntimeError("forced transform failure")

    monkeypatch.setattr(transform_module, "write_baseline_parquet_dataset", fail_after_partial_output)
    output_root = tmp_path / "runs"

    with pytest.raises(RuntimeError, match="forced transform failure"):
        run_transform_component(TransformRequest(RUN_ID, INPUT_PATHS, output_root))

    assert not (output_root / RUN_ID).exists()
    assert list(output_root.glob(".*.partial*")) == []


def test_manifest_contains_run_scoped_checksum_and_schema_metadata(tmp_path: Path) -> None:
    result = run_transform_component(TransformRequest(RUN_ID, INPUT_PATHS, tmp_path / "runs"))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["output_uri"] == result.output_dir.resolve().as_uri()

    assert manifest["status"] == "complete"
    assert manifest["run_id"] == RUN_ID
    assert manifest["outputs"]
    assert manifest["schema_hash"].startswith("sha256:")
    assert all(item["sha256"].startswith("sha256:") for item in manifest["outputs"])
    assert result.output_dir == tmp_path / "runs" / RUN_ID / "curated"


def test_invalid_input_fails_before_creating_run_directory(tmp_path: Path) -> None:
    missing_inputs = {"train": tmp_path / "missing.csv"}

    with pytest.raises(TransformError, match="does not exist"):
        run_transform_component(TransformRequest(RUN_ID, missing_inputs, tmp_path / "runs"))

    assert not (tmp_path / "runs").exists()
