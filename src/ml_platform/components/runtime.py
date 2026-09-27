"""Local component execution lifecycle and execution manifests."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .artifacts import Artifact
from .lineage import LineageWriter
from .logging import ComponentLogger
from .parameters import TypedParameters


_NAME = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
_RUN_ID = re.compile(r"^run-\d{8}t\d{6}z-[0-9a-f]{8}$")


class ComponentExecutionError(RuntimeError):
    """Reserved for callers that want to classify a component failure."""


@dataclass
class ComponentContext:
    """All declared inputs, outputs, and provenance paths for one attempt."""

    run_id: str
    component_name: str
    inputs: tuple[Artifact, ...] = field(default_factory=tuple)
    outputs: tuple[Artifact, ...] = field(default_factory=tuple)
    parameters: TypedParameters | Mapping[str, Any] = field(default_factory=TypedParameters)
    manifest_path: Path = Path("run-manifest.json")
    lineage_path: Path = Path("lineage.jsonl")
    attempt: int = 1
    logger: ComponentLogger | None = None

    def __post_init__(self) -> None:
        self.inputs = tuple(self.inputs)
        self.outputs = tuple(self.outputs)
        if not isinstance(self.parameters, TypedParameters):
            self.parameters = TypedParameters(self.parameters)
        self.manifest_path = Path(self.manifest_path)
        self.lineage_path = Path(self.lineage_path)

    def validate(self) -> None:
        """Validate the declaration without creating files or calling services."""

        if not _RUN_ID.fullmatch(self.run_id):
            raise ValueError("run_id must match run-YYYYMMDDtHHMMSSz-<8 lowercase hex>")
        if not _NAME.fullmatch(self.component_name):
            raise ValueError(f"invalid component_name: {self.component_name!r}")
        if not isinstance(self.attempt, int) or isinstance(self.attempt, bool) or self.attempt < 1:
            raise ValueError("attempt must be a positive integer")
        if not self.outputs:
            raise ValueError("a component must declare at least one output")
        if self.manifest_path == self.lineage_path:
            raise ValueError("manifest_path and lineage_path must be different files")
        artifact_names = [artifact.name for artifact in (*self.inputs, *self.outputs)]
        if len(artifact_names) != len(set(artifact_names)):
            raise ValueError("artifact names must be unique within a component")
        for artifact in (*self.inputs, *self.outputs):
            artifact.local_path()


def run_component(
    context: ComponentContext,
    action: Callable[[ComponentContext], Any],
) -> Any:
    """Run an action with validation, logs, manifest, and lineage evidence.

    Context validation is deliberately the first operation.  An invalid
    contract therefore cannot create a manifest, lineage file, log entry, or
    invoke the component action.
    """

    context.validate()
    started_at = _timestamp()
    logger = context.logger or ComponentLogger(
        run_id=context.run_id,
        component_name=context.component_name,
        attempt=context.attempt,
    )
    context.logger = logger
    lineage = LineageWriter(
        context.lineage_path,
        run_id=context.run_id,
        component_name=context.component_name,
    )
    lineage.emit("START", inputs=context.inputs, outputs=())
    logger.info("component started")

    try:
        result = action(context)
    except Exception as error:
        finished_at = _timestamp()
        message = f"{type(error).__name__}: {error}"
        lineage.emit("FAIL", inputs=context.inputs, outputs=(), message=message)
        _write_manifest(context, started_at, finished_at, status="failed", error=message)
        logger.error("component failed", error_type=type(error).__name__)
        raise

    finished_at = _timestamp()
    lineage.emit("COMPLETE", inputs=context.inputs, outputs=context.outputs)
    _write_manifest(context, started_at, finished_at, status="completed")
    logger.info("component completed")
    return result


def _write_manifest(
    context: ComponentContext,
    started_at: str,
    finished_at: str,
    *,
    status: str,
    error: str | None = None,
) -> None:
    manifest: dict[str, Any] = {
        "schema_version": "component-execution/1.0",
        "run_id": context.run_id,
        "component_name": context.component_name,
        "attempt": context.attempt,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "parameters": context.parameters.as_dict(),
        "inputs": [{"name": artifact.name, "uri": artifact.uri} for artifact in context.inputs],
        "outputs": [{"name": artifact.name, "uri": artifact.uri} for artifact in context.outputs],
    }
    if error:
        manifest["error"] = error[:512]
    context.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = context.manifest_path.with_suffix(context.manifest_path.suffix + ".partial")
    temporary_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(context.manifest_path)


def _timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
