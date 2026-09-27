from __future__ import annotations

from pathlib import Path

import pytest

from components.train_classic import TrainingError, TrainingRequest, run_training_component


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DATA = REPO_ROOT / "examples/sklearn_baseline/data"
INPUTS = {
    "train_path": BASELINE_DATA / "train.csv",
    "test_path": BASELINE_DATA / "test.csv",
    "metadata_path": BASELINE_DATA / "metadata.json",
}
RUN_ID = "run-20260927t130000z-00000001"


def request(tmp_path: Path) -> TrainingRequest:
    return TrainingRequest(
        run_id=RUN_ID,
        output_dir=tmp_path / "training-output",
        dataset_revision="lakefs-commit-c0ffee1234567890",
        tracking_uri="file:///tmp/ml-platform-training-test",
        experiment_name="local-classic-ml-test",
        run_name="housing-sale-baseline-test",
        model_name="housing-sale-baseline-test",
        **INPUTS,
    )


def test_invalid_input_fails_before_creating_output(tmp_path: Path) -> None:
    invalid = request(tmp_path)
    invalid = TrainingRequest(
        **{**invalid.__dict__, "train_path": tmp_path / "missing.csv"}
    )

    with pytest.raises(TrainingError, match="train_path does not exist"):
        run_training_component(invalid)

    assert not invalid.output_dir.exists()


def test_training_failure_leaves_no_partial_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import components.train_classic.train_classic as module

    def fail(_request):
        raise RuntimeError("forced training failure")

    monkeypatch.setattr(module, "fit_baseline_model", fail)

    with pytest.raises(RuntimeError, match="forced training failure"):
        run_training_component(request(tmp_path))

    assert not (tmp_path / "training-output").exists()


def test_fixed_fixture_reproduces_recorded_metric(tmp_path: Path) -> None:
    pytest.importorskip("sklearn", reason="sklearn is required for the fixed-fixture training check")
    from components.train_classic.train_classic import fit_baseline_model

    fit = fit_baseline_model(request(tmp_path))
    assert fit.accuracy == pytest.approx(0.7)
