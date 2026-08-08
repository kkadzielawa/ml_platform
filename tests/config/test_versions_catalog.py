import copy
import pathlib
import re

import yaml


CATALOG_PATH = pathlib.Path("config/versions.yaml")
REQUIRED_COMPONENTS = {
    "python",
    "base-image",
    "postgresql",
    "mlflow",
    "prometheus",
    "grafana",
}
FLOATING_TOKENS = {"latest", "stable", "main", "master", "nightly", "edge", "dev"}
VERSION_PATTERN = re.compile(r"^v?\d+\.\d+(?:\.\d+)?(?:[+-][0-9A-Za-z][0-9A-Za-z.-]*)?$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def load_catalog():
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))


def validation_errors(catalog):
    errors = []

    if catalog.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    components = catalog.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty list")
        return errors

    names = {component.get("name") for component in components}
    missing_names = REQUIRED_COMPONENTS - names
    if missing_names:
        errors.append(f"missing required components: {sorted(missing_names)}")

    for component in components:
        name = component.get("name", "<unknown>")
        version = component.get("version")
        if not isinstance(version, str) or not version.strip():
            errors.append(f"{name}: version is required")
        elif is_floating(version):
            errors.append(f"{name}: version is floating or unbounded: {version}")

        if not component.get("source_url", "").startswith("https://"):
            errors.append(f"{name}: source_url must be an https URL")

        if component.get("kind") == "image":
            image = component.get("image")
            if not isinstance(image, dict):
                errors.append(f"{name}: image metadata is required")
                continue
            for field in ("repository", "tag", "digest", "reference", "os", "architecture"):
                if not image.get(field):
                    errors.append(f"{name}: image.{field} is required")
            if image.get("tag") and is_floating(image["tag"]):
                errors.append(f"{name}: image tag is floating or unbounded: {image['tag']}")
            if image.get("digest") and not DIGEST_PATTERN.fullmatch(image["digest"]):
                errors.append(f"{name}: image digest must be sha256:<64 lowercase hex chars>")
            if image.get("digest") and image.get("reference") and image["digest"] not in image["reference"]:
                errors.append(f"{name}: image reference must include digest")

    return errors


def is_floating(value):
    normalized = value.strip().lower()
    if normalized in FLOATING_TOKENS:
        return True
    if any(token in normalized for token in ("<", ">", "*", ",")):
        return True
    if normalized.startswith(("~", "^")):
        return True
    if normalized.endswith((".x", "-snapshot")):
        return True
    return VERSION_PATTERN.fullmatch(value.strip()) is None


def test_versions_catalog_is_schema_valid():
    assert validation_errors(load_catalog()) == []


def test_rejects_missing_version():
    catalog = load_catalog()
    catalog["components"][0] = copy.deepcopy(catalog["components"][0])
    del catalog["components"][0]["version"]

    assert any("version is required" in error for error in validation_errors(catalog))


def test_rejects_floating_versions_and_tags():
    catalog = load_catalog()
    catalog["components"][0] = copy.deepcopy(catalog["components"][0])
    catalog["components"][0]["version"] = ">=3.11"
    catalog["components"][1] = copy.deepcopy(catalog["components"][1])
    catalog["components"][1]["image"] = copy.deepcopy(catalog["components"][1]["image"])
    catalog["components"][1]["image"]["tag"] = "latest"

    errors = validation_errors(catalog)

    assert any("version is floating" in error for error in errors)
    assert any("image tag is floating" in error for error in errors)


def test_rejects_image_without_digest():
    catalog = load_catalog()
    catalog["components"][1] = copy.deepcopy(catalog["components"][1])
    catalog["components"][1]["image"] = copy.deepcopy(catalog["components"][1]["image"])
    del catalog["components"][1]["image"]["digest"]

    assert any("image.digest is required" in error for error in validation_errors(catalog))
