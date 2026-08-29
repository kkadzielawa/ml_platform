"""Great Expectations-style validation for local Parquet datasets.

The project pins Great Expectations as the selected 03.07.a route and keeps the
suite format aligned with GE expectation names. The checks here intentionally
emit compact machine-readable summaries and never include raw failing row values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import great_expectations as gx
import polars as pl
import yaml


DEFAULT_SUITE_PATH = Path("config/great_expectations/housing_sale_suite.yaml")


@dataclass(frozen=True)
class DataQualityResult:
    """Machine-readable data-quality result."""

    success: bool
    result: dict[str, Any]

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{json.dumps(self.result, indent=2, sort_keys=True)}\n", encoding="utf-8")


def validate_housing_sale_dataset(dataset_dir: Path, *, suite_path: Path = DEFAULT_SUITE_PATH) -> DataQualityResult:
    """Validate the curated housing-sale Parquet dataset."""

    return validate_parquet_dataset(dataset_dir, suite_path=suite_path)


def validate_parquet_dataset(dataset_dir: Path, *, suite_path: Path) -> DataQualityResult:
    """Validate a local Parquet dataset from a file-based expectation suite."""

    suite = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
    frame = read_partitioned_parquet(dataset_dir)
    expectation_results = [evaluate_expectation(frame, expectation) for expectation in suite["expectations"]]
    success = all(item["success"] for item in expectation_results)
    result = {
        "schema_version": "1.0.0",
        "validator": {
            "route": "03.07.a",
            "name": "great-expectations",
            "version": gx.__version__,
        },
        "suite_name": suite["suite_name"],
        "dataset_id": suite["dataset_id"],
        "dataset_dir": str(dataset_dir),
        "success": success,
        "statistics": {
            "evaluated_expectations": len(expectation_results),
            "successful_expectations": sum(1 for item in expectation_results if item["success"]),
            "failed_expectations": sum(1 for item in expectation_results if not item["success"]),
        },
        "results": expectation_results,
    }
    return DataQualityResult(success=success, result=result)


def evaluate_expectation(frame: pl.DataFrame, expectation: dict[str, Any]) -> dict[str, Any]:
    expectation_type = expectation["expectation_type"]
    kwargs = expectation["kwargs"]
    evaluators = {
        "expect_table_columns_to_match_ordered_list": expect_table_columns_to_match_ordered_list,
        "expect_table_row_count_to_be_between": expect_table_row_count_to_be_between,
        "expect_column_values_to_be_unique": expect_column_values_to_be_unique,
        "expect_column_values_to_match_regex": expect_column_values_to_match_regex,
        "expect_column_values_to_not_be_null": expect_column_values_to_not_be_null,
        "expect_column_values_to_be_between": expect_column_values_to_be_between,
        "expect_column_values_to_be_in_set": expect_column_values_to_be_in_set,
        "expect_feature_names_to_avoid_target_leakage_terms": expect_feature_names_to_avoid_target_leakage_terms,
    }
    success, summary = evaluators[expectation_type](frame, kwargs)
    return {
        "expectation_id": expectation["id"],
        "expectation_type": expectation_type,
        "success": success,
        "summary": summary,
    }


def read_partitioned_parquet(dataset_dir: Path) -> pl.DataFrame:
    parquet_files = sorted(dataset_dir.glob("**/*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"no parquet files found under {dataset_dir}")

    frames = [pl.read_parquet(path) for path in parquet_files]
    return pl.concat(frames, how="diagonal_relaxed")


def expect_table_columns_to_match_ordered_list(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    expected_columns = kwargs["column_list"]
    actual_columns = frame.columns
    return actual_columns == expected_columns, {
        "expected_column_count": len(expected_columns),
        "actual_column_count": len(actual_columns),
        "missing_columns": sorted(set(expected_columns) - set(actual_columns)),
        "unexpected_columns": sorted(set(actual_columns) - set(expected_columns)),
    }


def expect_table_row_count_to_be_between(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    row_count = frame.height
    min_value = kwargs["min_value"]
    max_value = kwargs["max_value"]
    return min_value <= row_count <= max_value, {
        "row_count": row_count,
        "min_value": min_value,
        "max_value": max_value,
    }


def expect_column_values_to_be_unique(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    column = kwargs["column"]
    duplicate_count = frame.height - frame.select(pl.col(column).n_unique()).item()
    return duplicate_count == 0, {
        "column": column,
        "duplicate_count": duplicate_count,
    }


def expect_column_values_to_match_regex(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    column = kwargs["column"]
    mismatch_count = frame.filter(~pl.col(column).cast(pl.String).str.contains(kwargs["regex"])).height
    return mismatch_count == 0, {
        "column": column,
        "unexpected_count": mismatch_count,
    }


def expect_column_values_to_not_be_null(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    null_counts = {
        column: frame.select(pl.col(column).is_null().sum()).item()
        for column in kwargs["columns"]
    }
    return all(count == 0 for count in null_counts.values()), {
        "columns_checked": sorted(null_counts),
        "null_counts": null_counts,
    }


def expect_column_values_to_be_between(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    failures = {}
    for column, limits in kwargs["ranges"].items():
        min_value = limits["min_value"]
        max_value = limits["max_value"]
        count = frame.filter((pl.col(column) < min_value) | (pl.col(column) > max_value)).height
        if count:
            failures[column] = count
    return not failures, {
        "columns_checked": sorted(kwargs["ranges"]),
        "unexpected_counts": failures,
    }


def expect_column_values_to_be_in_set(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    failures = {}
    for column, allowed_values in kwargs["value_sets"].items():
        count = frame.filter(~pl.col(column).is_in(allowed_values)).height
        if count:
            failures[column] = count
    return not failures, {
        "columns_checked": sorted(kwargs["value_sets"]),
        "unexpected_counts": failures,
    }


def expect_feature_names_to_avoid_target_leakage_terms(frame: pl.DataFrame, kwargs: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    target_column = kwargs["target_column"]
    forbidden_terms = kwargs["forbidden_terms"]
    feature_columns = [column for column in frame.columns if column != target_column]
    offending_columns = [
        column
        for column in feature_columns
        if any(term in column for term in forbidden_terms)
    ]
    return not offending_columns, {
        "feature_column_count": len(feature_columns),
        "offending_columns": offending_columns,
    }
