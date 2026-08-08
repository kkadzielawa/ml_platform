import json
import pathlib
import re


SCHEMA_PATH = pathlib.Path("contracts/license-record.schema.json")
EXAMPLE_DIR = pathlib.Path("tests/contracts/fixtures/licenses")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validation_errors(instance, schema):
    return list(_validate(instance, schema, schema, "$"))


def _validate(instance, schema, root_schema, path):
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], root_schema)

    expected_type = schema.get("type")
    if expected_type and not matches_type(instance, expected_type):
        yield f"{path}: expected {expected_type}"
        return

    if "enum" in schema and instance not in schema["enum"]:
        yield f"{path}: not in enum"
    if "const" in schema and instance != schema["const"]:
        yield f"{path}: not const"

    if isinstance(instance, str):
        min_length = schema.get("minLength")
        pattern = schema.get("pattern")
        if min_length is not None and len(instance) < min_length:
            yield f"{path}: shorter than {min_length}"
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
        required = list(schema.get("required", []))
        for conditional in schema.get("allOf", []):
            required.extend(conditional_required_fields(instance, conditional))
        for field in required:
            if field not in instance:
                yield f"{path}: missing required field {field}"

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra_fields = set(instance) - set(properties)
            for field in sorted(extra_fields):
                yield f"{path}: unexpected field {field}"

        for field, value in instance.items():
            if field in properties:
                yield from _validate(value, properties[field], root_schema, f"{path}.{field}")


def conditional_required_fields(instance, conditional):
    if_schema = conditional.get("if", {})
    then_schema = conditional.get("then", {})
    properties = if_schema.get("properties", {})
    for field, rule in properties.items():
        if "const" in rule and instance.get(field) != rule["const"]:
            return []
    return then_schema.get("required", [])


def resolve_ref(ref, root_schema):
    if not ref.startswith("#/"):
        raise AssertionError(f"unsupported ref: {ref}")
    target = root_schema
    for part in ref.removeprefix("#/").split("/"):
        target = target[part]
    return target


def matches_type(value, expected_type):
    expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
    return any(_matches_single_type(value, candidate) for candidate in expected_types)


def _matches_single_type(value, expected_type):
    checks = {
        "array": lambda item: isinstance(item, list),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
        "object": lambda item: isinstance(item, dict),
        "string": lambda item: isinstance(item, str),
    }
    return checks[expected_type](value)


def test_schema_file_is_valid_json():
    schema = load_json(SCHEMA_PATH)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "License Record"


def test_package_model_and_dataset_examples_match_schema():
    schema = load_json(SCHEMA_PATH)
    examples = sorted(EXAMPLE_DIR.glob("*.json"))

    assert {path.name for path in examples} == {
        "dataset-cc-by.json",
        "model-apache.json",
        "package-pyyaml.json",
    }
    for example_path in examples:
        assert validation_errors(load_json(example_path), schema) == [], example_path


def test_model_and_dataset_specific_sections_are_required():
    schema = load_json(SCHEMA_PATH)
    model_record = load_json(EXAMPLE_DIR / "model-apache.json")
    dataset_record = load_json(EXAMPLE_DIR / "dataset-cc-by.json")
    del model_record["model"]
    del dataset_record["dataset"]

    assert any("missing required field model" in error for error in validation_errors(model_record, schema))
    assert any("missing required field dataset" in error for error in validation_errors(dataset_record, schema))


def test_rejects_unknown_or_source_available_as_accepted_by_default():
    source_available = load_json(EXAMPLE_DIR / "package-pyyaml.json")
    source_available["license"]["expression"] = "BUSL-1.1"
    source_available["license"]["classification"] = "source-available"
    source_available["license"]["osi_approved"] = False
    source_available["review"]["status"] = "accepted"

    assert policy_errors(source_available)


def test_rejects_missing_license_expression():
    schema = load_json(SCHEMA_PATH)
    record = load_json(EXAMPLE_DIR / "package-pyyaml.json")
    del record["license"]["expression"]

    assert any("missing required field expression" in error for error in validation_errors(record, schema))


def policy_errors(record):
    errors = []
    classification = record["license"]["classification"]
    status = record["review"]["status"]
    expression = record["license"]["expression"]
    if classification in {"source-available", "restricted", "unknown"} and status == "accepted":
        errors.append(f"{expression} cannot be accepted by default")
    if expression.lower() in {"latest", "unknown", "n/a"}:
        errors.append("license expression must be explicit")
    return errors
