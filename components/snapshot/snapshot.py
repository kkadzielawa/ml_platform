"""Resolve a mutable lakeFS reference to an immutable commit metadata artifact."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


class SnapshotError(RuntimeError):
    """Raised when a lakeFS reference cannot be resolved to a commit."""


class LakeFSReferenceClient(Protocol):
    """Minimum lakeFS client surface needed by this component."""

    def branch_head(self, repository: str, branch: str) -> str | None: ...


@dataclass(frozen=True)
class SnapshotRequest:
    """A mutable lakeFS reference and the logical dataset it represents."""

    repository: str
    reference: str
    dataset_path: str = ""

    def validate(self) -> None:
        if not self.repository or any(character.isspace() for character in self.repository):
            raise SnapshotError("repository must be a non-empty name without whitespace")
        if not self.reference or any(character.isspace() for character in self.reference):
            raise SnapshotError("reference must be a non-empty branch or dataset reference")
        if any(character.isspace() for character in self.dataset_path):
            raise SnapshotError("dataset_path must not contain whitespace")


@dataclass(frozen=True)
class SnapshotMetadata:
    """Immutable metadata emitted after a reference is successfully resolved."""

    repository: str
    reference: str
    commit_id: str
    dataset_path: str
    resolved_at: str
    schema_version: str = "1.0.0"

    def as_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "repository": self.repository,
            "reference": self.reference,
            "commit_id": self.commit_id,
            "dataset_path": self.dataset_path,
            "resolved_at": self.resolved_at,
        }


@dataclass(frozen=True)
class SnapshotResult:
    """Result returned after metadata has been durably published."""

    metadata: SnapshotMetadata
    artifact_path: Path


def resolve_snapshot(
    client: LakeFSReferenceClient,
    request: SnapshotRequest,
) -> SnapshotMetadata:
    """Resolve a mutable reference without reading or copying dataset objects."""

    request.validate()
    try:
        commit_id = client.branch_head(request.repository, request.reference)
    except Exception as error:
        raise SnapshotError(
            f"could not resolve {request.repository!r}/{request.reference!r}: {error}"
        ) from error
    if not isinstance(commit_id, str) or not commit_id:
        raise SnapshotError(
            f"lakeFS reference not found: {request.repository!r}/{request.reference!r}"
        )
    return SnapshotMetadata(
        repository=request.repository,
        reference=request.reference,
        commit_id=commit_id,
        dataset_path=request.dataset_path,
        resolved_at=_timestamp(),
    )


def write_snapshot_artifact(metadata: SnapshotMetadata, output_path: Path) -> Path:
    """Atomically publish metadata only after reference resolution succeeds."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".partial",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            json.dump(metadata.as_dict(), temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        Path(temporary_path).replace(output_path)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
    return output_path


def run_snapshot_component(
    client: LakeFSReferenceClient,
    request: SnapshotRequest,
    output_path: Path,
) -> SnapshotResult:
    """Resolve the reference and publish its metadata artifact."""

    metadata = resolve_snapshot(client, request)
    artifact_path = write_snapshot_artifact(metadata, output_path)
    return SnapshotResult(metadata=metadata, artifact_path=artifact_path)


def _timestamp() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    """Run against the configured local lakeFS service."""

    import argparse

    from ml_platform.ingestion.lakefs_client import LakeFSClient

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--reference", default="main")
    parser.add_argument("--dataset-path", default="")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    run_snapshot_component(
        LakeFSClient.from_environment(),
        SnapshotRequest(
            repository=arguments.repository,
            reference=arguments.reference,
            dataset_path=arguments.dataset_path,
        ),
        arguments.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
