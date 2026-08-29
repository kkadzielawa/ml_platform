from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from ml_platform.data import BaselineSchemaError, read_baseline_csv, transform_baseline_rows, write_baseline_parquet_dataset
from ml_platform.data.transforms import TRANSFORMED_COLUMNS


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DATA = REPO_ROOT / "examples/sklearn_baseline/data"
INPUT_PATHS = {
    "train": BASELINE_DATA / "train.csv",
    "test": BASELINE_DATA / "test.csv",
}


def test_baseline_transform_schema_and_row_counts():
    frame = read_baseline_csv(INPUT_PATHS["train"])
    transformed = transform_baseline_rows(frame, split="train")

    assert transformed.columns == TRANSFORMED_COLUMNS
    assert transformed.height == 180
    assert transformed["split"].unique().to_list() == ["train"]
    assert transformed["ingest_date"].dt.to_string("%Y-%m-%d").unique().to_list() == ["2026-08-27"]
    assert set(transformed["home_age_bucket"].unique().to_list()) == {"newer", "established", "older"}


def test_repeated_runs_produce_equivalent_output_and_metadata(tmp_path):
    first = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "first")
    second = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "second")

    comparable_first = without_absolute_paths(first.metadata)
    comparable_second = without_absolute_paths(second.metadata)

    assert comparable_first == comparable_second
    assert first.metadata["row_counts"] == {"test": 60, "train": 180}
    assert first.metadata["total_rows"] == 240
    assert len(first.metadata["output_files"]) == 2


def test_written_parquet_can_be_read_without_loading_entire_dataset_for_count(tmp_path):
    result = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")

    train_path = result.output_dir / "split=train/ingest_date=2026-08-27/part-00000.parquet"
    test_path = result.output_dir / "split=test/ingest_date=2026-08-27/part-00000.parquet"

    assert train_path.exists()
    assert test_path.exists()
    assert pl.scan_parquet(train_path).select(pl.len()).collect().item() == 180
    assert pl.scan_parquet(test_path).select(pl.len()).collect().item() == 60


def test_malformed_schema_fails_before_output_publication(tmp_path):
    malformed = tmp_path / "malformed.csv"
    malformed.write_text(
        "listing_id,listing_price_usd,square_feet\n"
        "listing-0001,250000,1000\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "published"

    with pytest.raises(BaselineSchemaError):
        write_baseline_parquet_dataset({"train": malformed, "test": INPUT_PATHS["test"]}, output_dir)

    assert not output_dir.exists()


def test_metadata_records_counts_hashes_and_checksums(tmp_path):
    result = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))

    assert metadata["schema_hash"].startswith("sha256:")
    assert metadata["metadata_sha256"].startswith("sha256:")
    assert set(metadata["input_checksums"]) == {"test", "train"}
    assert all(value.startswith("sha256:") for value in metadata["input_checksums"].values())
    assert all(item["sha256"].startswith("sha256:") for item in metadata["output_files"])


def without_absolute_paths(metadata: dict) -> dict:
    comparable = dict(metadata)
    return comparable
