from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ml_platform.data.transforms import DATASET_ID
from ml_platform.ingestion.baseline import CURATED_PREFIX, run_baseline_ingestion
from ml_platform.ingestion.lakefs_client import LakeFSNotFoundError


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DATA = REPO_ROOT / "examples/sklearn_baseline/data"


def test_successful_ingestion_commits_after_quality_gate(tmp_path):
    client = InMemoryLakeFSClient()
    manifest_path = tmp_path / "manifest.json"

    result = run_baseline_ingestion(
        repository="housing-sale-ingestion-test",
        output_manifest_path=manifest_path,
        client=client,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.lakefs_commit_id == "commit-0001"
    assert result.no_op is False
    assert client.commits == [("housing-sale-ingestion-test", result.branch)]
    assert client.merges == [("housing-sale-ingestion-test", "commit-0001", "main")]
    assert manifest["artifacts"]["outputs"][0]["data_revision"]["id"] == "commit-0001"
    assert manifest["parameters"]["dataset_id"] == DATASET_ID
    assert manifest["metrics"]["curated_row_count"] == 240.0
    assert client.get_object("housing-sale-ingestion-test", result.branch, f"{CURATED_PREFIX}/_metadata.json")


def test_bad_input_does_not_commit_or_write_manifest(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    malformed_train = source_dir / "train.csv"
    malformed_train.write_text(
        "listing_id,listing_price_usd,square_feet\n"
        "listing-0001,250000,1000\n",
        encoding="utf-8",
    )
    test_csv = source_dir / "test.csv"
    shutil.copyfile(BASELINE_DATA / "test.csv", test_csv)
    client = InMemoryLakeFSClient()
    manifest_path = tmp_path / "manifest.json"

    with pytest.raises(ValueError):
        run_baseline_ingestion(
            input_paths={"train": malformed_train, "test": test_csv},
            repository="housing-sale-ingestion-test",
            output_manifest_path=manifest_path,
            client=client,
        )

    assert client.commits == []
    assert client.merges == []
    assert not manifest_path.exists()


def test_repeated_successful_ingestion_emits_linked_no_op_manifest(tmp_path):
    client = InMemoryLakeFSClient()
    first = run_baseline_ingestion(
        repository="housing-sale-ingestion-test",
        output_manifest_path=tmp_path / "first.json",
        client=client,
    )

    second = run_baseline_ingestion(
        repository="housing-sale-ingestion-test",
        output_manifest_path=tmp_path / "second.json",
        client=client,
    )

    manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    assert first.lakefs_commit_id == second.lakefs_commit_id
    assert second.no_op is True
    assert client.commits == [("housing-sale-ingestion-test", first.branch)]
    assert manifest["parameters"]["no_op"] is True
    assert manifest["metrics"]["curated_row_count"] == 240.0
    assert manifest["artifacts"]["outputs"][0]["data_revision"]["id"] == "commit-0001"


class InMemoryLakeFSClient:
    def __init__(self) -> None:
        self.repositories: set[str] = set()
        self.objects: dict[tuple[str, str, str], bytes] = {}
        self.heads: dict[tuple[str, str], str] = {}
        self.commits: list[tuple[str, str]] = []
        self.merges: list[tuple[str, str, str]] = []

    def setup(self) -> None:
        pass

    def ensure_repository(self, repository: str, *, storage_namespace: str) -> None:
        self.repositories.add(repository)
        self.heads.setdefault((repository, "main"), None)

    def branch_head(self, repository: str, branch: str) -> str | None:
        return self.heads.get((repository, branch))

    def create_branch(self, repository: str, branch: str, source: str) -> None:
        self.heads[(repository, branch)] = None if source == "main" else source

    def upload_file(self, repository: str, branch: str, path: str, local_path: Path) -> None:
        self.objects[(repository, branch, path)] = local_path.read_bytes()

    def get_object(self, repository: str, ref: str, path: str) -> bytes:
        if (repository, ref, path) in self.objects:
            return self.objects[(repository, ref, path)]
        if ref == "main":
            head = self.heads.get((repository, "main"))
            if head is not None and (repository, head, path) in self.objects:
                return self.objects[(repository, head, path)]
        raise LakeFSNotFoundError(path)

    def commit(self, repository: str, branch: str, *, message: str, metadata: dict[str, str]) -> str:
        commit_id = f"commit-{len(self.commits) + 1:04d}"
        self.commits.append((repository, branch))
        self.heads[(repository, branch)] = commit_id
        for (stored_repository, stored_branch, path), content in list(self.objects.items()):
            if stored_repository == repository and stored_branch == branch:
                self.objects[(repository, commit_id, path)] = content
        return commit_id

    def merge(self, repository: str, source_ref: str, destination_branch: str) -> None:
        self.merges.append((repository, source_ref, destination_branch))
        self.heads[(repository, destination_branch)] = source_ref
