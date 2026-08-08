# sklearn baseline dataset

This example contains the Phase 0 baseline tabular classification fixture for the local classic-ML vertical slice.

## Dataset

- Name: `synthetic-housing-sale-classifier`
- Version: `v0001`
- Task: predict whether a housing listing will sell within 30 days
- Files: `data/train.csv`, `data/test.csv`, and `data/metadata.json`
- Generation script: `data/generate_dataset.py`
- Seed: `20260808`
- Split: deterministic seeded shuffle with 180 training rows and 60 test rows

## License and provenance

The dataset is generated synthetic data with no external source records and no personal data. It is documented as `CC0-1.0` in `data/metadata.json` so later training issues can treat it as redistributable study data.

The records are fictional housing listings. They are meant to be plausible enough for study, not representative of a real housing market.

## Schema

| Column | Role | Type | Notes |
|---|---|---|---|
| `listing_id` | identifier | string | Stable row identifier, excluded from model features. |
| `listing_price_usd` | feature | integer | Asking price at listing time. |
| `square_feet` | feature | integer | Interior size of the home. |
| `bedrooms` | feature | integer | Bedroom count. |
| `bathrooms` | feature | float | Bathroom count. |
| `home_age_years` | feature | integer | Approximate age of the home. |
| `school_rating` | feature | integer | Synthetic local school quality score from 1 to 10. |
| `walk_score` | feature | integer | Synthetic walkability score from 0 to 100. |
| `mortgage_rate_percent` | feature | float | Synthetic prevailing mortgage rate at listing time. |
| `property_type` | feature | categorical string | One of `condo`, `townhouse`, or `single-family`. |
| `market_temperature` | feature | categorical string | One of `cool`, `balanced`, or `hot`. |
| `sold_within_30_days` | target | integer-like string | Binary label: `0` means no, `1` means yes. |

## Expected baseline

The expected baseline is a majority-class classifier trained on `data/train.csv` and evaluated on `data/test.csv`. The exact majority class and test accuracy are recorded in `data/metadata.json`.

Later issues own model training, feature transformations, MLflow logging, packaging, and serving.
