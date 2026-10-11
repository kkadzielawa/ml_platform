from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from ml_platform.local_runner import (
    ComponentInvocation,
    LocalPipelineError,
    LocalPipelineRunner,
    python_module_invocation,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHONPATH = str(REPO_ROOT / "src")


def test_runner_executes_ordered_component_contracts_and_captures_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    first_output = tmp_path / "outputs" / "first.txt"
    second_output = tmp_path / "outputs" / "second.txt"
    source.write_text("portable component fixture\n", encoding="utf-8")
    run_root = tmp_path / "run"
    run_id = "run-20261011t120000z-00000001"

    first = python_module_invocation(
        "snapshot-fixture",
        "ml_platform.components.noop",
        (
            "--input-uri",
            source.as_uri(),
            "--output-uri",
            first_output.as_uri(),
            "--manifest",
            str(tmp_path / "evidence" / "first-manifest.json"),
            "--lineage",
            str(tmp_path / "evidence" / "first-lineage.jsonl"),
            "--run-id",
            run_id,
        ),
        output_paths={"artifact": first_output},
        environment={"PYTHONPATH": PYTHONPATH},
    )
    second = python_module_invocation(
        "validate-fixture",
        "ml_platform.components.noop",
        (
            "--input-uri",
            first_output.as_uri(),
            "--output-uri",
            second_output.as_uri(),
            "--manifest",
            str(tmp_path / "evidence" / "second-manifest.json"),
            "--lineage",
            str(tmp_path / "evidence" / "second-lineage.jsonl"),
            "--run-id",
            run_id,
        ),
        output_paths={"artifact": second_output},
        environment={"PYTHONPATH": PYTHONPATH},
    )

    result = LocalPipelineRunner(run_root, run_id=run_id).run([first, second])

    assert result.succeeded
    assert [component.name for component in result.components] == [
        "snapshot-fixture",
        "validate-fixture",
    ]
    assert second_output.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    capture = result.components[1].artifacts[0]
    assert capture.capture_path.is_file()
    assert capture.bytes == source.stat().st_size
    assert capture.sha256 == f"sha256:{hashlib.sha256(source.read_bytes()).hexdigest()}"

    summary = json.loads((run_root / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed"
    assert summary["components"][0]["status"] == "completed"


def test_runner_propagates_failure_and_stops_downstream(tmp_path: Path) -> None:
    marker = tmp_path / "downstream-ran.txt"
    failing = (
        sys.executable,
        "-c",
        "import sys; print('component failed'); raise SystemExit(17)",
    )
    downstream = (
        sys.executable,
        "-c",
        f"from pathlib import Path; Path({str(marker)!r}).write_text('unexpected')",
    )

    with pytest.raises(LocalPipelineError) as raised:
        LocalPipelineRunner(tmp_path / "run").run(
            [
                _invocation("failing-stage", failing),
                _invocation("downstream-stage", downstream),
            ]
        )

    result = raised.value.result
    assert result.failed_component == "failing-stage"
    assert result.skipped_components == ("downstream-stage",)
    assert [component.name for component in result.components] == ["failing-stage"]
    assert result.components[0].returncode == 17
    assert "component failed" in result.components[0].stdout
    assert not marker.exists()
    assert result.summary_path is not None and result.summary_path.is_file()


def test_runner_rejects_success_without_declared_artifact(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    invocation = _invocation(
        "missing-output",
        (sys.executable, "-c", "pass"),
        output_paths={"required": missing},
    )

    with pytest.raises(LocalPipelineError, match="did not publish declared artifact"):
        LocalPipelineRunner(tmp_path / "run").run([invocation])


def _invocation(
    name: str,
    command: tuple[str, ...],
    *,
    output_paths: dict[str, Path] | None = None,
):
    return ComponentInvocation(name=name, command=command, output_paths=output_paths or {})
