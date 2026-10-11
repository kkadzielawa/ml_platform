from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.classic_ml.pipeline import PIPELINE_STAGES, compile_pipeline, pipeline_spec
from pipelines.classic_ml.runtime_policies import RUNTIME_POLICIES


def test_policy_table_covers_every_stage_and_declares_all_runtime_controls() -> None:
    assert set(RUNTIME_POLICIES) == set(PIPELINE_STAGES)

    for policy in RUNTIME_POLICIES.values():
        assert policy.timeout_seconds > 0
        assert policy.termination_grace_seconds > 0
        assert policy.max_retries >= 0
        assert policy.cpu_request
        assert policy.cpu_limit
        assert policy.memory_request
        assert policy.memory_limit
        assert policy.cleanup_scope == "local-staging-only"
        assert policy.cache_identity

    assert RUNTIME_POLICIES["train"].cache_enabled is False
    assert RUNTIME_POLICIES["train"].max_retries == 0
    assert RUNTIME_POLICIES["register"].cache_enabled is False
    assert RUNTIME_POLICIES["register"].max_retries == 0


def test_pipeline_spec_exposes_the_policy_contract() -> None:
    spec = pipeline_spec()

    assert spec["runtime_policy_version"] == "classic-ml-runtime/v1"
    assert set(spec["runtime_policies"]) == set(PIPELINE_STAGES)
    assert spec["runtime_policies"]["train"]["cache_key_strategy"] == "disabled"
    assert spec["runtime_policies"]["register"]["retry_class"] == "non-idempotent-registration"


def _compiled_pipeline_spec(tmp_path: Path) -> dict:
    pytest.importorskip("kfp")
    yaml = pytest.importorskip("yaml")

    package = compile_pipeline(tmp_path / "classic-ml.yaml")
    return yaml.safe_load(package.read_text(encoding="utf-8"))


def _task_for_stage(spec: dict, stage: str) -> dict:
    return spec["root"]["dag"]["tasks"][f"{stage}-component"]


def _container_for_task(spec: dict, task: dict) -> dict:
    component_name = task["componentRef"]["name"]
    component = spec["components"][component_name]
    executor_name = component["executorLabel"]
    return spec["deploymentSpec"]["executors"][executor_name]["container"]


def test_compiled_ir_renders_cache_retry_timeout_resources_and_cleanup_policy(tmp_path: Path) -> None:
    spec = _compiled_pipeline_spec(tmp_path)

    for stage, policy in RUNTIME_POLICIES.items():
        task = _task_for_stage(spec, stage)
        container = _container_for_task(spec, task)

        caching = task.get("cachingOptions", {})
        if policy.cache_enabled:
            assert caching == {"enableCache": True}
            # A custom cacheKey would suppress the automatic input fingerprint.
            assert "cacheKey" not in caching
        else:
            assert caching == {}

        retry = task.get("retryPolicy")
        if policy.max_retries:
            assert retry["maxRetryCount"] == policy.max_retries
            assert retry["backoffDuration"] == policy.backoff_duration
            assert retry["backoffFactor"] == policy.backoff_factor
            assert retry["backoffMaxDuration"] == policy.backoff_max_duration
        else:
            assert retry is None

        command = container["command"]
        assert command[:4] == [
            "timeout",
            "--preserve-status",
            "--signal=TERM",
            f"--kill-after={policy.termination_grace_seconds}s",
        ]
        assert f"{policy.timeout_seconds}s" in command

        resources = container["resources"]
        assert resources["resourceCpuRequest"] == policy.cpu_request
        assert resources["resourceCpuLimit"] == policy.cpu_limit
        assert resources["resourceMemoryRequest"] == policy.memory_request
        assert resources["resourceMemoryLimit"] == policy.memory_limit

        assert {
            entry["name"]: entry["value"] for entry in container["env"]
        }["ML_PLATFORM_CLEANUP_SCOPE"] == policy.cleanup_scope


def test_cacheable_task_inputs_match_declared_identity(tmp_path: Path) -> None:
    spec = _compiled_pipeline_spec(tmp_path)

    for stage in ("validate", "evaluate"):
        task = _task_for_stage(spec, stage)
        inputs = set(task.get("inputs", {}).get("parameters", {}))
        inputs.update(task.get("inputs", {}).get("artifacts", {}))
        inputs = {name.removeprefix("pipelinechannel--") for name in inputs}
        assert inputs == set(RUNTIME_POLICIES[stage].cache_identity)


def test_training_and_registration_have_no_cache_or_blind_retry(tmp_path: Path) -> None:
    spec = _compiled_pipeline_spec(tmp_path)

    for stage in ("train", "register"):
        task = _task_for_stage(spec, stage)
        assert task.get("cachingOptions", {}) == {}
        assert "retryPolicy" not in task
