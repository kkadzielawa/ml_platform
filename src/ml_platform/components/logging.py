"""JSON Lines logging with the correlation fields required by components."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from typing import Any, TextIO


_SECRET_KEY = re.compile(r"password|passwd|secret|token|credential|api.?key", re.IGNORECASE)


class ComponentLogger:
    """Emit one structured JSON object per log line.

    The logger accepts explicit fields rather than arbitrary formatted text so
    component code can keep correlation metadata consistent.  Secret-like
    fields are redacted defensively before serialization.
    """

    def __init__(
        self,
        *,
        run_id: str,
        component_name: str,
        attempt: int,
        stream: TextIO | None = None,
    ) -> None:
        self._base = {
            "run_id": run_id,
            "component_name": component_name,
            "attempt": attempt,
        }
        self._stream = stream or sys.stdout

    def log(self, level: str, message: str, **fields: Any) -> None:
        if level not in {"debug", "info", "warning", "error"}:
            raise ValueError(f"unsupported log level: {level}")
        record = {
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": level,
            "message": message[:512],
            **self._base,
            **_redact_fields(fields),
        }
        self._stream.write(json.dumps(record, sort_keys=True) + "\n")
        self._stream.flush()

    def debug(self, message: str, **fields: Any) -> None:
        self.log("debug", message, **fields)

    def info(self, message: str, **fields: Any) -> None:
        self.log("info", message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self.log("warning", message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self.log("error", message, **fields)


def _redact_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: "[redacted]" if _SECRET_KEY.search(key) else value for key, value in fields.items()}
