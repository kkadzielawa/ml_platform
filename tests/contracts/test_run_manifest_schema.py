import json
import pathlib
import re


SCHEMA_PATH = pathlib.Path("contracts/run-manifest.schema.json")
VALID_EXAMPLE_PATH = pathlib.Path("contracts/examples/run-manifests/classic-ml-valid.json")
INVALID_FIXTURE_DIR = pathlib.Path("contracts/examples/run-manifests/invalid")


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


def test_schema_file_is_valid_json():
    schema = load_json(SCHEMA_PATH)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "Universal Run Manifest"


def test_valid_classic_ml_manifest_matches_schema():
    assert validation_errors(load_json(VALID_EXAMPLE_PATH), load_json(SCHEMA_PATH)) == []


def test_invalid_missing_provenance_fixtures_are_rejected():
    schema = load_json(SCHEMA_PATH)
    invalid_fixtures = sorted(INVALID_FIXTURE_DIR.glob("*.json"))

    assert invalid_fixtures
    for fixture_path in invalid_fixtures:
        assert validation_errors(load_json(fixture_path), schema), fixture_path


def test_manifest_represents_required_provenance_fields():
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    required_terms = [
        "artifact",
        "checksum",
        "commit",
        "data_revision",
        "dependency_lockfile_hash",
        "digest",
        "dirty_worktree",
        "evaluation_results",
        "license",
        "lineage_events",
        "metrics",
        "parameters",
        "policy_decisions",
        "random_seeds",
        "schema_ref",
        "signature",
        "sbom",
        "uri",
    ]

    for term in required_terms:
        assert term in schema_text
