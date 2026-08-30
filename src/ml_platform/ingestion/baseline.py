"""Versioned lakeFS ingestion for the baseline housing-sale dataset."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from ml_platform.data import write_baseline_parquet_dataset
from ml_platform.data.transforms import DATASET_ID, DATASET_VERSION, prefixed_sha256
from ml_platform.data_quality import validate_housing_sale_dataset
from ml_platform.ingestion.lakefs_client import LakeFSClient, LakeFSNotFoundError
from ml_platform.lineage import build_complete_event, build_fail_event, build_ingestion_start_event
from ml_platform.run_manifest.validation import validate_manifest


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_PATHS = {
    "train": REPO_ROOT / "examples/sklearn_baseline/data/train.csv",
    "test": REPO_ROOT / "examples/sklearn_baseline/data/test.csv",
}
RUN_MANIFEST_SCHEMA_PATH = REPO_ROOT / "contracts/run-manifest.schema.json"
DEFAULT_OUTPUT_PATH = Path(os.environ.get("BASELINE_INGESTION_MANIFEST", "/tmp/ml-platform-baseline-ingestion/run-manifest.json"))
RAW_PREFIX = f"raw/housing-sale/{DATASET_VERSION}"
CURATED_PREFIX = f"curated/{DATASET_ID}/{DATASET_VERSION}"


class LakeFSLike(Protocol):
    def setup(self) -> None: ...
    def ensure_repository(self, repository: str, *, storage_namespace: str) -> None: ...
    def branch_head(self, repository: str, branch: str) -> str | None: ...
    def create_branch(self, repository: str, branch: str, source: str) -> None: ...
    def upload_file(self, repository: str, branch: str, path: str, local_path: Path) -> None: ...
    def get_object(self, repository: str, ref: str, path: str) -> bytes: ...
    def commit(self, repository: str, branch: str, *, message: str, metadata: dict[str, str]) -> str: ...
    def merge(self, repository: str, source_ref: str, destination_branch: str) -> None: ...


class LineageCollectorLike(Protocol):
    def emit(self, event: dict) -> None: ...


@dataclass(frozen=True)
class BaselineIngestionResult:
    """Summary returned by the baseline ingestion workflow."""

    run_id: str
    repository: str
    branch: str | None
    lakefs_commit_id: str | None
    manifest_path: Path
    no_op: bool


@dataclass(frozen=True)
class ExistingCuratedDataset:
    commit_id: str
    total_rows: int
    metadata_checksum: str


def run_baseline_ingestion(
    *,
    input_paths: dict[str, Path] | None = None,
    repository: str = "housing-sale-ingestion",
    storage_namespace: str | None = None,
    output_manifest_path: Path = DEFAULT_OUTPUT_PATH,
    client: LakeFSLike | None = None,
    lineage_collector: LineageCollectorLike | None = None,
) -> BaselineIngestionResult:
    """Ingest baseline CSV files into lakeFS and emit a universal run manifest."""

    started_at = utc_now()
    run_id = build_run_id(started_at)
    source_paths = {split: Path(path) for split, path in (input_paths or DEFAULT_INPUT_PATHS).items()}
    source_checksums = {split: prefixed_sha256(path) for split, path in sorted(source_paths.items())}
    source_revision_id = source_revision(source_checksums)
    branch = f"ingest-{DATASET_VERSION}-{source_revision_id[-8:]}"
    storage_namespace = storage_namespace or f"s3://ml-platform-artifacts/lakefs/{repository}/"
    lakefs = client or LakeFSClient.from_environment()

    source_uris = [f"s3://ml-platform-artifacts/lakefs/{repository}/{RAW_PREFIX}/{split}.csv" for split in sorted(source_paths)]
    emit_lineage(
        lineage_collector,
        build_ingestion_start_event(
            run_id=run_id,
            started_at=isoformat_z(started_at),
            repository=repository,
            source_uris=source_uris,
            source_revision=source_revision_id,
        ),
    )

    try:
        lakefs.setup()
        lakefs.ensure_repository(repository, storage_namespace=storage_namespace)

        existing_dataset = matching_curated_dataset(lakefs, repository, source_checksums)
        if existing_dataset is not None:
            finished_at = utc_now()
            manifest = build_run_manifest(
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                repository=repository,
                branch=None,
                source_checksums=source_checksums,
                source_revision_id=source_revision_id,
                lakefs_commit_id=existing_dataset.commit_id,
                no_op=True,
                total_rows=existing_dataset.total_rows,
                output_checksum=existing_dataset.metadata_checksum,
            )
            write_valid_manifest(manifest, output_manifest_path)
            emit_lineage(lineage_collector, build_complete_event(manifest))
            return BaselineIngestionResult(
                run_id=manifest["run_id"],
                repository=repository,
                branch=None,
                lakefs_commit_id=existing_dataset.commit_id,
                manifest_path=output_manifest_path,
                no_op=True,
            )

        with tempfile.TemporaryDirectory(prefix="ml-platform-ingest-") as tmp:
            tmp_dir = Path(tmp)
            curated_dir = tmp_dir / "curated"
            transform_result = write_baseline_parquet_dataset(source_paths, curated_dir)
            quality_result = validate_housing_sale_dataset(transform_result.output_dir)
            if not quality_result.success:
                raise ValueError("baseline data-quality validation failed; lakeFS commit was not created")

            source_ref = lakefs.branch_head(repository, "main") or "main"
            create_branch_from_source(lakefs, repository, branch, source_ref)

            for split, path in source_paths.items():
                lakefs.upload_file(repository, branch, f"{RAW_PREFIX}/{split}.csv", path)
            for path in sorted(transform_result.output_dir.glob("**/*")):
                if path.is_file():
                    lakefs.upload_file(repository, branch, f"{CURATED_PREFIX}/{path.relative_to(transform_result.output_dir).as_posix()}", path)

            commit_id = lakefs.commit(
                repository,
                branch,
                message=f"ingest {DATASET_ID} {DATASET_VERSION}",
                metadata={
                    "issue": "03.08",
                    "dataset_id": DATASET_ID,
                    "dataset_version": DATASET_VERSION,
                    "source_revision": source_revision_id,
                },
            )
            lakefs.merge(repository, commit_id, "main")
            finished_at = utc_now()
            manifest = build_run_manifest(
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                repository=repository,
                branch=branch,
                source_checksums=source_checksums,
                source_revision_id=source_revision_id,
                lakefs_commit_id=commit_id,
                no_op=False,
                total_rows=transform_result.metadata["total_rows"],
                output_checksum=transform_result.metadata["metadata_sha256"],
            )
            write_valid_manifest(manifest, output_manifest_path)
            emit_lineage(lineage_collector, build_complete_event(manifest))

        return BaselineIngestionResult(
            run_id=manifest["run_id"],
            repository=repository,
            branch=branch,
            lakefs_commit_id=commit_id,
            manifest_path=output_manifest_path,
            no_op=False,
        )
    except Exception as exc:
        emit_lineage(
            lineage_collector,
            build_fail_event(
                run_id=run_id,
                started_at=isoformat_z(started_at),
                input_uris=source_uris,
                message=str(exc),
            ),
        )
        raise


def create_branch_from_source(client: LakeFSLike, repository: str, branch: str, source_ref: str) -> None:
    try:
        client.create_branch(repository, branch, source_ref)
    except Exception:
        if source_ref != "main":
            raise
        client.upload_file(repository, "main", ".lakefs/bootstrap.txt", REPO_ROOT / "docs/README.md")
        bootstrap_commit = client.commit(
            repository,
            "main",
            message="bootstrap repository for versioned ingestion",
            metadata={"issue": "03.08", "purpose": "bootstrap"},
        )
        client.create_branch(repository, branch, bootstrap_commit)


def matching_curated_dataset(client: LakeFSLike, repository: str, source_checksums: dict[str, str]) -> ExistingCuratedDataset | None:
    try:
        content = client.get_object(repository, "main", f"{CURATED_PREFIX}/_metadata.json")
    except LakeFSNotFoundError:
        return None

    metadata = json.loads(content)
    if metadata.get("input_checksums") != source_checksums:
        return None
    commit_id = client.branch_head(repository, "main")
    if commit_id is None:
        return None
    return ExistingCuratedDataset(
        commit_id=commit_id,
        total_rows=int(metadata["total_rows"]),
        metadata_checksum=metadata["metadata_sha256"],
    )


def write_valid_manifest(manifest: dict, path: Path) -> None:
    schema = json.loads(RUN_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_manifest(manifest, schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(manifest, indent=2, sort_keys=True)}\n", encoding="utf-8")


def build_run_manifest(
    *,
    run_id: str,
    started_at: datetime,
    finished_at: datetime,
    repository: str,
    branch: str | None,
    source_checksums: dict[str, str],
    source_revision_id: str,
    lakefs_commit_id: str,
    no_op: bool,
    total_rows: int,
    output_checksum: str,
) -> dict:
    source_uri = f"s3://ml-platform-artifacts/lakefs/{repository}/{RAW_PREFIX}/"
    target_uri = f"s3://ml-platform-artifacts/lakefs/{repository}/{CURATED_PREFIX}/"
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "owner": "study",
        "project": "ml-platform",
        "environment": "local",
        "parent_run_id": None,
        "timestamps": {
            "started_at": isoformat_z(started_at),
            "finished_at": isoformat_z(finished_at),
        },
        "correlation": {
            "trace_id": uuid.uuid4().hex,
            "correlation_id": f"baseline-ingestion-{source_revision_id[-8:]}",
        },
        "code": git_code_metadata(),
        "images": local_python_image_refs(),
        "artifacts": {
            "inputs": [
                {
                    "name": f"housing-sale-source-{split}",
                    "kind": "dataset",
                    "uri": f"s3://ml-platform-artifacts/lakefs/{repository}/{RAW_PREFIX}/{split}.csv",
                    "checksum": checksum,
                    "schema_ref": "https://example.local/ml-platform-study/contracts/dataset.schema.json",
                    "data_revision": {
                        "type": "object-version",
                        "id": source_revision_id,
                    },
                }
                for split, checksum in sorted(source_checksums.items())
            ],
            "outputs": [
                {
                    "name": DATASET_ID,
                    "kind": "dataset",
                    "uri": target_uri,
                    "checksum": output_checksum,
                    "schema_ref": "https://example.local/ml-platform-study/contracts/dataset.schema.json",
                    "data_revision": {
                        "type": "lakefs-commit",
                        "id": lakefs_commit_id,
                    },
                }
            ],
        },
        "model": {
            "name": "not-applicable",
            "version": "0.0.0",
            "license": "not-applicable",
            "tokenizer": None,
            "embedding_model": None,
            "prompt_version": None,
            "index_version": None,
        },
        "reproducibility": {
            "hardware": {
                "cpu": platform.processor() or platform.machine() or "local-cpu",
                "memory_gib": memory_gib(),
                "gpu": None,
            },
            "driver_runtime_versions": {
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "random_seeds": {},
        },
        "parameters": {
            "dataset_id": DATASET_ID,
            "dataset_version": DATASET_VERSION,
            "lakefs_repository": repository,
            "lakefs_branch": branch,
            "source_revision": source_revision_id,
            "no_op": no_op,
        },
        "metrics": {
            "input_file_count": float(len(source_checksums)),
            "curated_row_count": float(total_rows),
        },
        "evaluation_results": [
            {
                "name": "data-quality",
                "metric": "validation-success",
                "value": 1.0,
                "unit": "boolean",
                "threshold": "==1",
                "passed": True,
            }
        ],
        "policy_decisions": [
            {
                "name": "quality-gate",
                "decision": "allow",
                "reason": "Curated data is committed only after schema transform and quality validation succeed.",
            }
        ],
        "approval": {
            "required": False,
            "approved_by": None,
            "approved_at": None,
        },
        "lineage_events": [
            {
                "event_type": "ingested",
                "event_time": isoformat_z(finished_at),
                "source": source_uri,
                "target": target_uri,
            }
        ],
        "retention": {
            "security_classification": "internal",
            "retain_until": "2027-08-27",
        },
    }


def source_revision(source_checksums: dict[str, str]) -> str:
    payload = json.dumps(source_checksums, sort_keys=True).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def build_run_id(started_at: datetime) -> str:
    return f"run-{started_at.strftime('%Y%m%dt%H%M%Sz')}-{uuid.uuid4().hex[:8]}"


def emit_lineage(lineage_collector: LineageCollectorLike | None, event: dict) -> None:
    if lineage_collector is not None:
        lineage_collector.emit(event)


def git_code_metadata() -> dict:
    return {
        "repository": git_remote_url(),
        "commit": git_output("rev-parse", "HEAD", fallback="0" * 40),
        "dirty_worktree": bool(git_output("status", "--short", fallback="")),
        "dependency_lockfile_hash": prefixed_sha256(REPO_ROOT / "config/versions.yaml"),
    }


def git_remote_url() -> str:
    remote = git_output("config", "--get", "remote.origin.url", fallback="https://github.com/kkadzielawa/ml_platform")
    if remote.startswith("git@github.com:"):
        return "https://github.com/" + remote.removeprefix("git@github.com:").removesuffix(".git")
    return remote.removesuffix(".git")


def git_output(*args: str, fallback: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return fallback
    return result.stdout.strip()


def local_python_image_refs() -> dict:
    digest = f"sha256:{hashlib.sha256(sys.version.encode('utf-8')).hexdigest()}"
    ref = {
        "repository": "local/python",
        "tag": platform.python_version(),
        "digest": digest,
        "sbom": "file:///tmp/ml-platform-baseline-ingestion/python.spdx.json",
        "signature": "file:///tmp/ml-platform-baseline-ingestion/python.sig",
    }
    return {"source": ref, "output": dict(ref)}


def memory_gib() -> float:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return 0.0
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            kib = int(line.split()[1])
            return round(kib / 1024 / 1024, 2)
    return 0.0


def utc_now() -> datetime:
    return datetime.now(tz=UTC).replace(microsecond=0)


def isoformat_z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
