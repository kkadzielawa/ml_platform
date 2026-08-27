from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
RETENTION_CONFIGMAP = REPO_ROOT / "clusters/dev/data-storage/retention-configmap.yaml"
RETENTION_DOC = REPO_ROOT / "docs/data/retention.md"


def test_retention_policy_is_conservative_and_non_destructive():
    policy = load_policy()

    lifecycle = policy["lifecycle"]
    assert lifecycle["simulation_only"] is True
    assert lifecycle["destructive_delete_enabled"] is False

    for scope, rule in lifecycle["rules"].items():
        assert rule["bucket"].startswith("ml-platform-")
        assert rule["prefix"].startswith("projects/ml-platform/")
        assert rule["review_after_days"] > 0
        assert rule["protected_prefixes"], f"{scope} must protect current fixture prefixes"
        for prefix in rule["protected_prefixes"]:
            assert prefix.startswith(rule["prefix"])


def test_supported_and_unsupported_encryption_modes_are_explicit():
    policy = load_policy()
    encryption = policy["encryption"]

    assert encryption["supported"]["sse_c"]["status"] == "supported"
    assert encryption["supported"]["client_side_encryption"]["status"] == "supported"
    assert encryption["unsupported"]["sse_s3"]["status"] == "unsupported"
    assert encryption["unsupported"]["sse_kms"]["status"] == "unsupported"
    assert "server-managed" in encryption["unsupported"]["sse_s3"]["reason"]
    assert "KMS" in encryption["unsupported"]["sse_kms"]["reason"]


def test_non_destructive_expiry_simulation_protects_current_fixtures():
    policy = load_policy()
    now = dt.date(2026, 8, 27)

    current_fixtures = [
        inventory_object("raw", "projects/ml-platform/raw/smoke/current.txt", days_old=900, now=now),
        inventory_object("curated", "projects/ml-platform/curated/fixtures/current.parquet", days_old=900, now=now),
        inventory_object("artifacts", "projects/ml-platform/artifacts/manifests/current.json", days_old=1200, now=now),
        inventory_object("models", "projects/ml-platform/models/housing-sale-baseline/model.pkl", days_old=1200, now=now),
        inventory_object("evaluation", "projects/ml-platform/evaluation/smoke/current.json", days_old=900, now=now),
    ]

    decisions = [simulate_expiry(policy, item, now) for item in current_fixtures]

    assert {decision["action"] for decision in decisions} == {"protect"}
    assert all(decision["delete_call_issued"] is False for decision in decisions)


def test_non_destructive_expiry_simulation_selects_old_disposable_objects():
    policy = load_policy()
    now = dt.date(2026, 8, 27)

    old_scratch_objects = [
        inventory_object("raw", "projects/ml-platform/raw/scratch/old.csv", days_old=366, now=now),
        inventory_object("curated", "projects/ml-platform/curated/scratch/old.parquet", days_old=731, now=now),
        inventory_object("artifacts", "projects/ml-platform/artifacts/scratch/old.json", days_old=1096, now=now),
        inventory_object("evaluation", "projects/ml-platform/evaluation/scratch/old.json", days_old=731, now=now),
    ]

    decisions = [simulate_expiry(policy, item, now) for item in old_scratch_objects]

    assert {decision["action"] for decision in decisions} == {"would-expire"}
    assert all(decision["delete_call_issued"] is False for decision in decisions)


def test_models_are_reviewed_but_never_automatically_expired():
    policy = load_policy()
    now = dt.date(2026, 8, 27)
    model_object = inventory_object("models", "projects/ml-platform/models/experimental/scratch/model.pkl", days_old=9999, now=now)

    decision = simulate_expiry(policy, model_object, now)

    assert decision["action"] == "review"
    assert decision["delete_call_issued"] is False


def test_documentation_records_unsupported_backend_features():
    text = RETENTION_DOC.read_text(encoding="utf-8")

    assert "SSE-S3" in text
    assert "SSE-KMS" in text
    assert "Do not emulate unsupported encryption" in text
    assert "No S3 `DELETE` call is issued" in text


def load_policy() -> dict[str, Any]:
    manifest = yaml.safe_load(RETENTION_CONFIGMAP.read_text(encoding="utf-8"))
    return yaml.safe_load(manifest["data"]["retention.yaml"])


def inventory_object(scope: str, key: str, *, days_old: int, now: dt.date) -> dict[str, Any]:
    policy = load_policy()
    rule = policy["lifecycle"]["rules"][scope]
    return {
        "scope": scope,
        "bucket": rule["bucket"],
        "key": key,
        "created_on": now - dt.timedelta(days=days_old),
    }


def simulate_expiry(policy: dict[str, Any], item: dict[str, Any], now: dt.date) -> dict[str, Any]:
    rule = policy["lifecycle"]["rules"][item["scope"]]
    age_days = (now - item["created_on"]).days

    if any(item["key"].startswith(prefix) for prefix in rule["protected_prefixes"]):
        action = "protect"
    elif rule["expire_after_days"] is not None and age_days > rule["expire_after_days"]:
        action = "would-expire"
    elif age_days > rule["review_after_days"]:
        action = "review"
    else:
        action = "retain"

    return {
        "bucket": item["bucket"],
        "key": item["key"],
        "age_days": age_days,
        "action": action,
        "delete_call_issued": False,
    }
