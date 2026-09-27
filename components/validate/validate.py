"""Run the selected data-quality suite against an immutable dataset reference."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ml_platform.data_quality import validate_parquet_dataset


QUALITY_GATE_FAILURE_EXIT_CODE = 42


class ValidationError(ValueError):
    """Raised when a validation component input is not a valid declaration."""


class QualityGateFailure(RuntimeError):
    """Raised after a report is published for a failed quality gate."""

    exit_code = QUALITY_GATE_FAILURE_EXIT_CODE


@dataclass(frozen=True)
class ImmutableDatasetReference:
    """A local dataset materialization paired with an immutable lakeFS commit."""

    repository: str
    commit_id: str
    dataset_path: Path
    dataset_path_in_store: str = ""

    def validate(self) -> None:
        if not self.repository or any(character.isspace() for character in self.repository):
            raise ValidationError("repository must be a non-empty name without whitespace")
        if not self.commit_id or any(character.isspace() for character in self.commit_id):
            raise ValidationError("commit_id must be a non-empty immutable identifier")
        if any(character.isspace() for character in self.dataset_path_in_store):
            raise ValidationError("dataset_path_in_store must not contain whitespace")
        dataset_path = Path(self.dataset_path)
        if not dataset_path.is_dir():
            raise ValidationError(f"dataset path does not exist: {dataset_path}")


@dataclass(frozen=True)
class ValidationComponentResult:
    """Machine-readable validation outcome and its published report."""

    success: bool
    report: dict
    report_path: Path


def load_snapshot_reference(snapshot_path: Path, dataset_path: Path) -> ImmutableDatasetReference:
    """Load the commit identity emitted by the snapshot component."""

    try:
        payload = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"invalid snapshot metadata artifact: {snapshot_path}") from error
    if not isinstance(payload, dict):
        raise ValidationError("snapshot metadata artifact must contain an object")
    return ImmutableDatasetReference(
        repository=payload.get("repository", ""),
        commit_id=payload.get("commit_id", ""),
        dataset_path=Path(dataset_path),
        dataset_path_in_store=payload.get("dataset_path", ""),
    )


def run_validation_component(
    reference: ImmutableDatasetReference,
    *,
    suite_path: Path,
    report_path: Path,
) -> ValidationComponentResult:
    """Validate an immutable dataset and publish an aggregate report.

    The report is written for both passing and failing quality gates.  A failed
    gate raises ``QualityGateFailure`` only after that evidence is durable.
    """

    reference.validate()
    suite_path = Path(suite_path)
    if not suite_path.is_file():
        raise ValidationError(f"validation suite does not exist: {suite_path}")

    quality_result = validate_parquet_dataset(reference.dataset_path, suite_path=suite_path)
    source_result = quality_result.result
    report = {
        "schema_version": "1.0.0",
        "component": "dataset-validation",
        "status": "passed" if quality_result.success else "failed",
        "quality_gate": "passed" if quality_result.success else "failed",
        "reference": {
            "repository": reference.repository,
            "commit_id": reference.commit_id,
            "dataset_path": reference.dataset_path_in_store,
        },
        "validator": source_result["validator"],
        "suite_name": source_result["suite_name"],
        "dataset_id": source_result["dataset_id"],
        "statistics": source_result["statistics"],
        "results": source_result["results"],
    }
    published_path = write_validation_report(report, report_path)
    result = ValidationComponentResult(
        success=quality_result.success,
        report=report,
        report_path=published_path,
    )
    if not quality_result.success:
        raise QualityGateFailure(
            f"quality gate failed; report published at {published_path}"
        )
    return result


def write_validation_report(report: dict, report_path: Path) -> Path:
    """Atomically publish a JSON report without including row-level data."""

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=report_path.parent,
            prefix=f".{report_path.name}.",
            suffix=".partial",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            json.dump(report, temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        Path(temporary_path).replace(report_path)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
    return report_path


def main(argv: list[str] | None = None) -> int:
    """Run validation from a snapshot metadata artifact."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        run_validation_component(
            load_snapshot_reference(arguments.snapshot, arguments.dataset),
            suite_path=arguments.suite,
            report_path=arguments.report,
        )
    except QualityGateFailure as error:
        print(str(error))
        return error.exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
