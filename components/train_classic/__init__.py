"""Portable classic-ML training component."""

from .train_classic import (
    TrainingError,
    TrainingRequest,
    TrainingResult,
    fit_baseline_model,
    run_training_component,
)

__all__ = [
    "TrainingError",
    "TrainingRequest",
    "TrainingResult",
    "fit_baseline_model",
    "run_training_component",
]
