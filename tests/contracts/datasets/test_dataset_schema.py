from __future__ import annotations

import copy
import ast
import json
import pathlib
import re
from typing import Any


SCHEMA_PATH = pathlib.Path("contracts/dataset.schema.json")
VALID_FIXTURE_DIR = pathlib.Path("tests/contracts/datasets/fixtures/valid")
INVALID_FIXTURE_DIR = pathlib.Path("tests/contracts/datasets/fixtures/invalid")


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validation_errors(instance: Any, schema: dict[str, Any]) -> list[str]:
    return list(_validate(instance, schema, schema, "$"))


def _validate(instance: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str):
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], root_schema)

    expected_type = schema.get("type")
    if expected_type and not matches_type(instance, expected_type):
        yield f"{path}: expected {expected_type}"
        return

    if "const" in schema and instance != schema["const"]:
        yield f"{path}: expected const {schema['const']!r}"

    if "enum" in schema and instance not in schema["enum"]:
        yield f"{path}: not in enum"

    if isinstance(instance, str):
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        pattern = schema.get("pattern")
        if min_length is not None and len(instance) < min_length:
            yield f"{path}: shorter than {min_length}"
        if max_length is not None and len(instance) > max_length:
            yield f"{path}: longer than {max_length}"
        if pattern and re.search(pattern, instance) is None:
            yield f"{path}: does not match pattern"

    if isinstance(instance, int) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and instance < minimum:
            yield f"{path}: less than {minimum}"
        if maximum is not None and instance > maximum:
            yield f"{path}: greater than {maximum}"

    if isinstance(instance, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(instance) < min_items:
            yield f"{path}: fewer than {min_items} items"
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                yield from _validate(item, item_schema, root_schema, f"{path}[{index}]")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in instance:
                yield f"{path}: missing required field {field}"

        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties")
        if additional is False:
            extra_fields = set(instance) - set(properties)
            for field in sorted(extra_fields):
                yield f"{path}: unexpected field {field}"

        for field, value in instance.items():
            if field in properties:
                yield from _validate(value, properties[field], root_schema, f"{path}.{field}")
            elif isinstance(additional, dict):
                yield from _validate(value, additional, root_schema, f"{path}.{field}")


def resolve_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise AssertionError(f"unsupported ref: {ref}")
    target = root_schema
    for part in ref.removeprefix("#/").split("/"):
        target = target[part]
    return target


def matches_type(value: Any, expected_type: str | list[str]) -> bool:
    expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
    return any(_matches_single_type(value, candidate) for candidate in expected_types)


def _matches_single_type(value: Any, expected_type: str) -> bool:
    type_checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return type_checks[expected_type](value)


def valid_example() -> dict[str, Any]:
    return load_json(VALID_FIXTURE_DIR / "housing-sale-features.json")


def with_field_added(field: dict[str, Any]) -> dict[str, Any]:
    changed = copy.deepcopy(valid_example())
    changed["schema"]["fields"].append(field)
    changed["schema"]["version"] = "1.1.0"
    return changed


def test_schema_file_is_valid_json():
    schema = load_json(SCHEMA_PATH)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "Parquet Dataset Metadata Contract"


def test_valid_dataset_fixtures_match_schema():
    schema = load_json(SCHEMA_PATH)
    fixtures = sorted(VALID_FIXTURE_DIR.glob("*.json"))

    assert fixtures
    for fixture in fixtures:
        assert validation_errors(load_json(fixture), schema) == []


def test_invalid_dataset_fixtures_are_rejected():
    schema = load_json(SCHEMA_PATH)
    fixtures = sorted(INVALID_FIXTURE_DIR.glob("*.json"))

    assert fixtures
    for fixture in fixtures:
        assert validation_errors(load_json(fixture), schema), fixture


def test_adding_nullable_field_is_compatible_metadata_case():
    schema = load_json(SCHEMA_PATH)
    changed = with_field_added(
        {
            "name": "days_on_market",
            "type": "int32",
            "nullable": True,
            "description": "Optional derived feature added after the initial version.",
            "categorical": {
                "encoding": "none"
            }
        }
    )

    assert validation_errors(changed, schema) == []
    assert any(change["change"] == "add-nullable-field" for change in changed["evolution"]["compatible_changes"])


def test_required_field_removal_is_recorded_as_breaking_not_silently_validated():
    dataset = valid_example()
    field_names = {field["name"] for field in dataset["schema"]["fields"]}
    breaking_changes = {change["change"] for change in dataset["evolution"]["breaking_changes"]}

    assert "property_id" in field_names
    assert "remove-field" in breaking_changes


def test_contract_validates_metadata_without_parquet_or_dataset_scan_dependency():
    syntax_tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    imported_modules = {
        alias.name.split(".")[0]
        for node in ast.walk(syntax_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module.split(".")[0]
        for node in ast.walk(syntax_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")

    assert not {"pyarrow", "pandas"} & imported_modules
    assert "file_count" in schema_text
    assert "manifest" in schema_text
