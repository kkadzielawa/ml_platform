from __future__ import annotations

from pathlib import Path

from ml_platform.data import write_baseline_parquet_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATHS = {
    "train": REPO_ROOT / "examples/sklearn_baseline/data/train.csv",
    "test": REPO_ROOT / "examples/sklearn_baseline/data/test.csv",
}
OUTPUT_DIR = REPO_ROOT / "examples/data_transform/output/housing-sale-features"


def main() -> None:
    result = write_baseline_parquet_dataset(INPUT_PATHS, OUTPUT_DIR)
    print(f"wrote {result.output_dir}")
    print(f"metadata {result.metadata_path}")
    print(f"rows {result.metadata['total_rows']}")


if __name__ == "__main__":
    main()
