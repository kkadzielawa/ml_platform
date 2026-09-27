from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from components.validate import (
    QUALITY_GATE_FAILURE_EXIT_CODE,
    ImmutableDatasetReference,
    QualityGateFailure,
    ValidationError,
    run_validation_component,
)
from ml_platform.data import write_baseline_parquet_dataset


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DATA = REPO_ROOT / "examples/sklearn_baseline/data"
SUITE_PATH = REPO_ROOT / "config/great_expectations/housing_sale_suite.yaml"
INPUT_PATHS = {
    "train": BASELINE_DATA / "train.csv",
    "test": BASELINE_DATA / "test.csv",
}


def test_good_fixture_publishes_passing_aggregate_report(tmp_path: Path) -> None:
    dataset = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")
    report_path = tmp_path / "reports" / "quality.json"

    result = run_validation_component(
        ImmutableDatasetReference(
            repository="housing-sale-ingestion",
            commit_id="c0ffee1234567890",
            dataset_path=dataset.output_dir,
            dataset_path_in_store="curated/housing-sale/v0001",
        ),
        suite_path=SUITE_PATH,
        report_path=report_path,
    )

    assert result.success is True
    assert result.report["status"] == "passed"
    assert result.report["reference"]["commit_id"] == "c0ffee1234567890"
    assert result.report["statistics"]["failed_expectations"] == 0
    assert json.loads(report_path.read_text(encoding="utf-8"))["quality_gate"] == "passed"


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
def test_seeded_bad_fixture_publishes_failure_report(
    tmp_path: Path,
    defect_name: str,
    expected_failed_expectation: str,
) -> None:
    dataset = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")
    seed_defect(dataset.output_dir, defect_name)
    report_path = tmp_path / "reports" / f"{defect_name}.json"

    with pytest.raises(QualityGateFailure) as raised:
        run_validation_component(
            ImmutableDatasetReference(
                repository="housing-sale-ingestion",
                commit_id="c0ffee1234567890",
                dataset_path=dataset.output_dir,
            ),
            suite_path=SUITE_PATH,
            report_path=report_path,
        )

    assert raised.value.exit_code == QUALITY_GATE_FAILURE_EXIT_CODE
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert expected_failed_expectation in {
        item["expectation_id"] for item in report["results"] if not item["success"]
    }


def test_report_contains_no_restricted_row_values(tmp_path: Path) -> None:
    dataset = write_baseline_parquet_dataset(INPUT_PATHS, tmp_path / "dataset")
    parquet_path = dataset.output_dir / "split=train/ingest_date=2026-08-27/part-00000.parquet"
    frame = pl.read_parquet(parquet_path).with_columns(
        pl.when(pl.arange(0, pl.len()) == 0)
        .then(pl.lit("restricted@example.local"))
        .otherwise(pl.col("listing_id"))
        .alias("listing_id")
    )
    frame.write_parquet(parquet_path, compression="zstd", statistics=True)
    report_path = tmp_path / "report.json"

    with pytest.raises(QualityGateFailure):
        run_validation_component(
            ImmutableDatasetReference("housing-sale-ingestion", "c0ffee1234567890", dataset.output_dir),
            suite_path=SUITE_PATH,
            report_path=report_path,
        )

    serialized = report_path.read_text(encoding="utf-8")
    assert "restricted@example.local" not in serialized
    assert "listing-id-format" in serialized


def test_invalid_reference_fails_before_report_publication(tmp_path: Path) -> None:
    report_path = tmp_path / "reports" / "quality.json"

    with pytest.raises(ValidationError, match="commit_id"):
        run_validation_component(
            ImmutableDatasetReference("housing-sale-ingestion", "", tmp_path / "missing"),
            suite_path=SUITE_PATH,
            report_path=report_path,
        )

    assert not report_path.exists()
    assert not report_path.parent.exists()


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
            .then(pl.lit(9_999_999))
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
    else:
        raise AssertionError(f"unknown defect {defect_name}")
    frame.write_parquet(parquet_path, compression="zstd", statistics=True)
