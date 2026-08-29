from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
import yaml

from ml_platform.data import write_baseline_parquet_dataset
from ml_platform.data_quality import validate_housing_sale_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DATA = REPO_ROOT / "examples/sklearn_baseline/data"
SUITE_PATH = REPO_ROOT / "config/great_expectations/housing_sale_suite.yaml"
INPUT_PATHS = {
    "train": BASELINE_DATA / "train.csv",
    "test": BASELINE_DATA / "test.csv",
}


def test_great_expectations_suite_is_file_based_and_named():
    suite = yaml.safe_load(SUITE_PATH.read_text(encoding="utf-8"))

    assert suite["suite_name"] == "housing-sale-curated"
    assert suite["dataset_id"] == "housing-sale-features"
    assert {item["id"] for item in suite["expectations"]} == {
        "required-columns",
        "row-count",
        "unique-listing-id",
        "listing-id-format",
        "non-null-required-columns",
        "numeric-ranges",
        "categorical-values",
        "leakage-oriented-feature-names",
    }


def test_good_fixture_passes_and_emits_machine_readable_results(tmp_path):
    dataset = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")

    result = validate_housing_sale_dataset(dataset.output_dir)

    assert result.success is True
    assert result.result["validator"]["name"] == "great-expectations"
    assert result.result["validator"]["version"] == "1.21.0"
    assert result.result["statistics"] == {
        "evaluated_expectations": 8,
        "successful_expectations": 8,
        "failed_expectations": 0,
    }

    output_path = tmp_path / "quality-result.json"
    result.write_json(output_path)
    assert json.loads(output_path.read_text(encoding="utf-8"))["success"] is True


@pytest.mark.parametrize(
    ("defect_name", "expected_failed_expectation"),
    [
        ("duplicate-id", "unique-listing-id"),
        ("null-required", "non-null-required-columns"),
        ("numeric-range", "numeric-ranges"),
        ("bad-category", "categorical-values"),
        ("leakage-column", "leakage-oriented-feature-names"),
    ],
)
def test_seeded_defects_fail_intended_expectation(tmp_path, defect_name: str, expected_failed_expectation: str):
    dataset = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")
    seed_defect(dataset.output_dir, defect_name)

    result = validate_housing_sale_dataset(dataset.output_dir)
    failed_expectations = {
        item["expectation_id"]
        for item in result.result["results"]
        if not item["success"]
    }

    assert result.success is False
    assert expected_failed_expectation in failed_expectations


def test_validation_results_do_not_log_raw_restricted_row_values(tmp_path):
    dataset = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")
    seed_defect(dataset.output_dir, "restricted-raw-value")

    result = validate_housing_sale_dataset(dataset.output_dir)
    serialized = json.dumps(result.result, sort_keys=True)

    assert result.success is False
    assert "restricted@example.local" not in serialized
    assert "listing-0001" not in serialized
    assert "listing-id-format" in serialized
    assert "unexpected_counts" in serialized


def seed_defect(dataset_dir: Path, defect_name: str) -> None:
    parquet_path = dataset_dir / "split=train/ingest_date=2026-08-27/part-00000.parquet"
    frame = pl.read_parquet(parquet_path)

    if defect_name == "duplicate-id":
        frame = frame.with_columns(
            pl.when(pl.arange(0, pl.len()) == 1)
            .then(pl.lit(frame["listing_id"][0]))
            .otherwise(pl.col("listing_id"))
            .alias("listing_id")
        )
    elif defect_name == "null-required":
        frame = frame.with_columns(
            pl.when(pl.arange(0, pl.len()) == 0)
            .then(None)
            .otherwise(pl.col("listing_price_usd"))
            .alias("listing_price_usd")
        )
    elif defect_name == "numeric-range":
        frame = frame.with_columns(
            pl.when(pl.arange(0, pl.len()) == 0)
            .then(pl.lit(9999999))
            .otherwise(pl.col("listing_price_usd"))
            .alias("listing_price_usd")
        )
    elif defect_name == "bad-category":
        frame = frame.with_columns(
            pl.when(pl.arange(0, pl.len()) == 0)
            .then(pl.lit("castle"))
            .otherwise(pl.col("property_type"))
            .alias("property_type")
        )
    elif defect_name == "leakage-column":
        frame = frame.with_columns(pl.col("sold_within_30_days").alias("target_leak"))
    elif defect_name == "restricted-raw-value":
        frame = frame.with_columns(
            pl.when(pl.arange(0, pl.len()) == 0)
            .then(pl.lit("restricted@example.local"))
            .otherwise(pl.col("listing_id"))
            .alias("listing_id")
        )
    else:
        raise AssertionError(f"unknown defect {defect_name}")

    frame.write_parquet(parquet_path, compression="zstd", statistics=True)
