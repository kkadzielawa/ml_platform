"""Small JSONL OpenLineage writer used by the local component runner."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .artifacts import Artifact


PRODUCER = "https://github.com/kkadzielawa/ml_platform"
SCHEMA_URL = "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent"
_SECRET_TERM = re.compile(r"password|passwd|secret|token|credential|api.?key", re.IGNORECASE)


class LineageWriter:
    """Append OpenLineage-shaped events to a local JSON Lines file."""

    def __init__(self, path: Path, *, run_id: str, component_name: str) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.component_name = component_name

    def emit(
        self,
        event_type: str,
        *,
        inputs: Iterable[Artifact],
        outputs: Iterable[Artifact],
        message: str | None = None,
    ) -> dict[str, Any]:
        if event_type not in {"START", "COMPLETE", "FAIL"}:
            raise ValueError(f"unsupported lineage event type: {event_type}")
        event: dict[str, Any] = {
            "eventTime": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "producer": PRODUCER,
            "schemaURL": SCHEMA_URL,
            "eventType": event_type,
            "run": {"runId": self.run_id, "facets": {}},
            "job": {"namespace": "ml-platform-study", "name": self.component_name, "facets": {}},
            "inputs": [_dataset(artifact) for artifact in inputs],
            "outputs": [_dataset(artifact) for artifact in outputs],
        }
        if message:
            event["run"]["facets"]["mlPlatform_error"] = {
                "message": _sanitize_message(message),
            }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(event, sort_keys=True) + "\n")
        return event


def _dataset(artifact: Artifact) -> dict[str, Any]:
    parsed = urlparse(artifact.uri)
    return {
        "namespace": f"{parsed.scheme}://{parsed.netloc or 'local'}",
        "name": parsed.path.lstrip("/") or artifact.name,
        "facets": {"mlPlatform_artifact": {"uri": artifact.uri}},
    }


def _sanitize_message(message: str) -> str:
    sanitized = message[:512]
    sanitized = _SECRET_TERM.sub("[redacted]", sanitized)
    return re.sub(r"\b\d{5,}\b", "[redacted-number]", sanitized)
