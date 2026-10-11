"""Run portable component commands in order without an orchestrator.

The runner deliberately accepts an ordered sequence of already-defined
component invocations.  It records process evidence and declared artifacts,
but it does not introduce a second graph or component-definition language.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ComponentInvocation:
    """One existing component command and the artifacts it must publish."""

    name: str
    command: tuple[str, ...]
    output_paths: Mapping[str, Path] = field(default_factory=dict)
    environment: Mapping[str, str] = field(default_factory=dict)
    cwd: Path | None = None
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        if not _is_path_segment(self.name):
            raise ValueError("component name must be non-empty and contain no whitespace")
        command = tuple(str(argument) for argument in self.command)
        if not command:
            raise ValueError("component command must not be empty")
        object.__setattr__(self, "command", command)
        paths = {str(name): Path(path) for name, path in self.output_paths.items()}
        if any(not _is_path_segment(name) for name in paths):
            raise ValueError("artifact names must be non-empty and contain no whitespace")
        object.__setattr__(self, "output_paths", paths)
        object.__setattr__(self, "environment", {str(key): str(value) for key, value in self.environment.items()})
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive when provided")
        if self.cwd is not None:
            object.__setattr__(self, "cwd", Path(self.cwd))


@dataclass(frozen=True)
class ArtifactCapture:
    """Digest and durable capture location for one declared output."""

    name: str
    source_path: Path
    capture_path: Path
    sha256: str
    bytes: int
    kind: str

    def as_dict(self, *, root: Path | None = None) -> dict[str, Any]:
        source = _display_path(self.source_path, root)
        capture = _display_path(self.capture_path, root)
        return {
            "name": self.name,
            "source_path": source,
            "capture_path": capture,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class ComponentResult:
    """Captured evidence for one component attempt."""

    name: str
    command: tuple[str, ...]
    status: str
    returncode: int
    started_at: str
    finished_at: str
    duration_seconds: float
    stdout: str
    stderr: str
    artifacts: tuple[ArtifactCapture, ...] = ()
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == "completed"

    def as_dict(self, *, root: Path | None = None) -> dict[str, Any]:
        return {
            "name": self.name,
            "command": list(self.command),
            "status": self.status,
            "returncode": self.returncode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "artifacts": [artifact.as_dict(root=root) for artifact in self.artifacts],
            "error": self.error,
        }


@dataclass(frozen=True)
class LocalPipelineResult:
    """Final ordered-run result, including captured component evidence."""

    run_id: str
    status: str
    run_root: Path
    components: tuple[ComponentResult, ...]
    failed_component: str | None = None
    skipped_components: tuple[str, ...] = ()
    summary_path: Path | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == "completed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "local-pipeline-run/1.0",
            "run_id": self.run_id,
            "status": self.status,
            "run_root": str(self.run_root),
            "components": [component.as_dict(root=self.run_root) for component in self.components],
            "failed_component": self.failed_component,
            "skipped_components": list(self.skipped_components),
        }


class LocalPipelineError(RuntimeError):
    """Raised when a component fails or omits a declared artifact."""

    def __init__(self, result: LocalPipelineResult) -> None:
        if result.failed_component is None:
            raise ValueError("a failed local pipeline result must identify its component")
        failed = next(component for component in result.components if component.name == result.failed_component)
        detail = failed.error or f"exit code {failed.returncode}"
        super().__init__(f"local pipeline stopped at {failed.name}: {detail}")
        self.result = result


class LocalPipelineRunner:
    """Execute an ordered sequence of portable component commands."""

    def __init__(
        self,
        run_root: Path,
        *,
        run_id: str = "local-run",
        environment: Mapping[str, str] | None = None,
        default_timeout_seconds: float | None = None,
    ) -> None:
        self.run_root = Path(run_root)
        self.run_id = run_id
        self.environment = {str(key): str(value) for key, value in (environment or {}).items()}
        if default_timeout_seconds is not None and default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be positive when provided")
        self.default_timeout_seconds = default_timeout_seconds

    def run(
        self,
        invocations: Sequence[ComponentInvocation],
        *,
        summary_path: Path | None = None,
    ) -> LocalPipelineResult:
        """Run commands in order and stop immediately after the first failure."""

        ordered = tuple(invocations)
        _validate_ordered_invocations(ordered)
        self.run_root.mkdir(parents=True, exist_ok=True)
        captured_root = self.run_root / "captured-artifacts"
        results: list[ComponentResult] = []

        for index, invocation in enumerate(ordered):
            result = self._run_invocation(invocation, captured_root)
            results.append(result)
            if not result.succeeded:
                pipeline_result = LocalPipelineResult(
                    run_id=self.run_id,
                    status="failed",
                    run_root=self.run_root,
                    components=tuple(results),
                    failed_component=invocation.name,
                    skipped_components=tuple(item.name for item in ordered[index + 1 :]),
                )
                pipeline_result = self._write_summary(pipeline_result, summary_path)
                raise LocalPipelineError(pipeline_result)

        pipeline_result = LocalPipelineResult(
            run_id=self.run_id,
            status="completed",
            run_root=self.run_root,
            components=tuple(results),
        )
        return self._write_summary(pipeline_result, summary_path)

    def _run_invocation(
        self,
        invocation: ComponentInvocation,
        captured_root: Path,
    ) -> ComponentResult:
        started_at = _timestamp()
        started_monotonic = time.monotonic()
        environment = os.environ.copy()
        environment.update(self.environment)
        environment.update(invocation.environment)
        timeout = invocation.timeout_seconds or self.default_timeout_seconds
        try:
            completed = subprocess.run(
                list(invocation.command),
                cwd=invocation.cwd,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            returncode = completed.returncode
            error = None if returncode == 0 else _process_error(returncode, stderr)
        except subprocess.TimeoutExpired as expired:
            stdout = _text_output(expired.stdout)
            stderr = _text_output(expired.stderr)
            returncode = 124
            error = f"timed out after {timeout:g}s"
        except OSError as error:
            stdout = ""
            stderr = ""
            returncode = 127
            error = f"could not start component: {error}"

        artifacts: tuple[ArtifactCapture, ...] = ()
        if returncode == 0:
            try:
                artifacts = _capture_artifacts(invocation, captured_root)
            except (OSError, ValueError) as capture_error:
                returncode = 1
                error = str(capture_error)

        finished_at = _timestamp()
        return ComponentResult(
            name=invocation.name,
            command=invocation.command,
            status="completed" if returncode == 0 else "failed",
            returncode=returncode,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=round(time.monotonic() - started_monotonic, 6),
            stdout=stdout,
            stderr=stderr,
            artifacts=artifacts,
            error=error,
        )

    def _write_summary(
        self,
        result: LocalPipelineResult,
        summary_path: Path | None,
    ) -> LocalPipelineResult:
        destination = Path(summary_path) if summary_path is not None else self.run_root / "run-summary.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return LocalPipelineResult(
            run_id=result.run_id,
            status=result.status,
            run_root=result.run_root,
            components=result.components,
            failed_component=result.failed_component,
            skipped_components=result.skipped_components,
            summary_path=destination,
        )


def python_module_invocation(
    name: str,
    module: str,
    arguments: Sequence[str] = (),
    *,
    output_paths: Mapping[str, Path] | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    python_executable: str | Path | None = None,
    timeout_seconds: float | None = None,
) -> ComponentInvocation:
    """Build an invocation for the same ``python -m`` component entrypoint."""

    executable = str(python_executable or sys.executable)
    return ComponentInvocation(
        name=name,
        command=(executable, "-m", module, *(str(argument) for argument in arguments)),
        output_paths=output_paths or {},
        environment=environment or {},
        cwd=cwd,
        timeout_seconds=timeout_seconds,
    )


def _validate_ordered_invocations(invocations: Sequence[ComponentInvocation]) -> None:
    names = [invocation.name for invocation in invocations]
    if len(names) != len(set(names)):
        raise ValueError("component names must be unique within one local run")


def _is_path_segment(value: str) -> bool:
    return bool(value) and value not in {".", ".."} and "/" not in value and "\\" not in value and not any(
        character.isspace() for character in value
    )


def _capture_artifacts(
    invocation: ComponentInvocation,
    captured_root: Path,
) -> tuple[ArtifactCapture, ...]:
    captures: list[ArtifactCapture] = []
    for name, source_path in invocation.output_paths.items():
        source = Path(source_path)
        if not source.exists():
            raise ValueError(f"component {invocation.name} did not publish declared artifact {name}: {source}")
        destination = captured_root / invocation.name / name
        if _is_within(destination, source) or _is_within(source, destination):
            raise ValueError(f"capture path overlaps declared artifact {name}: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
            kind = "directory"
        else:
            shutil.copy2(source, destination)
            kind = "file"
        digest, byte_count = _digest_path(destination)
        captures.append(
            ArtifactCapture(
                name=name,
                source_path=source,
                capture_path=destination,
                sha256=digest,
                bytes=byte_count,
                kind=kind,
            )
        )
    return tuple(captures)


def _digest_path(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    byte_count = 0
    if path.is_file():
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                byte_count += len(chunk)
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}", byte_count
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        relative = child.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        child_digest, child_bytes = _digest_path(child)
        digest.update(child_digest.encode("ascii"))
        byte_count += child_bytes
    return f"sha256:{digest.hexdigest()}", byte_count


def _process_error(returncode: int, stderr: str) -> str:
    detail = stderr.strip().splitlines()
    return f"exit code {returncode}" if not detail else f"exit code {returncode}: {detail[-1][:512]}"


def _text_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def _display_path(path: Path, root: Path | None) -> str:
    if root is None:
        return str(path)
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
