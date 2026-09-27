"""Strict, small helpers for reading component parameters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ParameterError(ValueError):
    """Raised when a component parameter is missing or has the wrong type."""


class TypedParameters:
    """Read a mapping with explicit types and useful error messages.

    Booleans are deliberately not accepted as integers.  Python considers
    ``bool`` a subclass of ``int``, but accepting ``True`` for a retry count
    makes component contracts surprisingly easy to misuse.
    """

    def __init__(self, values: Mapping[str, Any] | None = None) -> None:
        self._values = dict(values or {})

    def as_dict(self) -> dict[str, Any]:
        return dict(self._values)

    def _require(self, name: str) -> Any:
        if not isinstance(name, str) or not name:
            raise ParameterError("parameter name must be a non-empty string")
        if name not in self._values:
            raise ParameterError(f"missing required parameter: {name}")
        return self._values[name]

    def require_str(self, name: str) -> str:
        value = self._require(name)
        if not isinstance(value, str):
            raise ParameterError(f"parameter {name!r} must be a string")
        return value

    def require_int(self, name: str) -> int:
        value = self._require(name)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ParameterError(f"parameter {name!r} must be an integer")
        return value

    def require_float(self, name: str) -> float:
        value = self._require(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ParameterError(f"parameter {name!r} must be a number")
        return float(value)

    def require_bool(self, name: str) -> bool:
        value = self._require(name)
        if not isinstance(value, bool):
            raise ParameterError(f"parameter {name!r} must be a boolean")
        return value
