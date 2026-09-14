import copy
import json
import re
from pathlib import Path


ROOT = Path("tests/contracts/pipelines/fixtures")
SCHEMA_PATH = Path("contracts/pipeline-component.schema.json")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(spec):
    errors = []
    required = {"schema_version", "name", "stage", "image", "command", "inputs", "outputs", "execution", "logging", "provenance", "state"}
    errors.extend(f"missing {key}" for key in required - set(spec))
    if spec.get("schema_version") != "1.0.0": errors.append("schema version")
    if spec.get("stage") not in {"snapshot", "validate", "transform", "train", "evaluate", "register", "batch-inference"}: errors.append("stage")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", spec.get("image", {}).get("digest", "")): errors.append("image digest")
    for artifact in spec.get("inputs", []) + spec.get("outputs", []):
        uri = artifact.get("uri", "")
        if not re.fullmatch(r"(s3|file|https)://[^\s]+", uri) or "/main/" in uri or "/latest/" in uri: errors.append("immutable artifact uri")
    execution = spec.get("execution", {})
    if execution.get("retry", {}).get("retry_safety") not in {"idempotent", "deduplicated-output"}: errors.append("retry safety")
    cancellation = execution.get("cancellation", {})
    if cancellation.get("signal") != "SIGTERM" or cancellation.get("behavior") != "stop-new-work-and-cleanup-local-state": errors.append("cancellation")
    if execution.get("exit_codes") != {"success": 0, "cancelled": 130, "retryable": 75, "permanent_failure": 1}: errors.append("exit codes")
    logging = spec.get("logging", {})
    if logging.get("format") != "json-lines" or logging.get("raw_data_logging") is not False: errors.append("logging")
    if spec.get("provenance") != {"run_manifest": "write-on-success-and-failure", "lineage": "emit-start-complete-fail"}: errors.append("provenance")
    if spec.get("state") != {"shared_memory_required": False, "durable_state": "declared-artifacts-only"}: errors.append("state")
    return errors


def merge(base, change):
    for key, value in change.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict): merge(base[key], value)
        else: base[key] = value


def test_schema_declares_orchestrator_neutral_execution_rules():
    schema = load(SCHEMA_PATH)
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    assert schema["title"] == "Portable Pipeline Component Contract"
    for term in ["SIGTERM", "idempotent", "deduplicated-output", "shared_memory_required", "emit-start-complete-fail", "raw_data_logging", "retryable"]:
        assert term in text


def test_valid_component_specification_is_accepted():
    assert validate(load(ROOT / "valid/snapshot.json")) == []


def test_invalid_component_specifications_are_rejected():
    valid = load(ROOT / "valid/snapshot.json")
    fixtures = sorted((ROOT / "invalid").glob("*.json"))
    assert fixtures
    for fixture in fixtures:
        candidate = copy.deepcopy(valid)
        merge(candidate, load(fixture))
        assert validate(candidate), fixture
