"""Runtime policy declarations for the classic ML pipeline.

The policy table is deliberately independent of the KFP SDK.  It is used both
by the pipeline builder and by tests that inspect the compiled IR.

KFP's custom cache key replaces its automatic input fingerprint.  The
cacheable tasks below therefore use the automatic key and declare the exact
identity inputs that must remain wired into the task.  Tasks whose current
inputs cannot prove an immutable identity, or which have external side
effects, have caching disabled instead of receiving an unsafe static key.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


RUNTIME_POLICY_VERSION = "classic-ml-runtime/v1"


@dataclass(frozen=True)
class RuntimePolicy:
    """One stage's execution, cache, resource, and cleanup contract."""

    cache_enabled: bool
    cache_identity: tuple[str, ...]
    retry_class: str
    max_retries: int
    backoff_duration: str | None
    backoff_factor: float | None
    backoff_max_duration: str | None
    timeout_seconds: int
    termination_grace_seconds: int
    cpu_request: str
    cpu_limit: str
    memory_request: str
    memory_limit: str
    cleanup_scope: str = "local-staging-only"

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-friendly representation for specs and docs."""

        result = asdict(self)
        result["cache_identity"] = list(self.cache_identity)
        result["cache_key_strategy"] = (
            "automatic-inputs" if self.cache_enabled else "disabled"
        )
        return result


# The identity lists are documentation and test contracts for the automatic
# KFP cache key.  They are not passed as custom KFP cache_key values because a
# custom value makes KFP ignore all automatic inputs.
RUNTIME_POLICIES: dict[str, RuntimePolicy] = {
    "snapshot": RuntimePolicy(
        cache_enabled=False,
        cache_identity=("repository", "resolved_commit_id", "dataset_path"),
        retry_class="transient-container",
        max_retries=2,
        backoff_duration="10s",
        backoff_factor=2.0,
        backoff_max_duration="120s",
        timeout_seconds=300,
        termination_grace_seconds=30,
        cpu_request="100m",
        cpu_limit="500m",
        memory_request="256Mi",
        memory_limit="512Mi",
    ),
    "validate": RuntimePolicy(
        cache_enabled=True,
        cache_identity=("snapshot_manifest", "dataset_path", "suite_path"),
        retry_class="transient-container",
        max_retries=2,
        backoff_duration="10s",
        backoff_factor=2.0,
        backoff_max_duration="120s",
        timeout_seconds=600,
        termination_grace_seconds=30,
        cpu_request="250m",
        cpu_limit="1",
        memory_request="512Mi",
        memory_limit="1Gi",
    ),
    "transform": RuntimePolicy(
        cache_enabled=False,
        cache_identity=(
            "run_id",
            "dataset_content_checksum",
            "transform_implementation",
            "transform_configuration",
        ),
        retry_class="idempotent-output",
        max_retries=2,
        backoff_duration="10s",
        backoff_factor=2.0,
        backoff_max_duration="120s",
        timeout_seconds=900,
        termination_grace_seconds=30,
        cpu_request="250m",
        cpu_limit="1",
        memory_request="512Mi",
        memory_limit="1Gi",
    ),
    "train": RuntimePolicy(
        cache_enabled=False,
        cache_identity=(
            "dataset_revision",
            "code_version",
            "model_name",
            "model_version",
            "training_implementation",
        ),
        retry_class="non-idempotent-side-effect",
        max_retries=0,
        backoff_duration=None,
        backoff_factor=None,
        backoff_max_duration=None,
        timeout_seconds=1800,
        termination_grace_seconds=60,
        cpu_request="500m",
        cpu_limit="2",
        memory_request="1Gi",
        memory_limit="2Gi",
    ),
    "evaluate": RuntimePolicy(
        cache_enabled=True,
        cache_identity=(
            "transformed_dataset",
            "training_output",
            "run_id",
            "dataset_path",
            "metadata_path",
            "dataset_name",
            "dataset_version",
            "dataset_revision",
            "model_name",
            "model_version",
            "code_version",
        ),
        retry_class="idempotent-output",
        max_retries=2,
        backoff_duration="10s",
        backoff_factor=2.0,
        backoff_max_duration="120s",
        timeout_seconds=900,
        termination_grace_seconds=30,
        cpu_request="250m",
        cpu_limit="1",
        memory_request="512Mi",
        memory_limit="1Gi",
    ),
    "register": RuntimePolicy(
        cache_enabled=False,
        cache_identity=(
            "evaluation_sha256",
            "mlflow_run_id",
            "model_name",
            "model_version",
            "model_source_uri",
            "license_record",
        ),
        retry_class="non-idempotent-registration",
        max_retries=0,
        backoff_duration=None,
        backoff_factor=None,
        backoff_max_duration=None,
        timeout_seconds=600,
        termination_grace_seconds=30,
        cpu_request="100m",
        cpu_limit="500m",
        memory_request="256Mi",
        memory_limit="512Mi",
    ),
}


def runtime_policy_spec() -> dict[str, dict[str, Any]]:
    """Return all policies in a serializable form for docs and tests."""

    return {stage: policy.as_dict() for stage, policy in RUNTIME_POLICIES.items()}


def bounded_command(module: str, policy: RuntimePolicy) -> list[str]:
    """Build a process-level deadline command for the pinned Debian image.

    KFP 2.17 has no task-level timeout method or IR field.  GNU ``timeout``
    sends SIGTERM at the deadline and SIGKILL only after the component's
    declared cleanup grace period.  ``--preserve-status`` lets the component's
    own exit status remain visible to the orchestrator when it exits cleanly.
    """

    return [
        "timeout",
        "--preserve-status",
        "--signal=TERM",
        f"--kill-after={policy.termination_grace_seconds}s",
        f"{policy.timeout_seconds}s",
        "python",
        "-m",
        module,
    ]


def apply_runtime_policy(task: Any, stage: str) -> Any:
    """Apply a declared policy to a KFP ``PipelineTask``."""

    policy = RUNTIME_POLICIES[stage]
    # Do not pass a custom cache key: in KFP it suppresses the automatic input
    # fingerprint and would make a static key unsafe for runtime parameters.
    task.set_caching_options(policy.cache_enabled)
    if policy.max_retries:
        task.set_retry(
            num_retries=policy.max_retries,
            backoff_duration=policy.backoff_duration,
            backoff_factor=policy.backoff_factor,
            backoff_max_duration=policy.backoff_max_duration,
        )
    task.set_cpu_request(policy.cpu_request)
    task.set_cpu_limit(policy.cpu_limit)
    task.set_memory_request(policy.memory_request)
    task.set_memory_limit(policy.memory_limit)
    # Keep the cleanup contract visible in the rendered task definition while
    # leaving durable artifact deletion outside the pipeline's authority.
    task.set_env_variable("ML_PLATFORM_CLEANUP_SCOPE", policy.cleanup_scope)
    return task
