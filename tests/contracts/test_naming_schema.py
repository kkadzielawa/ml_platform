import copy
import json
import pathlib
import re


SCHEMA_PATH = pathlib.Path("contracts/naming.schema.json")


VALID_EXAMPLE = {
    "project": {"name": "ml-platform"},
    "environment": {"name": "local"},
    "dataset": {"name": "iris-classifier", "version": "v0001"},
    "model": {"name": "iris-baseline", "version": "0.1.0"},
    "run": {"id": "run-20260808t142233z-a1b2c3d4"},
    "artifact_prefixes": {
        "datasets": "projects/ml-platform/datasets/iris-classifier/versions/v0001/",
        "models": "projects/ml-platform/models/iris-baseline/versions/0.1.0/",
        "runs": "projects/ml-platform/runs/run-20260808t142233z-a1b2c3d4/",
        "experiments": "projects/ml-platform/experiments/local-classic-ml/",
    },
    "labels": {
        "app.kubernetes.io/name": "iris-baseline",
        "app.kubernetes.io/part-of": "ml-platform",
        "ml-platform-study/phase": "00",
        "ml-platform-study/component": "training",
        "ml-platform-study/environment": "local",
        "ml-platform-study/owner": "study",
    },
}


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validation_errors(instance, schema):
    return list(_validate(instance, schema, schema, "$"))


def _validate(instance, schema, root_schema, path):
    if "$ref" in schema:
        schema = resolve_ref(schema["$ref"], root_schema)

    expected_type = schema.get("type")
    if expected_type and not matches_type(instance, expected_type):
        yield f"{path}: expected {expected_type}"
        return

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

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in instance:
                yield f"{path}: missing required field {field}"

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra_fields = set(instance) - set(properties)
            for field in sorted(extra_fields):
                yield f"{path}: unexpected field {field}"

        for field, subschema in properties.items():
            if field in instance:
                yield from _validate(instance[field], subschema, root_schema, f"{path}.{field}")


def resolve_ref(ref, root_schema):
    if not ref.startswith("#/"):
        raise AssertionError(f"unsupported ref: {ref}")
    target = root_schema
    for part in ref.removeprefix("#/").split("/"):
        target = target[part]
    return target


def matches_type(value, expected_type):
    return {
        "object": isinstance(value, dict),
        "string": isinstance(value, str),
    }[expected_type]


def with_change(path, value):
    changed = copy.deepcopy(VALID_EXAMPLE)
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return changed


def without(path):
    changed = copy.deepcopy(VALID_EXAMPLE)
    target = changed
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return changed


def test_schema_file_is_valid_json():
    schema = load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ML Platform Naming Contract"


def test_valid_example_matches_schema():
    assert validation_errors(VALID_EXAMPLE, load_schema()) == []


def test_invalid_portable_names_are_rejected():
    schema = load_schema()
    invalid_examples = [
        with_change(("project", "name"), "ML_Platform"),
        with_change(("dataset", "name"), "a"),
        with_change(("model", "name"), "model_latest"),
        with_change(("environment", "name"), "dev.local"),
        with_change(("project", "name"), "konrad-test"),
    ]

    for example in invalid_examples:
        assert validation_errors(example, schema)


def test_invalid_run_and_version_values_are_rejected():
    schema = load_schema()
    invalid_examples = [
        with_change(("run", "id"), "2026-08-08-a1b2c3d4"),
        with_change(("dataset", "version"), "latest"),
        with_change(("model", "version"), "1.0"),
    ]

    for example in invalid_examples:
        assert validation_errors(example, schema)


def test_invalid_artifact_prefixes_are_rejected():
    schema = load_schema()
    invalid_examples = [
        with_change(("artifact_prefixes", "runs"), "/projects/ml-platform/runs/run-20260808t142233z-a1b2c3d4/"),
        with_change(("artifact_prefixes", "runs"), "s3://bucket/projects/ml-platform/runs/run-20260808t142233z-a1b2c3d4/"),
        with_change(("artifact_prefixes", "runs"), "projects/ml-platform//runs/run-20260808t142233z-a1b2c3d4/"),
        with_change(("artifact_prefixes", "runs"), "projects/ml-platform/runs/../secret/"),
        with_change(("artifact_prefixes", "runs"), "projects/ml-platform/runs/user-token/"),
    ]

    for example in invalid_examples:
        assert validation_errors(example, schema)


def test_required_labels_are_enforced():
    schema = load_schema()

    assert validation_errors(without(("labels", "ml-platform-study/owner")), schema)
    assert validation_errors(with_change(("labels", "ml-platform-study/phase"), "phase-00"), schema)
