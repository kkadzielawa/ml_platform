from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from ml_platform.components.artifacts import Artifact
from ml_platform.components.logging import ComponentLogger
from ml_platform.components.noop import copy_one_artifact
from ml_platform.components.parameters import ParameterError, TypedParameters
from ml_platform.components.runtime import ComponentContext, run_component


def test_noop_runs_with_filesystem_fixtures(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("study fixture\n", encoding="utf-8")
    destination = tmp_path / "published.txt"
    manifest = tmp_path / "evidence" / "manifest.json"
    lineage = tmp_path / "evidence" / "lineage.jsonl"
    logs = io.StringIO()
    context = ComponentContext(
        run_id="run-20260926t120000z-00000001",
        component_name="noop-copy",
        inputs=(Artifact("input", source.as_uri()),),
        outputs=(Artifact("output", destination.as_uri()),),
        parameters={"copy_mode": "binary"},
        manifest_path=manifest,
        lineage_path=lineage,
        logger=ComponentLogger(
            run_id="run-20260926t120000z-00000001",
            component_name="noop-copy",
            attempt=1,
            stream=logs,
        ),
    )

    run_component(context, copy_one_artifact)

    assert destination.read_text(encoding="utf-8") == "study fixture\n"
    written_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    assert written_manifest["status"] == "completed"
    assert written_manifest["outputs"][0]["name"] == "output"
    events = [json.loads(line) for line in lineage.read_text(encoding="utf-8").splitlines()]
    assert [event["eventType"] for event in events] == ["START", "COMPLETE"]
    assert all({"run_id", "component_name", "attempt"} <= set(json.loads(line)) for line in logs.getvalue().splitlines())


def test_invalid_contract_fails_before_side_effects(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    lineage = tmp_path / "lineage.jsonl"
    called = False

    def action(_: ComponentContext) -> None:
        nonlocal called
        called = True

    context = ComponentContext(
        run_id="run-20260926t120001z-00000002",
        component_name="invalid-component",
        outputs=(),
        manifest_path=manifest,
        lineage_path=lineage,
    )

    with pytest.raises(ValueError, match="at least one output"):
        run_component(context, action)

    assert called is False
    assert not manifest.exists()
    assert not lineage.exists()


def test_failed_action_writes_fail_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("fixture", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    lineage = tmp_path / "lineage.jsonl"
    context = ComponentContext(
        run_id="run-20260926t120002z-00000003",
        component_name="failing-component",
        inputs=(Artifact("input", source.as_uri()),),
        outputs=(Artifact("output", (tmp_path / "output.txt").as_uri()),),
        manifest_path=manifest,
        lineage_path=lineage,
    )

    def fail(_: ComponentContext) -> None:
        raise RuntimeError("fixture failure")

    with pytest.raises(RuntimeError, match="fixture failure"):
        run_component(context, fail)

    assert json.loads(manifest.read_text(encoding="utf-8"))["status"] == "failed"
    events = [json.loads(line) for line in lineage.read_text(encoding="utf-8").splitlines()]
    assert [event["eventType"] for event in events] == ["START", "FAIL"]


def test_typed_parameters_are_strict() -> None:
    parameters = TypedParameters({"name": "baseline", "count": 2, "threshold": 0.75, "enabled": True})
    assert parameters.require_str("name") == "baseline"
    assert parameters.require_int("count") == 2
    assert parameters.require_float("threshold") == 0.75
    assert parameters.require_bool("enabled") is True

    with pytest.raises(ParameterError, match="must be an integer"):
        TypedParameters({"count": True}).require_int("count")
    with pytest.raises(ParameterError, match="missing required parameter"):
        parameters.require_str("missing")
