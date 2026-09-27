"""Wrap deterministic Polars/DuckDB transforms in an atomic component run."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import re

from ml_platform.data import write_baseline_parquet_dataset


_RUN_ID = re.compile(r"^run-\d{8}t\d{6}z-[0-9a-f]{8}$")


class TransformError(ValueError):
    """Raised when a transform declaration or publication is invalid."""


@dataclass(frozen=True)
class TransformRequest:
    """Inputs and configuration for one run-scoped deterministic transform."""

    run_id: str
    input_paths: Mapping[str, Path]
    output_root: Path
    config: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not _RUN_ID.fullmatch(self.run_id):
            raise TransformError("run_id must match run-YYYYMMDDtHHMMSSz-<8 lowercase hex>")
        if not self.input_paths:
            raise TransformError("at least one named input is required")
        if any(not name or any(character.isspace() for character in name) for name in self.input_paths):
            raise TransformError("input names must be non-empty and contain no whitespace")
        for name, path in self.input_paths.items():
            input_path = Path(path)
            if not input_path.is_file():
                raise TransformError(f"input file does not exist for {name}: {input_path}")
        try:
            json.dumps(self.config, sort_keys=True)
        except (TypeError, ValueError) as error:
            raise TransformError("transform config must be JSON-serializable") from error


@dataclass(frozen=True)
class TransformResult:
    """Published run-scoped curated dataset and its metadata."""

    run_id: str
    output_dir: Path
    manifest_path: Path
    manifest: dict[str, Any]


def run_transform_component(request: TransformRequest) -> TransformResult:
    """Transform inputs into an atomically published run-scoped output."""

    request.validate()
    output_root = Path(request.output_root).resolve()
    final_root = output_root / request.run_id
    if final_root.exists():
        raise TransformError(f"run output already exists: {final_root}")

    output_root.mkdir(parents=True, exist_ok=True)
    staging_root = Path(tempfile.mkdtemp(prefix=f".{request.run_id}.", dir=output_root))
    try:
        curated_dir = staging_root / "curated"
        transform_result = write_baseline_parquet_dataset(
            {name: Path(path) for name, path in sorted(request.input_paths.items())},
            curated_dir,
        )
        manifest = build_transform_manifest(request, staging_root, transform_result.metadata)
        manifest["output_uri"] = (final_root / "curated").resolve().as_uri()
        manifest_path = staging_root / "transform-manifest.json"
        _write_json(manifest_path, manifest)
        staging_root.replace(final_root)
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise

    return TransformResult(
        run_id=request.run_id,
        output_dir=final_root / "curated",
        manifest_path=final_root / "transform-manifest.json",
        manifest=manifest,
    )


def build_transform_manifest(
    request: TransformRequest,
    staging_root: Path,
    transform_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Build compact checksums/schema evidence without row-level values."""

    curated_dir = staging_root / "curated"
    output_files = [
        {
            "path": path.relative_to(staging_root).as_posix(),
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(curated_dir.rglob("*.parquet"))
    ]
    if not output_files:
        raise TransformError("transform produced no parquet outputs")
    input_files = [
        {"name": name, "sha256": _sha256_file(Path(path))}
        for name, path in sorted(request.input_paths.items())
    ]
    config_hash = _sha256_bytes(json.dumps(request.config, sort_keys=True).encode("utf-8"))
    return {
        "schema_version": "1.0.0",
        "component": "dataset-transform",
        "status": "complete",
        "run_id": request.run_id,
        "output_uri": (staging_root / "curated").resolve().as_uri(),
        "config_sha256": config_hash,
        "inputs": input_files,
        "outputs": output_files,
        "schema_hash": transform_metadata["schema_hash"],
        "row_counts": transform_metadata["row_counts"],
        "total_rows": transform_metadata["total_rows"],
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".partial",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            json.dump(payload, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        Path(temporary_path).replace(path)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def main(argv: list[str] | None = None) -> int:
    """Run the baseline transform from local CSV inputs."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    run_transform_component(
        TransformRequest(
            run_id=arguments.run_id,
            input_paths={"train": arguments.train, "test": arguments.test},
            output_root=arguments.output_root,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
