from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from pipelines.classic_ml.pipeline import (
    CLASSIC_PIPELINE_NAME,
    PIPELINE_EDGES,
    PIPELINE_PARAMETERS,
    PIPELINE_STAGES,
    build_pipeline,
    compile_pipeline,
    pipeline_spec,
)


def test_graph_has_portable_order_and_no_import_time_execution() -> None:
    spec = pipeline_spec()

    assert spec["name"] == CLASSIC_PIPELINE_NAME
    assert tuple(spec["stages"]) == PIPELINE_STAGES
    assert tuple(tuple(edge) for edge in spec["edges"]) == PIPELINE_EDGES
    assert tuple(spec["parameters"]) == PIPELINE_PARAMETERS
    assert spec["behavior"] == {
        "cache": False,
        "registration_requires_passing_evaluation": True,
        "run_on_import": False,
    }


def test_graph_contains_all_required_stage_names() -> None:
    assert set(PIPELINE_STAGES) == {"snapshot", "validate", "transform", "train", "evaluate", "register"}
    assert PIPELINE_EDGES == (
        ("snapshot", "validate"),
        ("validate", "transform"),
        ("transform", "train"),
        ("train", "evaluate"),
        ("evaluate", "register"),
    )


def test_compile_is_explicit_and_reports_missing_sdk_cleanly(tmp_path: Path) -> None:
    if importlib.util.find_spec("kfp") is not None:
        pytest.skip("KFP SDK is installed; compile behavior is covered by the integration route")

    with pytest.raises(RuntimeError, match="KFP SDK is required only to compile"):
        compile_pipeline(tmp_path / "classic-ml.yaml")


def test_pipeline_builder_is_lazy_when_kfp_is_unavailable() -> None:
    if importlib.util.find_spec("kfp") is not None:
        pytest.skip("KFP SDK is installed; builder behavior is covered by compilation")

    with pytest.raises(RuntimeError, match="KFP SDK is required only to compile"):
        build_pipeline()
