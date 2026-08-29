"""Deterministic transforms for the Phase 0 housing-sale fixture."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import duckdb
import polars as pl


DATASET_ID = "housing-sale-features"
DATASET_VERSION = "v0001"
INGEST_DATE = "2026-08-27"
PARTITION_COLUMNS = ("split", "ingest_date")

SOURCE_COLUMNS = [
    "listing_id",
    "listing_price_usd",
    "square_feet",
    "bedrooms",
    "bathrooms",
    "home_age_years",
    "school_rating",
    "walk_score",
    "mortgage_rate_percent",
    "property_type",
    "market_temperature",
    "sold_within_30_days",
]

TRANSFORMED_COLUMNS = [
    "listing_id",
    "split",
    "ingest_date",
    "listing_price_usd",
    "square_feet",
    "price_per_square_foot",
    "bedrooms",
    "bathrooms",
    "home_age_years",
    "home_age_bucket",
    "school_rating",
    "walk_score",
    "mortgage_rate_percent",
    "property_type",
    "market_temperature",
    "sold_within_30_days",
]

SOURCE_SCHEMA = {
    "listing_id": pl.String,
    "listing_price_usd": pl.Int64,
    "square_feet": pl.Int64,
    "bedrooms": pl.Int64,
    "bathrooms": pl.Float64,
    "home_age_years": pl.Int64,
    "school_rating": pl.Int64,
    "walk_score": pl.Int64,
    "mortgage_rate_percent": pl.Float64,
    "property_type": pl.String,
    "market_temperature": pl.String,
    "sold_within_30_days": pl.Int64,
}

TRANSFORMED_SCHEMA = {
    "listing_id": pl.String,
    "split": pl.String,
    "ingest_date": pl.Date,
    "listing_price_usd": pl.Int64,
    "square_feet": pl.Int64,
    "price_per_square_foot": pl.Float64,
    "bedrooms": pl.Int64,
    "bathrooms": pl.Float64,
    "home_age_years": pl.Int64,
    "home_age_bucket": pl.String,
    "school_rating": pl.Int64,
    "walk_score": pl.Int64,
    "mortgage_rate_percent": pl.Float64,
    "property_type": pl.String,
    "market_temperature": pl.String,
    "sold_within_30_days": pl.Int64,
}


class BaselineSchemaError(ValueError):
    """Raised when the baseline fixture schema is malformed."""


@dataclass(frozen=True)
class DatasetTransformResult:
    """Summary of a deterministic dataset transform."""

    output_dir: Path
    metadata_path: Path
    metadata: dict


def read_baseline_csv(path: Path) -> pl.DataFrame:
    """Read the baseline CSV fixture with explicit types."""

    return pl.read_csv(path, schema_overrides=SOURCE_SCHEMA)


def validate_baseline_schema(frame: pl.DataFrame) -> None:
    """Validate the expected source columns and dtypes before publishing output."""

    if frame.columns != SOURCE_COLUMNS:
        raise BaselineSchemaError(f"expected columns {SOURCE_COLUMNS}, got {frame.columns}")

    for column, expected_dtype in SOURCE_SCHEMA.items():
        actual_dtype = frame.schema[column]
        if actual_dtype != expected_dtype:
            raise BaselineSchemaError(f"expected {column} to be {expected_dtype}, got {actual_dtype}")

    invalid_targets = frame.filter(~pl.col("sold_within_30_days").is_in([0, 1]))
    if invalid_targets.height:
        raise BaselineSchemaError("sold_within_30_days must contain only 0 or 1")

    invalid_property_types = frame.filter(~pl.col("property_type").is_in(["condo", "townhouse", "single-family"]))
    if invalid_property_types.height:
        raise BaselineSchemaError("property_type contains unsupported values")

    invalid_market_temperatures = frame.filter(~pl.col("market_temperature").is_in(["cool", "balanced", "hot"]))
    if invalid_market_temperatures.height:
        raise BaselineSchemaError("market_temperature contains unsupported values")


def transform_baseline_rows(frame: pl.DataFrame, *, split: str) -> pl.DataFrame:
    """Create a deterministic curated feature table for one split."""

    validate_baseline_schema(frame)

    return (
        frame.sort("listing_id")
        .with_columns(
            pl.lit(split).alias("split"),
            pl.lit(INGEST_DATE).str.strptime(pl.Date, "%Y-%m-%d").alias("ingest_date"),
            (pl.col("listing_price_usd") / pl.col("square_feet")).round(6).alias("price_per_square_foot"),
            pl.when(pl.col("home_age_years") <= 10)
            .then(pl.lit("newer"))
            .when(pl.col("home_age_years") <= 40)
            .then(pl.lit("established"))
            .otherwise(pl.lit("older"))
            .alias("home_age_bucket"),
        )
        .select(TRANSFORMED_COLUMNS)
    )


def write_baseline_parquet_dataset(input_paths: Mapping[str, Path], output_dir: Path) -> DatasetTransformResult:
    """Read baseline CSV splits, validate them, and publish deterministic Parquet plus metadata."""

    source_frames = {split: read_baseline_csv(path) for split, path in sorted(input_paths.items())}
    for frame in source_frames.values():
        validate_baseline_schema(frame)

    transformed_frames = {split: transform_baseline_rows(frame, split=split) for split, frame in source_frames.items()}
    schema_hash = transformed_schema_hash()
    input_checksums = {split: prefixed_sha256(path) for split, path in sorted(input_paths.items())}

    tmp_dir = output_dir.with_name(f".{output_dir.name}.tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    output_files = []
    row_counts = {}
    try:
        for split, frame in transformed_frames.items():
            partition_dir = tmp_dir / f"split={split}" / f"ingest_date={INGEST_DATE}"
            partition_dir.mkdir(parents=True, exist_ok=True)
            parquet_path = partition_dir / "part-00000.parquet"
            frame.write_parquet(parquet_path, compression="zstd", statistics=True)

            relative_path = parquet_path.relative_to(tmp_dir).as_posix()
            row_count = parquet_row_count(parquet_path)
            row_counts[split] = row_count
            output_files.append(
                {
                    "path": relative_path,
                    "rows": row_count,
                    "sha256": prefixed_sha256(parquet_path),
                }
            )

        metadata = build_metadata(input_checksums, output_files, row_counts, schema_hash)
        metadata_path = tmp_dir / "_metadata.json"
        metadata_path.write_text(f"{json.dumps(metadata, indent=2, sort_keys=True)}\n", encoding="utf-8")
        metadata["metadata_sha256"] = prefixed_sha256(metadata_path)
        metadata_path.write_text(f"{json.dumps(metadata, indent=2, sort_keys=True)}\n", encoding="utf-8")

        if output_dir.exists():
            shutil.rmtree(output_dir)
        tmp_dir.rename(output_dir)
    except Exception:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        raise

    return DatasetTransformResult(
        output_dir=output_dir,
        metadata_path=output_dir / "_metadata.json",
        metadata=json.loads((output_dir / "_metadata.json").read_text(encoding="utf-8")),
    )


def build_metadata(input_checksums: dict[str, str], output_files: list[dict], row_counts: dict[str, int], schema_hash: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "dataset_id": DATASET_ID,
        "version": DATASET_VERSION,
        "format": "parquet",
        "partition_columns": list(PARTITION_COLUMNS),
        "row_counts": row_counts,
        "total_rows": sum(row_counts.values()),
        "schema_hash": schema_hash,
        "input_checksums": input_checksums,
        "output_files": sorted(output_files, key=lambda item: item["path"]),
    }


def transformed_schema_hash() -> str:
    payload = [
        {"name": column, "dtype": str(TRANSFORMED_SCHEMA[column])}
        for column in TRANSFORMED_COLUMNS
    ]
    return prefixed_sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def parquet_row_count(path: Path) -> int:
    with duckdb.connect(database=":memory:") as connection:
        return connection.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]


def prefixed_sha256(path: Path) -> str:
    return prefixed_sha256_bytes(path.read_bytes())


def prefixed_sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"
