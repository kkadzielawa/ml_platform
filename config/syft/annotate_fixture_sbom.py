from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: annotate_fixture_sbom.py <cyclonedx.json> <spdx.json> <application.json> <image-id-file>"
        )

    cyclonedx_path = Path(sys.argv[1])
    spdx_path = Path(sys.argv[2])
    application_path = Path(sys.argv[3])
    image_id_path = Path(sys.argv[4])

    application = read_json(application_path)
    image_id = image_id_path.read_text(encoding="utf-8").strip()

    annotate_cyclonedx(cyclonedx_path, application, image_id)
    annotate_spdx(spdx_path, application, image_id)


def annotate_cyclonedx(path: Path, application: dict[str, Any], image_id: str) -> None:
    sbom = read_json(path)
    components = sbom.setdefault("components", [])
    component = {
        "type": "application",
        "name": application["application_name"],
        "version": "0.1.0",
        "bom-ref": f"application:{application['application_name']}",
        "properties": [
            {"name": "ml-platform.source.path", "value": application["expected_path"]},
            {"name": "ml-platform.image.id", "value": image_id},
        ],
    }
    replace_named(components, component)
    metadata = sbom.setdefault("metadata", {})
    properties = metadata.setdefault("properties", [])
    replace_property(properties, "ml-platform.image.id", image_id)
    write_json(path, sbom)


def annotate_spdx(path: Path, application: dict[str, Any], image_id: str) -> None:
    sbom = read_json(path)
    packages = sbom.setdefault("packages", [])
    package = {
        "name": application["application_name"],
        "SPDXID": f"SPDXRef-Application-{application['application_name']}",
        "versionInfo": "0.1.0",
        "downloadLocation": "NOASSERTION",
        "filesAnalyzed": False,
        "supplier": "Organization: ml-platform-study",
        "licenseConcluded": "NOASSERTION",
        "licenseDeclared": "NOASSERTION",
        "copyrightText": "NOASSERTION",
        "comment": f"{application['expected_path']} in image {image_id}",
    }
    replace_named(packages, package)
    sbom["documentComment"] = f"Fixture image ID: {image_id}"
    write_json(path, sbom)


def replace_named(items: list[dict[str, Any]], replacement: dict[str, Any]) -> None:
    name = replacement["name"]
    items[:] = [item for item in items if item.get("name") != name]
    items.append(replacement)


def replace_property(properties: list[dict[str, str]], name: str, value: str) -> None:
    properties[:] = [item for item in properties if item.get("name") != name]
    properties.append({"name": name, "value": value})


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
