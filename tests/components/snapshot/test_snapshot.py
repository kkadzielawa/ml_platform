from __future__ import annotations

import json
from pathlib import Path

import pytest

from components.snapshot import SnapshotError, SnapshotRequest, run_snapshot_component


class FakeLakeFS:
    def __init__(self, commit_id: str | None = None, error: Exception | None = None) -> None:
        self.commit_id = commit_id
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def branch_head(self, repository: str, branch: str) -> str | None:
        self.calls.append((repository, branch))
        if self.error:
            raise self.error
        return self.commit_id


def test_valid_reference_emits_exact_commit_id_without_copying_data(tmp_path: Path) -> None:
    output = tmp_path / "artifacts" / "snapshot.json"
    client = FakeLakeFS(commit_id="c0ffee1234567890")

    result = run_snapshot_component(
        client,
        SnapshotRequest(
            repository="housing-sale-ingestion",
            reference="main",
            dataset_path="curated/housing-sale/v0001",
        ),
        output,
    )

    assert client.calls == [("housing-sale-ingestion", "main")]
    assert result.metadata.commit_id == "c0ffee1234567890"
    assert json.loads(output.read_text(encoding="utf-8"))["commit_id"] == "c0ffee1234567890"
    assert list(tmp_path.rglob("*.parquet")) == []


def test_missing_reference_fails_before_output_publication(tmp_path: Path) -> None:
    output = tmp_path / "artifacts" / "snapshot.json"

    with pytest.raises(SnapshotError, match="reference not found"):
        run_snapshot_component(
            FakeLakeFS(commit_id=None),
            SnapshotRequest(repository="housing-sale-ingestion", reference="missing"),
            output,
        )

    assert not output.exists()
    assert not output.parent.exists()


def test_client_failure_fails_before_output_publication(tmp_path: Path) -> None:
    output = tmp_path / "artifacts" / "snapshot.json"

    with pytest.raises(SnapshotError, match="could not resolve"):
        run_snapshot_component(
            FakeLakeFS(error=ConnectionError("lakeFS unavailable")),
            SnapshotRequest(repository="housing-sale-ingestion", reference="main"),
            output,
        )

    assert not output.exists()
