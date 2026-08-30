"""Stdlib-only OpenLineage RunEvent construction for ingestion workflows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_URL = "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent"
PRODUCER = "https://github.com/kkadzielawa/ml_platform"
JOB_NAMESPACE = "ml-platform-study"
INGESTION_JOB_NAME = "baseline-versioned-ingestion"
FORBIDDEN_FAILURE_TERMS = ("password", "passwd", "secret", "token", "credential", "apikey", "api-key")


@dataclass
class InMemoryLineageCollector:
    """Tiny collector fixture for tests and local exploration."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    def event_types(self) -> list[str]:
        return [event["eventType"] for event in self.events]

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = "\n".join(json.dumps(event, sort_keys=True) for event in self.events)
        path.write_text(f"{payload}\n", encoding="utf-8")


def events_for_successful_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Build START and COMPLETE OpenLineage events from a universal run manifest."""

    return [build_start_event(manifest), build_complete_event(manifest)]


def build_start_event(manifest: dict[str, Any]) -> dict[str, Any]:
    return build_run_event(
        manifest,
        event_type="START",
        event_time=manifest["timestamps"]["started_at"],
        include_outputs=False,
    )


def build_complete_event(manifest: dict[str, Any]) -> dict[str, Any]:
    return build_run_event(
        manifest,
        event_type="COMPLETE",
        event_time=manifest["timestamps"]["finished_at"],
        include_outputs=True,
    )


def build_fail_event(
    *,
    run_id: str,
    started_at: str,
    input_uris: list[str],
    failed_at: str | None = None,
    message: str,
) -> dict[str, Any]:
    """Build a sanitized FAIL event without raw row values or secret-like strings."""

    event_time = failed_at or isoformat_z(datetime.now(tz=UTC))
    return {
        "eventTime": event_time,
        "producer": PRODUCER,
        "schemaURL": SCHEMA_URL,
        "eventType": "FAIL",
        "run": {
            "runId": run_id,
            "facets": {
                "mlPlatform_error": {
                    "_producer": PRODUCER,
                    "_schemaURL": "https://example.local/ml-platform-study/contracts/lineage/error-facet.json",
                    "message": sanitize_failure_message(message),
                    "failedAt": event_time,
                },
                "nominalTime": {
                    "_producer": PRODUCER,
                    "_schemaURL": "https://openlineage.io/spec/facets/1-0-1/NominalTimeRunFacet.json",
                    "nominalStartTime": started_at,
                    "nominalEndTime": event_time,
                },
            },
        },
        "job": job(),
        "inputs": [dataset_from_uri(uri) for uri in input_uris],
        "outputs": [],
    }


def build_ingestion_start_event(
    *,
    run_id: str,
    started_at: str,
    repository: str,
    source_uris: list[str],
    source_revision: str,
) -> dict[str, Any]:
    """Build a START event before a full run manifest exists."""

    return {
        "eventTime": started_at,
        "producer": PRODUCER,
        "schemaURL": SCHEMA_URL,
        "eventType": "START",
        "run": {
            "runId": run_id,
            "facets": {
                "mlPlatform_runManifest": {
                    "_producer": PRODUCER,
                    "_schemaURL": "https://example.local/ml-platform-study/contracts/run-manifest.schema.json",
                    "runId": run_id,
                    "correlationId": f"baseline-ingestion-{source_revision[-8:]}",
                    "lakefsRepository": repository,
                    "lakefsBranch": None,
                    "sourceRevision": source_revision,
                    "noOp": False,
                }
            },
        },
        "job": job(),
        "inputs": [dataset_from_uri(uri) for uri in source_uris],
        "outputs": [],
    }


def build_run_event(
    manifest: dict[str, Any],
    *,
    event_type: str,
    event_time: str,
    include_outputs: bool,
) -> dict[str, Any]:
    return {
        "eventTime": event_time,
        "producer": PRODUCER,
        "schemaURL": SCHEMA_URL,
        "eventType": event_type,
        "run": {
            "runId": manifest["run_id"],
            "facets": run_facets(manifest),
        },
        "job": job(),
        "inputs": [
            dataset_from_artifact(artifact)
            for artifact in manifest["artifacts"]["inputs"]
        ],
        "outputs": [
            dataset_from_artifact(artifact)
            for artifact in manifest["artifacts"]["outputs"]
        ]
        if include_outputs
        else [],
    }


def run_facets(manifest: dict[str, Any]) -> dict[str, Any]:
    parameters = manifest.get("parameters", {})
    return {
        "mlPlatform_runManifest": {
            "_producer": PRODUCER,
            "_schemaURL": "https://example.local/ml-platform-study/contracts/run-manifest.schema.json",
            "runId": manifest["run_id"],
            "correlationId": manifest["correlation"]["correlation_id"],
            "lakefsRepository": parameters.get("lakefs_repository"),
            "lakefsBranch": parameters.get("lakefs_branch"),
            "sourceRevision": parameters.get("source_revision"),
            "noOp": parameters.get("no_op", False),
        },
        "nominalTime": {
            "_producer": PRODUCER,
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-1/NominalTimeRunFacet.json",
            "nominalStartTime": manifest["timestamps"]["started_at"],
            "nominalEndTime": manifest["timestamps"]["finished_at"],
        },
    }


def job() -> dict[str, Any]:
    return {
        "namespace": JOB_NAMESPACE,
        "name": INGESTION_JOB_NAME,
        "facets": {
            "sourceCodeLocation": {
                "_producer": PRODUCER,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-1/SourceCodeLocationJobFacet.json",
                "type": "git",
                "url": PRODUCER,
            }
        },
    }


def dataset_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    dataset = dataset_from_uri(artifact["uri"])
    dataset["facets"].update(
        {
            "schema": {
                "_producer": PRODUCER,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
                "fields": [],
            },
            "dataSource": {
                "_producer": PRODUCER,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-1/DatasourceDatasetFacet.json",
                "name": dataset["namespace"],
                "uri": dataset["namespace"],
            },
            "mlPlatform_dataRevision": {
                "_producer": PRODUCER,
                "_schemaURL": "https://example.local/ml-platform-study/contracts/lineage/data-revision-facet.json",
                "type": artifact["data_revision"]["type"],
                "id": artifact["data_revision"]["id"],
                "checksum": artifact["checksum"],
                "schemaRef": artifact["schema_ref"],
            },
        }
    )
    return dataset


def dataset_from_uri(uri: str) -> dict[str, Any]:
    parsed = urlparse(uri)
    namespace = f"{parsed.scheme}://{parsed.netloc}"
    name = parsed.path.lstrip("/") or parsed.netloc
    return {
        "namespace": namespace,
        "name": name,
        "facets": {},
    }


def sanitize_failure_message(message: str) -> str:
    sanitized = message
    for term in FORBIDDEN_FAILURE_TERMS:
        sanitized = re.sub(rf"{term}[^,\s]*", "[redacted]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"listing-\d+", "[redacted-listing-id]", sanitized)
    sanitized = re.sub(r"\b\d{5,}\b", "[redacted-number]", sanitized)
    return sanitized[:512]


def isoformat_z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
