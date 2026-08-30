from __future__ import annotations

import json
from pathlib import Path

from ml_platform.lineage import (
    InMemoryLineageCollector,
    build_fail_event,
    events_for_successful_manifest,
)
from ml_platform.ingestion import run_baseline_ingestion
from ml_platform.run_manifest.validation import validate_manifest
from tests.integration.ingestion.test_baseline_ingestion import InMemoryLakeFSClient


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_success_events_match_run_manifest_dataset_uris_and_run_id():
    manifest = load_manifest_fixture()
    events = events_for_successful_manifest(manifest)

    assert [event["eventType"] for event in events] == ["START", "COMPLETE"]
    assert {event["run"]["runId"] for event in events} == {manifest["run_id"]}
    assert [dataset["namespace"] + "/" + dataset["name"] for dataset in events[0]["inputs"]] == [
        artifact["uri"]
        for artifact in manifest["artifacts"]["inputs"]
    ]
    assert events[0]["outputs"] == []
    assert [dataset["namespace"] + "/" + dataset["name"] for dataset in events[1]["outputs"]] == [
        artifact["uri"]
        for artifact in manifest["artifacts"]["outputs"]
    ]


def test_events_validate_against_local_openlineage_contract():
    schema = json.loads((REPO_ROOT / "contracts/lineage/openlineage-run-event.schema.json").read_text(encoding="utf-8"))
    manifest = load_manifest_fixture()

    for event in events_for_successful_manifest(manifest):
        validate_manifest(event, schema)


def test_collector_captures_start_complete_and_fail_events(tmp_path):
    manifest = load_manifest_fixture()
    collector = InMemoryLineageCollector()

    for event in events_for_successful_manifest(manifest):
        collector.emit(event)
    collector.emit(
        build_fail_event(
            run_id=manifest["run_id"],
            started_at=manifest["timestamps"]["started_at"],
            failed_at=manifest["timestamps"]["finished_at"],
            input_uris=[artifact["uri"] for artifact in manifest["artifacts"]["inputs"]],
            message="secret token abc listing-0001 price 425000 leaked from malformed fixture",
        )
    )
    output_path = tmp_path / "events.jsonl"
    collector.write_jsonl(output_path)

    assert collector.event_types() == ["START", "COMPLETE", "FAIL"]
    content = output_path.read_text(encoding="utf-8")
    assert "listing-0001" not in content
    assert "425000" not in content
    assert "secret" not in content.lower()
    assert "token" not in content.lower()


def test_ingestion_emits_start_and_complete_events_that_match_manifest(tmp_path):
    collector = InMemoryLineageCollector()
    result = run_baseline_ingestion(
        repository="housing-sale-lineage-test",
        output_manifest_path=tmp_path / "manifest.json",
        client=InMemoryLakeFSClient(),
        lineage_collector=collector,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert collector.event_types() == ["START", "COMPLETE"]
    assert {event["run"]["runId"] for event in collector.events} == {manifest["run_id"]}
    assert [dataset["namespace"] + "/" + dataset["name"] for dataset in collector.events[0]["inputs"]] == [
        artifact["uri"]
        for artifact in manifest["artifacts"]["inputs"]
    ]
    assert [dataset["namespace"] + "/" + dataset["name"] for dataset in collector.events[1]["outputs"]] == [
        artifact["uri"]
        for artifact in manifest["artifacts"]["outputs"]
    ]


def test_ingestion_emits_sanitized_fail_event_without_committing(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    train = source_dir / "train.csv"
    train.write_text(
        "listing_id,listing_price_usd,square_feet\n"
        "listing-0001,425000,1000\n",
        encoding="utf-8",
    )
    test = source_dir / "test.csv"
    test.write_text(
        "listing_id,listing_price_usd,square_feet\n"
        "listing-0002,525000,1200\n",
        encoding="utf-8",
    )
    collector = InMemoryLineageCollector()
    client = InMemoryLakeFSClient()

    try:
        run_baseline_ingestion(
            input_paths={"train": train, "test": test},
            repository="housing-sale-lineage-test",
            output_manifest_path=tmp_path / "manifest.json",
            client=client,
            lineage_collector=collector,
        )
    except ValueError:
        pass

    assert collector.event_types() == ["START", "FAIL"]
    assert client.commits == []
    serialized = json.dumps(collector.events)
    assert "listing-0001" not in serialized
    assert "425000" not in serialized
    assert "secret" not in serialized.lower()


def load_manifest_fixture() -> dict:
    return json.loads((REPO_ROOT / "contracts/examples/run-manifests/classic-ml-valid.json").read_text(encoding="utf-8"))
