"""Register an MLflow model only after validating passing evaluation evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


_RUN_ID = re.compile(r"^run-\d{8}t\d{6}z-[0-9a-f]{8}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_MLFLOW_RUN_ID = re.compile(r"^[0-9a-f]{32}$")
_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}$")
_ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

REGISTRATION_FAILURE_EXIT_CODE = 43


class RegistrationError(ValueError):
    """Raised before registration when evidence or configuration is invalid."""


class ModelRegistryClient(Protocol):
    """Small MLflow client surface used by the component."""

    def get_registered_model(self, name: str) -> Any: ...

    def create_registered_model(self, name: str) -> Any: ...

    def search_model_versions(self, filter_string: str) -> Sequence[Any]: ...

    def create_model_version(self, name: str, source: str, run_id: str, tags: Mapping[str, str]) -> Any: ...

    def set_registered_model_alias(self, name: str, alias: str, version: str) -> Any: ...


@dataclass(frozen=True)
class RegistrationRequest:
    """Immutable registration inputs and expected upstream identities."""

    run_id: str
    mlflow_run_id: str
    model_name: str
    model_version: str
    model_source: str
    evaluation_path: Path
    expected_evaluation_sha256: str
    run_manifest_path: Path
    signature_path: Path
    license_record_path: Path
    alias: str = "candidate"
    tracking_uri: str = ""

    def validate(self) -> None:
        if not _RUN_ID.fullmatch(self.run_id):
            raise RegistrationError("run_id must match run-YYYYMMDDtHHMMSSz-<8 lowercase hex>")
        if not _MLFLOW_RUN_ID.fullmatch(self.mlflow_run_id):
            raise RegistrationError("mlflow_run_id must be a 32-character lowercase hex identifier")
        if not _MODEL_NAME.fullmatch(self.model_name):
            raise RegistrationError("model_name contains unsupported characters")
        if not self.model_version or any(character.isspace() for character in self.model_version):
            raise RegistrationError("model_version must be a non-empty identifier without whitespace")
        if not self.model_source or any(character.isspace() for character in self.model_source):
            raise RegistrationError("model_source must be a non-empty URI without whitespace")
        if not _SHA256.fullmatch(self.expected_evaluation_sha256):
            raise RegistrationError("expected_evaluation_sha256 must use sha256:<64 lowercase hex>")
        if not _ALIAS.fullmatch(self.alias):
            raise RegistrationError("alias contains unsupported characters")
        if self.tracking_uri and any(character.isspace() for character in self.tracking_uri):
            raise RegistrationError("tracking_uri must not contain whitespace")
        for name, path in {
            "evaluation_path": self.evaluation_path,
            "run_manifest_path": self.run_manifest_path,
            "signature_path": self.signature_path,
            "license_record_path": self.license_record_path,
        }.items():
            if not Path(path).is_file():
                raise RegistrationError(f"{name} does not exist: {path}")


@dataclass(frozen=True)
class RegistrationResult:
    """Registered version and the evidence tags attached to it."""

    model_name: str
    version: str
    alias: str
    created: bool
    tags: dict[str, str]


def run_registration_component(
    request: RegistrationRequest,
    *,
    client: ModelRegistryClient | None = None,
    client_factory: Callable[[str], ModelRegistryClient] | None = None,
) -> RegistrationResult:
    """Validate evidence, then create/reuse exactly one MLflow model version.

    All local evidence is read and checked before the first registry mutation.
    Re-running the same request finds the existing version by MLflow run and
    source instead of creating a duplicate.
    """

    request.validate()
    evidence = _load_and_validate_evidence(request)
    registry = client or (client_factory or _default_client)(request.tracking_uri)
    _ensure_registered_model(registry, request.model_name)
    existing = _matching_versions(registry, request)
    if len(existing) > 1:
        raise RegistrationError("multiple registered versions already match this run and source")

    tags = _registration_tags(request, evidence)
    if existing:
        version = _version_string(existing[0])
        created = False
    else:
        model_version = registry.create_model_version(
            name=request.model_name,
            source=request.model_source,
            run_id=request.mlflow_run_id,
            tags=tags,
        )
        version = _version_string(model_version)
        created = True
    registry.set_registered_model_alias(request.model_name, request.alias, version)
    return RegistrationResult(
        model_name=request.model_name,
        version=version,
        alias=request.alias,
        created=created,
        tags=tags,
    )


def _load_and_validate_evidence(request: RegistrationRequest) -> dict[str, Any]:
    actual_evaluation_checksum = _sha256_file(Path(request.evaluation_path))
    if actual_evaluation_checksum != request.expected_evaluation_sha256:
        raise RegistrationError("evaluation report checksum does not match expected_evaluation_sha256")
    evaluation = _load_json(Path(request.evaluation_path), "evaluation report")
    _validate_evaluation_report(evaluation, request)
    candidate = _nested_object(evaluation, "model", "candidate")
    if candidate.get("name") != request.model_name or candidate.get("version") != request.model_version:
        raise RegistrationError("evaluation candidate identity does not match registration request")
    if not _SHA256.fullmatch(str(candidate.get("artifact_sha256", ""))):
        raise RegistrationError("evaluation candidate artifact checksum is missing or malformed")
    dataset = _nested_object(evaluation, "dataset")
    code = _nested_object(evaluation, "code")
    thresholds = _nested_object(evaluation, "thresholds")

    manifest = _load_json(Path(request.run_manifest_path), "run manifest")
    if manifest.get("run_id") != request.run_id:
        raise RegistrationError("run manifest run_id does not match registration request")
    manifest_model = _nested_object(manifest, "model")
    if manifest_model.get("name") != request.model_name or str(manifest_model.get("version")) != request.model_version:
        raise RegistrationError("run manifest model identity does not match registration request")
    if not manifest_model.get("license"):
        raise RegistrationError("run manifest must identify the model license")
    if not isinstance(manifest.get("artifacts"), dict):
        raise RegistrationError("run manifest must include artifact provenance")

    signature = _load_json(Path(request.signature_path), "model signature")
    if not isinstance(signature, dict) or not signature:
        raise RegistrationError("model signature must be a non-empty JSON object")

    license_record = _load_json(Path(request.license_record_path), "license record")
    _validate_license_record(license_record, request, str(manifest_model["license"]))
    return {
        "evaluation": evaluation,
        "dataset": dataset,
        "code": code,
        "thresholds": thresholds,
        "manifest": manifest,
        "signature": signature,
        "license": license_record,
        "evaluation_sha256": actual_evaluation_checksum,
        "manifest_sha256": _sha256_file(Path(request.run_manifest_path)),
        "signature_sha256": _sha256_file(Path(request.signature_path)),
        "license_sha256": _sha256_file(Path(request.license_record_path)),
    }


def _validate_evaluation_report(evaluation: Mapping[str, Any], request: RegistrationRequest) -> None:
    required_fields = {
        "schema_version",
        "component",
        "evaluation_id",
        "run_id",
        "status",
        "decision",
        "dataset",
        "model",
        "code",
        "thresholds",
        "metrics",
        "slices",
        "latency",
        "checks",
        "failures",
    }
    missing = sorted(required_fields - set(evaluation))
    if missing:
        raise RegistrationError(f"evaluation report is missing required fields: {', '.join(missing)}")
    if evaluation["schema_version"] != "1.0.0":
        raise RegistrationError("evaluation report must use schema version 1.0.0")
    if evaluation["component"] != "offline-evaluation":
        raise RegistrationError("evaluation report was not produced by offline-evaluation")
    if evaluation["decision"] != "pass" or evaluation["status"] != "passed":
        raise RegistrationError("model registration requires a passing evaluation decision")
    if evaluation["failures"] != []:
        raise RegistrationError("model registration requires an evaluation with no failures")
    if evaluation["run_id"] != request.run_id:
        raise RegistrationError("evaluation run_id does not match registration request")
    if not isinstance(evaluation["checks"], list) or not evaluation["checks"]:
        raise RegistrationError("evaluation report must include gate checks")
    if any(not isinstance(check, dict) or check.get("passed") is not True for check in evaluation["checks"]):
        raise RegistrationError("all evaluation gate checks must pass before registration")
    if not isinstance(evaluation["slices"], list) or not evaluation["slices"]:
        raise RegistrationError("evaluation report must include slice evidence")
    latency = _nested_object(evaluation, "latency")
    if latency.get("passed") is not True:
        raise RegistrationError("evaluation latency gate must pass before registration")
    for section, keys in {
        "dataset": ("name", "version", "revision"),
        "code": ("version",),
        "thresholds": ("version",),
        "metrics": ("candidate_accuracy", "baseline_accuracy", "improvement"),
    }.items():
        payload = _nested_object(evaluation, section)
        missing_section_fields = [key for key in keys if key not in payload]
        if missing_section_fields:
            raise RegistrationError(
                f"evaluation {section} is missing required fields: {', '.join(missing_section_fields)}"
            )
    _nested_object(evaluation, "model", "baseline")


def _validate_license_record(record: Mapping[str, Any], request: RegistrationRequest, manifest_license: str) -> None:
    if record.get("schema_version") != "1.0.0":
        raise RegistrationError("license record must use schema version 1.0.0")
    if record.get("record_type") not in {"model-weights", "generated-adapter"}:
        raise RegistrationError("license record must describe model weights or an adapter")
    if record.get("name") != request.model_name or str(record.get("version")) != request.model_version:
        raise RegistrationError("license record model identity does not match registration request")
    license_details = record.get("license")
    review = record.get("review")
    if not isinstance(license_details, dict) or not license_details.get("expression"):
        raise RegistrationError("license record must include an SPDX/custom expression")
    if str(license_details["expression"]) != manifest_license:
        raise RegistrationError("license expression does not match the run manifest")
    if not isinstance(review, dict) or review.get("status") != "accepted":
        raise RegistrationError("model license must have an accepted review status")


def _registration_tags(request: RegistrationRequest, evidence: Mapping[str, Any]) -> dict[str, str]:
    evaluation = evidence["evaluation"]
    dataset = evidence["dataset"]
    code = evidence["code"]
    thresholds = evidence["thresholds"]
    return {
        "ml-platform.run_id": request.run_id,
        "ml-platform.mlflow_run_id": request.mlflow_run_id,
        "ml-platform.evaluation.decision": str(evaluation["decision"]),
        "ml-platform.evaluation.schema_version": str(evaluation["schema_version"]),
        "ml-platform.evaluation.sha256": str(evidence["evaluation_sha256"]),
        "ml-platform.evaluation.threshold_version": str(thresholds.get("version", "unknown")),
        "ml-platform.dataset.name": str(dataset.get("name", "unknown")),
        "ml-platform.dataset.version": str(dataset.get("version", "unknown")),
        "ml-platform.dataset.revision": str(dataset.get("revision", "unknown")),
        "ml-platform.code.version": str(code.get("version", "unknown")),
        "ml-platform.provenance.run_manifest_sha256": str(evidence["manifest_sha256"]),
        "ml-platform.provenance.run_manifest_ref": Path(request.run_manifest_path).resolve().as_uri(),
        "ml-platform.provenance.signature_sha256": str(evidence["signature_sha256"]),
        "ml-platform.provenance.signature_ref": Path(request.signature_path).resolve().as_uri(),
        "ml-platform.provenance.license_sha256": str(evidence["license_sha256"]),
        "ml-platform.provenance.license_ref": Path(request.license_record_path).resolve().as_uri(),
    }


def _ensure_registered_model(client: ModelRegistryClient, model_name: str) -> None:
    try:
        client.get_registered_model(model_name)
    except Exception as error:
        if not _looks_like_not_found(error):
            raise RegistrationError(f"could not inspect registered model {model_name!r}: {error}") from error
        try:
            client.create_registered_model(model_name)
        except Exception as create_error:
            if not _looks_like_already_exists(create_error):
                raise RegistrationError(f"could not create registered model {model_name!r}: {create_error}") from create_error


def _matching_versions(client: ModelRegistryClient, request: RegistrationRequest) -> list[Any]:
    try:
        versions = client.search_model_versions(f"name = '{request.model_name}'")
    except Exception as error:
        raise RegistrationError(f"could not inspect model versions: {error}") from error
    return [
        version
        for version in versions
        if str(getattr(version, "run_id", "")) == request.mlflow_run_id
        and str(getattr(version, "source", "")) == request.model_source
    ]


def _version_string(model_version: Any) -> str:
    version = getattr(model_version, "version", None)
    if version is None or not str(version):
        raise RegistrationError("MLflow did not return a model version")
    return str(version)


def _default_client(tracking_uri: str) -> ModelRegistryClient:
    try:
        from mlflow.tracking import MlflowClient
    except ImportError as error:
        raise RegistrationError("mlflow is required for model registration") from error
    return MlflowClient(tracking_uri=tracking_uri or None)


def _load_json(path: Path, description: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RegistrationError(f"{description} is not valid JSON: {path}") from error
    if not isinstance(payload, dict):
        raise RegistrationError(f"{description} must contain a JSON object: {path}")
    return payload


def _nested_object(payload: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or not isinstance(current.get(key), dict):
            raise RegistrationError(f"evidence is missing object: {'.'.join(keys)}")
        current = current[key]
    return current


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _looks_like_not_found(error: Exception) -> bool:
    return isinstance(error, KeyError) or "not found" in str(error).lower() or "does not exist" in str(error).lower()


def _looks_like_already_exists(error: Exception) -> bool:
    return "already exists" in str(error).lower() or "already registered" in str(error).lower()


def main(argv: list[str] | None = None) -> int:
    """Register a model from prevalidated local evidence."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--mlflow-run-id", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--model-source", required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--evaluation-sha256", required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--license-record", type=Path, required=True)
    parser.add_argument("--alias", default="candidate")
    parser.add_argument("--tracking-uri", default=os.environ.get("MLFLOW_TRACKING_URI", ""))
    arguments = parser.parse_args(argv)
    try:
        run_registration_component(
            RegistrationRequest(
                run_id=arguments.run_id,
                mlflow_run_id=arguments.mlflow_run_id,
                model_name=arguments.model_name,
                model_version=arguments.model_version,
                model_source=arguments.model_source,
                evaluation_path=arguments.evaluation,
                expected_evaluation_sha256=arguments.evaluation_sha256,
                run_manifest_path=arguments.run_manifest,
                signature_path=arguments.signature,
                license_record_path=arguments.license_record,
                alias=arguments.alias,
                tracking_uri=arguments.tracking_uri,
            )
        )
    except RegistrationError as error:
        print(str(error))
        return REGISTRATION_FAILURE_EXIT_CODE
    return 0
