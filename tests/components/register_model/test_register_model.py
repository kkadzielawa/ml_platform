from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from components.register_model import (
    RegistrationError,
    RegistrationRequest,
    run_registration_component,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_ID = "run-20260927t150000z-00000001"
MLFLOW_RUN_ID = "0123456789abcdef0123456789abcdef"
MODEL_NAME = "housing-sale-candidate"
MODEL_VERSION = "0.1.0"


@dataclass
class FakeRegistry:
    registered: set[str]
    versions: list[SimpleNamespace]
    aliases: list[tuple[str, str, str]]
    create_model_version_calls: int = 0

    def __init__(self) -> None:
        self.registered = set()
        self.versions = []
        self.aliases = []
        self.create_model_version_calls = 0

    def get_registered_model(self, name: str):
        if name not in self.registered:
            raise KeyError(name)
        return SimpleNamespace(name=name)

    def create_registered_model(self, name: str):
        self.registered.add(name)
        return SimpleNamespace(name=name)

    def search_model_versions(self, filter_string: str):
        assert filter_string == f"name = '{MODEL_NAME}'"
        return list(self.versions)

    def create_model_version(self, name: str, source: str, run_id: str, tags: dict[str, str]):
        self.create_model_version_calls += 1
        version = SimpleNamespace(
            name=name,
            version=str(len(self.versions) + 1),
            source=source,
            run_id=run_id,
            tags=tags,
        )
        self.versions.append(version)
        return version

    def set_registered_model_alias(self, name: str, alias: str, version: str):
        self.aliases.append((name, alias, version))


def request(tmp_path: Path, *, expected_checksum: str | None = None) -> RegistrationRequest:
    artifacts = write_evidence(tmp_path)
    return RegistrationRequest(
        run_id=RUN_ID,
        mlflow_run_id=MLFLOW_RUN_ID,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        model_source=f"runs:/{MLFLOW_RUN_ID}/model",
        evaluation_path=artifacts["evaluation"],
        expected_evaluation_sha256=expected_checksum or sha256_file(artifacts["evaluation"]),
        run_manifest_path=artifacts["manifest"],
        signature_path=artifacts["signature"],
        license_record_path=artifacts["license"],
    )


def write_evidence(tmp_path: Path, *, decision: str = "pass") -> dict[str, Path]:
    evaluation = tmp_path / "evaluation.json"
    evaluation.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "component": "offline-evaluation",
                "evaluation_id": f"{RUN_ID}-evaluation",
                "run_id": RUN_ID,
                "status": "passed" if decision == "pass" else "failed",
                "decision": decision,
                "failures": [] if decision == "pass" else ["candidate_accuracy"],
                "dataset": {
                    "name": "synthetic-housing-sale-classifier",
                    "version": "v0001",
                    "revision": "lakefs-commit-c0ffee1234567890",
                },
                "model": {
                    "candidate": {
                        "name": MODEL_NAME,
                        "version": MODEL_VERSION,
                        "artifact_sha256": "sha256:" + "1" * 64,
                    },
                    "baseline": {
                        "type": "majority-class",
                        "version": "metadata.expected_baseline",
                        "artifact_sha256": None,
                    },
                },
                "code": {"version": "git:0123456789abcdef0123456789abcdef01234567"},
                "thresholds": {"version": "evaluation-thresholds/v1"},
                "metrics": {
                    "candidate_accuracy": 1.0,
                    "baseline_accuracy": 0.56,
                    "improvement": 0.44,
                },
                "slices": [
                    {
                        "column": "property_type",
                        "value": "single-family",
                        "rows": 10,
                        "candidate_accuracy": 1.0,
                        "baseline_accuracy": 0.5,
                        "improvement": 0.5,
                        "passed": True,
                    }
                ],
                "latency": {"passed": True, "p95_ms": 1.0},
                "checks": [{"name": "candidate_accuracy", "passed": True}],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = json.loads(
        (REPO_ROOT / "contracts/examples/run-manifests/classic-ml-valid.json").read_text(encoding="utf-8")
    )
    manifest["run_id"] = RUN_ID
    manifest["model"]["name"] = MODEL_NAME
    manifest["model"]["version"] = MODEL_VERSION
    manifest["model"]["license"] = "BSD-3-Clause"
    manifest_path = tmp_path / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

    signature_path = tmp_path / "signature.json"
    signature_path.write_text(
        json.dumps({"inputs": [{"name": "listing_price_usd", "type": "double"}], "outputs": [{"type": "long"}]}),
        encoding="utf-8",
    )

    license_path = tmp_path / "license.json"
    license_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "record_type": "model-weights",
                "name": MODEL_NAME,
                "version": MODEL_VERSION,
                "source_url": "https://github.com/kkadzielawa/ml_platform",
                "license": {
                    "kind": "spdx",
                    "expression": "BSD-3-Clause",
                    "classification": "osi-open-source",
                },
                "review": {
                    "status": "accepted",
                    "decision_by": "study",
                    "decision_date": "2026-09-27",
                    "notes": "Synthetic study model.",
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {
        "evaluation": evaluation,
        "manifest": manifest_path,
        "signature": signature_path,
        "license": license_path,
    }


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def test_passing_evidence_registers_one_version_and_aliases_it(tmp_path: Path) -> None:
    registry = FakeRegistry()
    evaluation_request = request(tmp_path)

    result = run_registration_component(evaluation_request, client=registry)

    assert result.created is True
    assert result.version == "1"
    assert result.alias == "candidate"
    assert registry.create_model_version_calls == 1
    assert registry.aliases == [(MODEL_NAME, "candidate", "1")]
    assert result.tags["ml-platform.evaluation.decision"] == "pass"
    assert result.tags["ml-platform.dataset.revision"] == "lakefs-commit-c0ffee1234567890"
    assert result.tags["ml-platform.provenance.signature_ref"].startswith("file://")
    assert result.tags["ml-platform.provenance.license_ref"].startswith("file://")
    assert result.tags["ml-platform.provenance.run_manifest_ref"].startswith("file://")


def test_repeating_the_same_request_does_not_create_a_duplicate_version(tmp_path: Path) -> None:
    registry = FakeRegistry()
    evaluation_request = request(tmp_path)

    first = run_registration_component(evaluation_request, client=registry)
    second = run_registration_component(evaluation_request, client=registry)

    assert first.version == second.version == "1"
    assert first.created is True
    assert second.created is False
    assert registry.create_model_version_calls == 1
    assert registry.aliases == [
        (MODEL_NAME, "candidate", "1"),
        (MODEL_NAME, "candidate", "1"),
    ]


def test_failing_evaluation_registers_nothing(tmp_path: Path) -> None:
    artifacts = write_evidence(tmp_path, decision="fail")
    evaluation_request = RegistrationRequest(
        run_id=RUN_ID,
        mlflow_run_id=MLFLOW_RUN_ID,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        model_source=f"runs:/{MLFLOW_RUN_ID}/model",
        evaluation_path=artifacts["evaluation"],
        expected_evaluation_sha256=sha256_file(artifacts["evaluation"]),
        run_manifest_path=artifacts["manifest"],
        signature_path=artifacts["signature"],
        license_record_path=artifacts["license"],
    )
    registry = FakeRegistry()

    with pytest.raises(RegistrationError, match="passing evaluation") as raised:
        run_registration_component(evaluation_request, client=registry)

    assert raised.value.args
    assert registry.create_model_version_calls == 0
    assert registry.aliases == []
    assert registry.registered == set()


def test_tampered_evaluation_registers_nothing(tmp_path: Path) -> None:
    evaluation_request = request(tmp_path)
    evaluation_request.evaluation_path.write_text(
        evaluation_request.evaluation_path.read_text(encoding="utf-8").replace('"decision": "pass"', '"decision": "fail"'),
        encoding="utf-8",
    )
    registry = FakeRegistry()

    with pytest.raises(RegistrationError, match="checksum"):
        run_registration_component(evaluation_request, client=registry)

    assert registry.create_model_version_calls == 0
    assert registry.aliases == []


def test_missing_evidence_fails_before_registry_access(tmp_path: Path) -> None:
    artifacts = write_evidence(tmp_path)
    missing = RegistrationRequest(
        run_id=RUN_ID,
        mlflow_run_id=MLFLOW_RUN_ID,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        model_source=f"runs:/{MLFLOW_RUN_ID}/model",
        evaluation_path=tmp_path / "missing-evaluation.json",
        expected_evaluation_sha256=sha256_file(artifacts["evaluation"]),
        run_manifest_path=artifacts["manifest"],
        signature_path=artifacts["signature"],
        license_record_path=artifacts["license"],
    )
    registry = FakeRegistry()

    with pytest.raises(RegistrationError, match="evaluation_path does not exist"):
        run_registration_component(missing, client=registry)

    assert registry.create_model_version_calls == 0
