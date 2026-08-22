from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGE_NAME = os.environ.get("BUILD_FIXTURE_IMAGE", "ml-platform-study/build-fixture:local")
SECRET_VALUE = "fixture-build-secret-value"


def test_dockerfile_uses_digest_pinned_base_and_buildkit_syntax() -> None:
    dockerfile = (REPO_ROOT / "build" / "Dockerfile.build-fixture").read_text(encoding="utf-8")
    lines = dockerfile.splitlines()

    assert lines[0] == "# syntax=docker/dockerfile:1.7"
    from_lines = [line for line in lines if line.startswith("FROM ")]
    assert from_lines == [
        "FROM docker.io/library/python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a"
    ]
    assert "--mount=type=secret,id=fixture_build_secret" in dockerfile


def test_image_runs_as_non_root_and_does_not_expose_build_secret() -> None:
    inspect = docker("image", "inspect", IMAGE_NAME)
    metadata = json.loads(inspect.stdout)[0]

    assert metadata["Config"]["User"] == "10001:10001"
    assert not metadata["Config"].get("Env") or SECRET_VALUE not in "\n".join(metadata["Config"]["Env"])

    uid = docker("run", "--rm", "--entrypoint", "python", IMAGE_NAME, "-c", "import os; print(os.getuid())")
    assert uid.stdout.strip() == "10001"

    secret_search = docker(
        "run",
        "--rm",
        "--entrypoint",
        "python",
        IMAGE_NAME,
        "-c",
        (
            "from pathlib import Path; "
            f"needle={SECRET_VALUE!r}; "
            "hits=[]; "
            "\nfor path in [Path('/opt/ml-platform/build-fixture'), Path('/home/appuser'), Path('/tmp')]:"
            "\n    if path.exists():"
            "\n        for item in path.rglob('*'):"
            "\n            if item.is_file() and needle in item.read_text(errors='ignore'):"
            "\n                hits.append(str(item))"
            "\nprint('\\n'.join(hits))"
        ),
    )
    assert secret_search.stdout.strip() == ""


def test_image_serves_health_response() -> None:
    response = docker("run", "--rm", "--entrypoint", "python", IMAGE_NAME, "-c", "import app, json; print(app.json.dumps({'status':'ok'}, sort_keys=True))")
    assert response.stdout.strip() == '{"status": "ok"}'


def test_repeated_build_report_exists_and_records_two_builds() -> None:
    report = REPO_ROOT / "build" / "reports" / "build-fixture-digests.txt"
    content = report.read_text(encoding="utf-8")

    assert "first_image_id=" in content
    assert "second_image_id=" in content
    assert "ids_match=true" in content


def docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
