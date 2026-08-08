"""Generate the Phase 0 baseline housing-sale classification fixture."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from pathlib import Path


DATASET_NAME = "synthetic-housing-sale-classifier"
DATASET_VERSION = "v0001"
SEED = 20260808
TOTAL_ROWS = 240
TRAIN_ROWS = 180
TEST_ROWS = 60
FEATURE_COLUMNS = [
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
]
TARGET_COLUMN = "sold_within_30_days"
CSV_COLUMNS = ["listing_id", *FEATURE_COLUMNS, TARGET_COLUMN]
PROPERTY_TYPES = ["condo", "townhouse", "single-family"]
MARKET_TEMPERATURES = ["cool", "balanced", "hot"]
PROPERTY_BIAS = {
    "condo": 0.05,
    "townhouse": 0.12,
    "single-family": 0.0,
}
MARKET_BIAS = {
    "cool": -0.65,
    "balanced": 0.0,
    "hot": 0.65,
}


def main() -> None:
    write_dataset(Path(__file__).parent)


def write_dataset(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = generate_rows()
    train_rows, test_rows = split_rows(rows)

    train_path = output_dir / "train.csv"
    test_path = output_dir / "test.csv"
    metadata_path = output_dir / "metadata.json"

    write_csv(train_path, train_rows)
    write_csv(test_path, test_rows)
    write_json(metadata_path, build_metadata(train_rows, test_rows, train_path, test_path))


def generate_rows() -> list[dict[str, str]]:
    rng = random.Random(SEED)
    rows = []
    for row_number in range(1, TOTAL_ROWS + 1):
        property_type = weighted_choice(rng, [("condo", 0.28), ("townhouse", 0.22), ("single-family", 0.50)])
        market_temperature = weighted_choice(rng, [("cool", 0.28), ("balanced", 0.44), ("hot", 0.28)])
        bedrooms = rng.choices([1, 2, 3, 4, 5], weights=[0.08, 0.24, 0.38, 0.22, 0.08], k=1)[0]
        bathrooms = rng.choices([1.0, 1.5, 2.0, 2.5, 3.0, 3.5], weights=[0.10, 0.14, 0.32, 0.24, 0.14, 0.06], k=1)[0]
        square_feet = int(round(rng.gauss(780 + bedrooms * 430 + bathrooms * 115, 190) / 10) * 10)
        square_feet = clamp(square_feet, 650, 3600)
        home_age_years = rng.randint(0, 95)
        school_rating = clamp(int(round(rng.gauss(6.2, 1.8))), 1, 10)
        walk_score = clamp(int(round(rng.gauss(56, 22))), 5, 98)
        mortgage_rate_percent = round(rng.uniform(5.2, 8.4), 2)

        base_price_per_square_foot = {
            "condo": 260,
            "townhouse": 245,
            "single-family": 235,
        }[property_type]
        price_per_square_foot = (
            base_price_per_square_foot
            + school_rating * 11
            + walk_score * 0.9
            - home_age_years * 0.55
            + rng.gauss(0, 28)
        )
        listing_price_usd = int(round((square_feet * price_per_square_foot) / 1000) * 1000)
        listing_price_usd = clamp(listing_price_usd, 160_000, 1_250_000)

        affordability_pressure = (listing_price_usd / square_feet - 305) / 85
        quality_signal = (school_rating - 6) / 2.2 + (walk_score - 55) / 35
        financing_pressure = (mortgage_rate_percent - 6.5) / 1.25
        age_pressure = (home_age_years - 35) / 35
        score = (
            0.95 * quality_signal
            - 1.05 * affordability_pressure
            - 0.55 * financing_pressure
            - 0.35 * age_pressure
            + PROPERTY_BIAS[property_type]
            + MARKET_BIAS[market_temperature]
            + rng.gauss(0, 0.55)
        )
        probability = 1.0 / (1.0 + math.exp(-score))
        sold_within_30_days = int(rng.random() < probability)

        rows.append(
            {
                "listing_id": f"listing-{row_number:04d}",
                "listing_price_usd": str(listing_price_usd),
                "square_feet": str(square_feet),
                "bedrooms": str(bedrooms),
                "bathrooms": format_float(bathrooms),
                "home_age_years": str(home_age_years),
                "school_rating": str(school_rating),
                "walk_score": str(walk_score),
                "mortgage_rate_percent": format_float(mortgage_rate_percent),
                "property_type": property_type,
                "market_temperature": market_temperature,
                "sold_within_30_days": str(sold_within_30_days),
            }
        )
    return rows


def split_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    shuffled_rows = list(rows)
    random.Random(SEED + 1).shuffle(shuffled_rows)
    train_ids = {row["listing_id"] for row in shuffled_rows[:TRAIN_ROWS]}
    train_rows = [row for row in rows if row["listing_id"] in train_ids]
    test_rows = [row for row in rows if row["listing_id"] not in train_ids]
    return train_rows, test_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_metadata(train_rows: list[dict[str, str]], test_rows: list[dict[str, str]], train_path: Path, test_path: Path):
    majority_class = most_common_target(train_rows)
    baseline_accuracy = sum(row[TARGET_COLUMN] == majority_class for row in test_rows) / len(test_rows)
    return {
        "schema_version": "1.0.0",
        "dataset": {
            "name": DATASET_NAME,
            "version": DATASET_VERSION,
            "license": "CC0-1.0",
            "provenance": "Generated by examples/sklearn_baseline/data/generate_dataset.py; no external source data.",
            "source_url": "https://github.com/kkadzielawa/ml_platform/tree/main/examples/sklearn_baseline",
        },
        "generation": {
            "seed": SEED,
            "algorithm": "stdlib-random synthetic housing-sale binary classification fixture",
            "script": "examples/sklearn_baseline/data/generate_dataset.py",
            "target_rule": "A deterministic pseudo-random sale probability combines listing-time price, home attributes, local quality signals, financing pressure, property type, and market temperature.",
        },
        "schema": {
            "columns": CSV_COLUMNS,
            "feature_columns": FEATURE_COLUMNS,
            "identifier_column": "listing_id",
            "target_column": TARGET_COLUMN,
            "target_meaning": {
                "0": "listing did not sell within 30 days",
                "1": "listing sold within 30 days",
            },
            "target_values": ["0", "1"],
        },
        "split": {
            "method": "deterministic seeded shuffle",
            "seed": SEED + 1,
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
        },
        "expected_baseline": {
            "type": "majority_class",
            "train_majority_class": majority_class,
            "test_accuracy": round(baseline_accuracy, 6),
        },
        "checksums": {
            "train_csv_sha256": sha256_file(train_path),
            "test_csv_sha256": sha256_file(test_path),
        },
    }


def write_json(path: Path, payload) -> None:
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def weighted_choice(rng: random.Random, weighted_values: list[tuple[str, float]]) -> str:
    values, weights = zip(*weighted_values)
    return rng.choices(values, weights=weights, k=1)[0]


def most_common_target(rows: list[dict[str, str]]) -> str:
    counts = {"0": 0, "1": 0}
    for row in rows:
        counts[row[TARGET_COLUMN]] += 1
    return max(counts, key=lambda label: (counts[label], label))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def format_float(value: float) -> str:
    return f"{value:.2f}"


if __name__ == "__main__":
    main()
