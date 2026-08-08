"""Small stdlib-only validator for the Phase 0 run manifest contract."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


def validate_manifest(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    errors = validation_errors(instance, schema)
    if errors:
        raise ValueError("run manifest does not match schema:\n" + "\n".join(errors))


def validation_errors(instance: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    return list(_validate(instance, schema, schema, "$"))


def _validate(instance: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str) -> Iterable[str]:
    if "$ref" in schema:
        schema = _resolve_ref(schema["$ref"], root_schema)

    expected_type = schema.get("type")
    if expected_type and not _matches_type(instance, expected_type):
        yield f"{path}: expected {expected_type}"
        return

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


def _resolve_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema ref: {ref}")
    target = root_schema
    for part in ref.removeprefix("#/").split("/"):
        target = target[part]
    return target


def _matches_type(value: Any, expected_type: str | list[str]) -> bool:
    expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
    return any(_matches_single_type(value, candidate) for candidate in expected_types)


def _matches_single_type(value: Any, expected_type: str) -> bool:
    type_checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "null": lambda item: item is None,
        "number": lambda item: (isinstance(item, int) or isinstance(item, float)) and not isinstance(item, bool),
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return type_checks[expected_type](value)
