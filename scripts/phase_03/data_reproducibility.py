"""Prove that a curated Parquet release can be read again by lakeFS commit ID.

This is a deliberately small end-to-end study workflow. It publishes two
complete Parquet releases, records a run manifest and OpenLineage events for
each, then reads the first release after the second exists.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from ml_platform.data.transforms import prefixed_sha256, write_baseline_parquet_dataset
from ml_platform.ingestion.baseline import (
    DEFAULT_INPUT_PATHS,
    build_run_id,
    build_run_manifest,
    source_revision,
    write_valid_manifest,
)
from ml_platform.ingestion.lakefs_client import LakeFSClient, lakefs_port_forward
from ml_platform.lineage import events_for_successful_manifest


DEFAULT_REPORT_PATH = Path("/tmp/ml-platform-data-reproducibility/latest.json")
DATASET_ID = "housing-sale-features"
SOURCE_PREFIX = "raw/housing-sale"
CURATED_PREFIX = f"curated/{DATASET_ID}"
EVIDENCE_PREFIX = "evidence/data-reproducibility"


@dataclass(frozen=True)
class Release:
    """Immutable references and measurements for one published release."""

    dataset_version: str
    source_version: str
    data_commit: str
    evidence_commit: str
    manifest_path: str
    lineage_path: str
    schema: dict[str, str]
    row_count: int
    content_checksum: str


def main() -> None:
    report_path = Path(os.environ.get("DATA_REPRODUCIBILITY_REPORT", DEFAULT_REPORT_PATH))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    repository = f"study-data-reproducibility-{uuid.uuid4().hex[:12]}"
    report: dict[str, Any] = {
        "issue": "03.12",
        "status": "running",
        "repository": repository,
        "table_route": "parquet-lakefs",
        "generated_at": utc_now(),
        "releases": {},
        "reproduction": {},
        "checks": {},
        "cleanup": {"repository_deleted": False},
    }
    client: LakeFSClient | None = None

    try:
        with tempfile.TemporaryDirectory(prefix="ml-platform-data-reproducibility-") as temporary_directory:
            work_dir = Path(temporary_directory)
            first_inputs = copy_source_version(work_dir, source_version="v0001")
            second_inputs = copy_source_version(work_dir, source_version="v0002", revise_listing_price=True)
            client = LakeFSClient.from_environment()

            with lakefs_port_forward():
                wait_for_lakefs(client)
                client.setup()
                client.ensure_repository(
                    repository,
                    storage_namespace=f"s3://ml-platform-artifacts/lakefs/{repository}/",
                )
                first = publish_release(
                    client,
                    repository=repository,
                    dataset_version="v0001",
                    source_version="v0001",
                    source_paths=first_inputs,
                    work_dir=work_dir,
                )
                second = publish_release(
                    client,
                    repository=repository,
                    dataset_version="v0002",
                    source_version="v0002",
                    source_paths=second_inputs,
                    work_dir=work_dir,
                )
                reproduced = read_release(client, repository, first.data_commit, first.dataset_version)

            assert reproduced["schema"] == first.schema, "schema changed when reading the original commit"
            assert reproduced["row_count"] == first.row_count, "row count changed when reading the original commit"
            assert reproduced["content_checksum"] == first.content_checksum, "content changed when reading the original commit"
            assert first.data_commit != second.data_commit, "two publications must have distinct commits"
            assert first.content_checksum != second.content_checksum, "second source version must alter curated content"
            report["releases"] = {"first": release_record(repository, first), "second": release_record(repository, second)}
            report["reproduction"] = {"read_ref": first.data_commit, "dataset_version": first.dataset_version, **reproduced}
            report["checks"] = {
                "first_release_reproduced_by_immutable_commit": True,
                "schema_matches": True,
                "row_count_matches": True,
                "content_checksum_matches": True,
                "second_release_differs": True,
            }
            report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        if client is not None and os.environ.get("KEEP_DATA_REPRODUCIBILITY_REPOSITORY") != "1":
            try:
                with lakefs_port_forward():
                    delete_repository_if_exists(client, repository)
                report["cleanup"] = {"repository_deleted": True}
            except Exception as cleanup_error:
                report["cleanup"] = {"repository_deleted": False, "error": str(cleanup_error)}
        elif client is not None:
            report["cleanup"] = {"repository_deleted": False, "retained_for_inspection": True}
        write_report(report, report_path)
        print(f"Data reproducibility report written to {report_path}")


def copy_source_version(work_dir: Path, *, source_version: str, revise_listing_price: bool = False) -> dict[str, Path]:
    """Copy the stable fixture and make one transparent revision for source v0002."""

    destination = work_dir / "sources" / source_version
    destination.mkdir(parents=True, exist_ok=True)
    copied: dict[str, Path] = {}
    for split, source_path in DEFAULT_INPUT_PATHS.items():
        target = destination / f"{split}.csv"
        shutil.copyfile(source_path, target)
        copied[split] = target
    if revise_listing_price:
        train_path = copied["train"]
        original = train_path.read_text(encoding="utf-8")
        revised = original.replace("listing-0002,813000,", "listing-0002,825000,", 1)
        if original == revised:
            raise RuntimeError("expected to revise listing-0002 in the baseline train source")
        train_path.write_text(revised, encoding="utf-8")
    return copied


def publish_release(
    client: LakeFSClient,
    *,
    repository: str,
    dataset_version: str,
    source_version: str,
    source_paths: dict[str, Path],
    work_dir: Path,
) -> Release:
    """Publish one immutable source/curated pair, then write its evidence objects."""

    started_at = datetime.now(UTC)
    output_dir = work_dir / f"curated-{dataset_version}"
    transform = write_baseline_parquet_dataset(source_paths, output_dir)
    metadata = set_dataset_version(transform.metadata_path, dataset_version)
    for split, path in sorted(source_paths.items()):
        client.upload_file(repository, "main", f"{SOURCE_PREFIX}/{source_version}/{split}.csv", path)
    for path in sorted(output_dir.glob("**/*")):
        if path.is_file():
            client.upload_file(repository, "main", f"{CURATED_PREFIX}/{dataset_version}/{path.relative_to(output_dir).as_posix()}", path)
    data_commit = client.commit(
        repository,
        "main",
        message=f"publish {DATASET_ID} {dataset_version} from source {source_version}",
        metadata={"issue": "03.12", "dataset_version": dataset_version, "source_version": source_version, "table_route": "parquet-lakefs"},
    )
    source_checksums = {split: prefixed_sha256(path) for split, path in sorted(source_paths.items())}
    manifest_path, lineage_path = write_evidence(
        repository=repository,
        dataset_version=dataset_version,
        source_version=source_version,
        source_checksums=source_checksums,
        data_commit=data_commit,
        metadata=metadata,
        output_dir=output_dir,
        started_at=started_at,
        work_dir=work_dir,
    )
    client.upload_file(repository, "main", manifest_path, work_dir / manifest_path)
    client.upload_file(repository, "main", lineage_path, work_dir / lineage_path)
    evidence_commit = client.commit(
        repository,
        "main",
        message=f"record reproducibility evidence for {DATASET_ID} {dataset_version}",
        metadata={"issue": "03.12", "dataset_version": dataset_version, "data_commit": data_commit},
    )
    return Release(
        dataset_version=dataset_version,
        source_version=source_version,
        data_commit=data_commit,
        evidence_commit=evidence_commit,
        manifest_path=manifest_path,
        lineage_path=lineage_path,
        **release_signature(output_dir, metadata),
    )


def write_evidence(
    *,
    repository: str,
    dataset_version: str,
    source_version: str,
    source_checksums: dict[str, str],
    data_commit: str,
    metadata: dict[str, Any],
    output_dir: Path,
    started_at: datetime,
    work_dir: Path,
) -> tuple[str, str]:
    """Create contract-valid manifest and OpenLineage evidence that pin the data commit."""

    run_id = build_run_id(started_at)
    manifest = build_run_manifest(
        run_id=run_id,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        repository=repository,
        branch="main",
        source_checksums=source_checksums,
        source_revision_id=source_revision(source_checksums),
        lakefs_commit_id=data_commit,
        no_op=False,
        total_rows=int(metadata["total_rows"]),
        output_checksum=release_signature(output_dir, metadata)["content_checksum"],
    )
    for artifact in manifest["artifacts"]["inputs"]:
        split = artifact["name"].removeprefix("housing-sale-source-")
        artifact["uri"] = f"s3://ml-platform-artifacts/lakefs/{repository}/{SOURCE_PREFIX}/{source_version}/{split}.csv"
        artifact["data_revision"] = {"type": "lakefs-commit", "id": data_commit}
    output = manifest["artifacts"]["outputs"][0]
    output["uri"] = f"s3://ml-platform-artifacts/lakefs/{repository}/{CURATED_PREFIX}/{dataset_version}/"
    output["data_revision"] = {"type": "lakefs-commit", "id": data_commit}
    manifest["parameters"].update({"dataset_version": dataset_version, "source_version": source_version, "lakefs_commit": data_commit, "publication_rule": "new-complete-version"})
    manifest["lineage_events"][0]["source"] = f"s3://ml-platform-artifacts/lakefs/{repository}/{SOURCE_PREFIX}/{source_version}/"
    manifest["lineage_events"][0]["target"] = f"s3://ml-platform-artifacts/lakefs/{repository}/{CURATED_PREFIX}/{dataset_version}/"
    manifest_relative_path = f"{EVIDENCE_PREFIX}/runs/{run_id}/run-manifest.json"
    lineage_relative_path = f"{EVIDENCE_PREFIX}/runs/{run_id}/openlineage-events.jsonl"
    manifest_local_path = work_dir / manifest_relative_path
    lineage_local_path = work_dir / lineage_relative_path
    write_valid_manifest(manifest, manifest_local_path)
    lineage_local_path.parent.mkdir(parents=True, exist_ok=True)
    lineage_events = events_for_successful_manifest(manifest)
    lineage_local_path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in lineage_events) + "\n", encoding="utf-8")
    return manifest_relative_path, lineage_relative_path


def set_dataset_version(metadata_path: Path, dataset_version: str) -> dict[str, Any]:
    """Make local metadata reflect its immutable publication prefix."""

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["version"] = dataset_version
    metadata.pop("metadata_sha256", None)
    canonical = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    metadata["metadata_sha256"] = prefixed_sha256_bytes(canonical.encode("utf-8"))
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def read_release(client: LakeFSClient, repository: str, commit: str, dataset_version: str) -> dict[str, Any]:
    """Read Parquet only through a recorded commit, never the moving main branch."""

    prefix = f"{CURATED_PREFIX}/{dataset_version}"
    metadata = json.loads(client.get_object(repository, commit, f"{prefix}/_metadata.json"))
    files = {item["path"]: client.get_object(repository, commit, f"{prefix}/{item['path']}") for item in metadata["output_files"]}
    frame = pl.concat([pl.read_parquet(io.BytesIO(content)) for content in files.values()]).sort("listing_id")
    return {"schema": {name: str(dtype) for name, dtype in frame.schema.items()}, "row_count": frame.height, "content_checksum": content_checksum(files)}


def release_signature(output_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    files = {item["path"]: (output_dir / item["path"]).read_bytes() for item in metadata["output_files"]}
    frame = pl.concat([pl.read_parquet(io.BytesIO(content)) for content in files.values()]).sort("listing_id")
    return {"schema": {name: str(dtype) for name, dtype in frame.schema.items()}, "row_count": frame.height, "content_checksum": content_checksum(files)}


def content_checksum(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path, content in sorted(files.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def release_record(repository: str, release: Release) -> dict[str, Any]:
    """Use explicit repository/ref/path triplets to link evidence in lakeFS."""

    return {
        "dataset_version": release.dataset_version,
        "source_version": release.source_version,
        "data_commit": release.data_commit,
        "evidence_commit": release.evidence_commit,
        "run_manifest": {"repository": repository, "ref": release.evidence_commit, "path": release.manifest_path},
        "lineage_events": {"repository": repository, "ref": release.evidence_commit, "path": release.lineage_path},
        "schema": release.schema,
        "row_count": release.row_count,
        "content_checksum": release.content_checksum,
    }


def wait_for_lakefs(client: LakeFSClient) -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{client.endpoint}/_health", timeout=2):
                return
        except urllib.error.URLError:
            time.sleep(1)
    raise TimeoutError("lakeFS health endpoint did not become available")


def delete_repository_if_exists(client: LakeFSClient, repository: str) -> None:
    try:
        client.request("DELETE", f"/repositories/{repository}")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise


def write_report(report: dict[str, Any], report_path: Path) -> None:
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prefixed_sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    main()
