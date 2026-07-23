"""Calibration Framework — evidence pipeline for state-space adoption.

Provides:
    - CalibrationAnalyzer: stateless, read-only analyzer for Markov state spaces
    - Metrics: AIC, BIC, Markov χ², state persistence, conditional entropy
    - EvidenceReport: deterministic evidence report dataclass
    - Persistence helpers for adoption records
"""

from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer
from trady_ai.reflection.calibration.metrics import (
    aic,
    bic,
    conditional_entropy,
    markov_chi2,
    state_persistence,
)
from trady_ai.reflection.calibration.models import EvidenceReport

__all__ = [
    "CalibrationAnalyzer",
    "EvidenceReport",
    "aic",
    "bic",
    "conditional_entropy",
    "markov_chi2",
    "state_persistence",
]
