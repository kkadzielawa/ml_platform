import csv
import hashlib
import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "examples" / "sklearn_baseline" / "data"
TRAIN_PATH = DATA_DIR / "train.csv"
TEST_PATH = DATA_DIR / "test.csv"
METADATA_PATH = DATA_DIR / "metadata.json"
GENERATOR_PATH = DATA_DIR / "generate_dataset.py"
EXPECTED_COLUMNS = [
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
CATEGORICAL_COLUMNS = ["property_type", "market_temperature"]
TARGET_COLUMN = "sold_within_30_days"


def test_baseline_dataset_schema_and_metadata():
    train_rows = read_csv(TRAIN_PATH)
    test_rows = read_csv(TEST_PATH)
    metadata = read_json(METADATA_PATH)

    assert len(train_rows) == 180
    assert len(test_rows) == 60
    assert list(train_rows[0]) == EXPECTED_COLUMNS
    assert list(test_rows[0]) == EXPECTED_COLUMNS

    assert metadata["dataset"]["name"] == "synthetic-housing-sale-classifier"
    assert metadata["dataset"]["version"] == "v0001"
    assert metadata["dataset"]["license"] == "CC0-1.0"
    assert metadata["generation"]["seed"] == 20260808
    assert metadata["schema"]["columns"] == EXPECTED_COLUMNS
    assert metadata["schema"]["feature_columns"] == FEATURE_COLUMNS
    assert metadata["schema"]["identifier_column"] == "listing_id"
    assert metadata["schema"]["target_column"] == TARGET_COLUMN
    assert metadata["split"]["train_rows"] == len(train_rows)
    assert metadata["split"]["test_rows"] == len(test_rows)
    assert metadata["checksums"]["train_csv_sha256"] == sha256_file(TRAIN_PATH)
    assert metadata["checksums"]["test_csv_sha256"] == sha256_file(TEST_PATH)


def test_baseline_dataset_is_deterministic(tmp_path):
    generator = load_generator()
    generator.write_dataset(tmp_path)

    for filename in ["train.csv", "test.csv", "metadata.json"]:
        assert (tmp_path / filename).read_text(encoding="utf-8") == (DATA_DIR / filename).read_text(encoding="utf-8")


def test_baseline_split_has_no_overlap_and_preserves_classes():
    train_rows = read_csv(TRAIN_PATH)
    test_rows = read_csv(TEST_PATH)

    train_ids = {row["listing_id"] for row in train_rows}
    test_ids = {row["listing_id"] for row in test_rows}

    assert train_ids.isdisjoint(test_ids)
    assert {row[TARGET_COLUMN] for row in train_rows} == {"0", "1"}
    assert {row[TARGET_COLUMN] for row in test_rows} == {"0", "1"}


def test_baseline_features_are_human_interpretable_and_valid():
    rows = [*read_csv(TRAIN_PATH), *read_csv(TEST_PATH)]

    assert {row["property_type"] for row in rows} == {"condo", "townhouse", "single-family"}
    assert {row["market_temperature"] for row in rows} == {"cool", "balanced", "hot"}

    for row in rows:
        assert 160_000 <= int(row["listing_price_usd"]) <= 1_250_000
        assert 650 <= int(row["square_feet"]) <= 3600
        assert 1 <= int(row["bedrooms"]) <= 5
        assert 1.0 <= float(row["bathrooms"]) <= 3.5
        assert 0 <= int(row["home_age_years"]) <= 95
        assert 1 <= int(row["school_rating"]) <= 10
        assert 0 <= int(row["walk_score"]) <= 100
        assert 5.0 <= float(row["mortgage_rate_percent"]) <= 8.5
        assert row[TARGET_COLUMN] in {"0", "1"}


def test_baseline_data_has_no_obvious_target_leakage():
    rows = [*read_csv(TRAIN_PATH), *read_csv(TEST_PATH)]
    targets = [row[TARGET_COLUMN] for row in rows]
    leakage_terms = ["target", "label", "sold", "sale", "closed", "days_on_market"]

    for column in FEATURE_COLUMNS:
        assert all(term not in column for term in leakage_terms)
        values = [row[column] for row in rows]
        assert values != targets
        assert invert_binary(values) != targets

    for column in CATEGORICAL_COLUMNS:
        values_to_targets = {}
        for row in rows:
            values_to_targets.setdefault(row[column], set()).add(row[TARGET_COLUMN])
        assert all(targets_for_value == {"0", "1"} for targets_for_value in values_to_targets.values())


def test_majority_class_baseline_matches_metadata():
    train_rows = read_csv(TRAIN_PATH)
    test_rows = read_csv(TEST_PATH)
    metadata = read_json(METADATA_PATH)

    majority_class = most_common_target(train_rows)
    accuracy = sum(row[TARGET_COLUMN] == majority_class for row in test_rows) / len(test_rows)

    assert metadata["expected_baseline"]["type"] == "majority_class"
    assert metadata["expected_baseline"]["train_majority_class"] == majority_class
    assert metadata["expected_baseline"]["test_accuracy"] == round(accuracy, 6)


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_generator():
    spec = importlib.util.spec_from_file_location("baseline_data_generator", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invert_binary(values):
    if set(values) <= {"0", "1"}:
        return ["1" if value == "0" else "0" for value in values]
    return []


def most_common_target(rows):
    counts = {"0": 0, "1": 0}
    for row in rows:
        counts[row[TARGET_COLUMN]] += 1
    return max(counts, key=lambda label: (counts[label], label))
