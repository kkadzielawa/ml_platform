from __future__ import annotations

import io
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest

from ml_platform.ingestion.lakefs_client import LakeFSClient, lakefs_port_forward


REPO_ROOT = Path(__file__).resolve().parents[3]
ADR_PATH = REPO_ROOT / "adr/0004-parquet-lakefs-table-route.md"
TABLE_ROUTE_PATH = REPO_ROOT / "docs/data/table-route.md"
POINTER_PATH = "published/housing-sale-features.json"


def test_parquet_lakefs_route_documents_commit_pinning_and_table_limits():
    adr = ADR_PATH.read_text(encoding="utf-8")
    route = TABLE_ROUTE_PATH.read_text(encoding="utf-8")

    assert "Accepted" in adr
    assert "lakeFS commit ID" in adr
    assert "transactional table semantics" in adr
    assert "row-level" in adr
    assert "repository name" in route
    assert "lakeFS commit ID" in route
    assert "must not be used" in route
    assert "single publisher" in route


@pytest.mark.skipif(
    os.environ.get("RUN_TABLE_ROUTE_INTEGRATION") != "1",
    reason="table-route integration requires a running kind cluster and lakeFS deployment",
)
def test_parquet_release_is_reconstructed_from_an_older_lakefs_commit(tmp_path: Path):
    polars = pytest.importorskip("polars")
    repository = f"study-parquet-route-{uuid.uuid4().hex[:12]}"
    client = LakeFSClient.from_environment()

    with lakefs_port_forward():
        wait_for_lakefs(client)
        client.setup()
        client.ensure_repository(
            repository,
            storage_namespace=f"s3://ml-platform-artifacts/lakefs/{repository}/",
        )

        try:
            first_path = write_parquet_release(
                polars,
                tmp_path,
                version="v0001",
                rows=[{"listing_id": "home-001", "sale_price_usd": 310000}],
            )
            first_object_path = "curated/housing-sale-features/v0001/part-00000.parquet"
            client.upload_file(repository, "main", first_object_path, first_path)
            client.upload_bytes(
                repository,
                "main",
                POINTER_PATH,
                release_pointer("v0001", first_object_path),
            )
            first_commit = client.commit(
                repository,
                "main",
                message="publish housing-sale-features v0001",
                metadata={"issue": "03.11.a", "dataset_version": "v0001", "table_route": "parquet-lakefs"},
            )

            second_path = write_parquet_release(
                polars,
                tmp_path,
                version="v0002",
                rows=[{"listing_id": "home-001", "sale_price_usd": 325000}],
            )
            second_object_path = "curated/housing-sale-features/v0002/part-00000.parquet"
            client.upload_file(repository, "main", second_object_path, second_path)
            client.upload_bytes(
                repository,
                "main",
                POINTER_PATH,
                release_pointer("v0002", second_object_path),
            )
            second_commit = client.commit(
                repository,
                "main",
                message="publish housing-sale-features v0002",
                metadata={"issue": "03.11.a", "dataset_version": "v0002", "table_route": "parquet-lakefs"},
            )

            first_manifest = json.loads(client.get_object(repository, first_commit, POINTER_PATH))
            latest_manifest = json.loads(client.get_object(repository, "main", POINTER_PATH))
            first_frame = polars.read_parquet(
                io.BytesIO(client.get_object(repository, first_commit, first_manifest["parquet_path"]))
            )
            latest_frame = polars.read_parquet(
                io.BytesIO(client.get_object(repository, "main", latest_manifest["parquet_path"]))
            )

            assert first_commit != second_commit
            assert first_manifest == {"dataset_version": "v0001", "parquet_path": first_object_path}
            assert latest_manifest == {"dataset_version": "v0002", "parquet_path": second_object_path}
            assert first_frame.to_dicts() == [{"listing_id": "home-001", "sale_price_usd": 310000}]
            assert latest_frame.to_dicts() == [{"listing_id": "home-001", "sale_price_usd": 325000}]
        finally:
            delete_repository_if_exists(client, repository)


def write_parquet_release(polars, tmp_path: Path, *, version: str, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / f"housing-sale-features-{version}.parquet"
    polars.DataFrame(rows).write_parquet(path)
    return path


def release_pointer(version: str, parquet_path: str) -> bytes:
    return json.dumps(
        {"dataset_version": version, "parquet_path": parquet_path}, sort_keys=True
    ).encode("utf-8")


def wait_for_lakefs(client: LakeFSClient) -> None:
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{client.endpoint}/_health", timeout=2):
                return
        except urllib.error.URLError:
            time.sleep(1)
    raise AssertionError("lakeFS health endpoint did not become available")


def delete_repository_if_exists(client: LakeFSClient, repository: str) -> None:
    try:
        client.request("DELETE", f"/repositories/{repository}")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
