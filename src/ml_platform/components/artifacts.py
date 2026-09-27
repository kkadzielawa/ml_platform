"""Filesystem-backed artifact helpers for local component execution."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse


class ArtifactError(ValueError):
    """Raised when an artifact URI cannot be used by the local SDK."""


@dataclass(frozen=True)
class Artifact:
    """A named durable artifact location.

    The local runner intentionally supports only ``file://`` URIs.  Object
    storage adapters can implement the same interface later without making
    local tests depend on a service.
    """

    name: str
    uri: str

    def __post_init__(self) -> None:
        if not self.name or any(character.isspace() for character in self.name):
            raise ArtifactError("artifact name must be non-empty and contain no whitespace")
        if not self.uri or any(character.isspace() for character in self.uri):
            raise ArtifactError("artifact URI must be non-empty and contain no whitespace")

    def local_path(self) -> Path:
        parsed = urlparse(self.uri)
        if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
            raise ArtifactError(
                f"local execution supports only file:// artifacts, got {self.uri!r}"
            )
        path = Path(unquote(parsed.path))
        if not path.is_absolute():
            raise ArtifactError(f"file artifact URI must be absolute: {self.uri!r}")
        return path


def download_file(artifact: Artifact, destination: Path) -> Path:
    """Copy a local artifact into a component's working directory."""

    source = artifact.local_path()
    if not source.is_file():
        raise ArtifactError(f"input artifact does not exist: {artifact.uri}")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_copy(source, destination)
    return destination


def upload_file(source: Path, artifact: Artifact) -> Path:
    """Publish a local file to a declared local artifact URI atomically."""

    source = Path(source)
    if not source.is_file():
        raise ArtifactError(f"upload source does not exist: {source}")
    destination = artifact.local_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        return destination
    _atomic_copy(source, destination)
    return destination


def _atomic_copy(source: Path, destination: Path) -> None:
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=f".{destination.name}.", suffix=".partial", delete=False
        ) as temporary:
            temporary_path = temporary.name
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        shutil.copystat(source, temporary_path, follow_symlinks=True)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
