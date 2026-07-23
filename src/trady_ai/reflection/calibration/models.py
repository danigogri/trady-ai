"""Data models for the Calibration Framework.

Provides:
    - EvidenceReport: deterministic report of calibration metrics
    - AdoptedStateSpace: configuration model for state-space adoption
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class EvidenceReport:
    """Deterministic evidence report for a Markov state space.

    All fields are computed from transition counts and state sequences.
    Same inputs always produce identical values.

    Attributes:
        aic: Akaike Information Criterion value.
        bic: Bayesian Information Criterion value.
        markov_test: Billingsley χ² test results (statistic, p_value, df,
            reject_null, significance_level).
        state_persistence: Per-state mean residence times, keyed by state
            index (0..|S|-1).
        conditional_entropy: Conditional entropy H(X_{n+1}|X_n) in bits.
        num_states: Size of the state space (|S|).
        num_observations: Total number of state transitions observed.
        transition_counts: Raw transition count matrix (list of lists).
        computed_at: ISO-8601 timestamp of computation.
    """

    aic: float = 0.0
    bic: float = 0.0
    markov_test: dict[str, object] = field(default_factory=lambda: {
        "statistic": 0.0,
        "p_value": 1.0,
        "df": 0,
        "reject_null": False,
        "significance_level": 0.05,
    })
    state_persistence: dict[int, float] = field(default_factory=dict)
    conditional_entropy: float = 0.0
    num_states: int = 0
    num_observations: int = 0
    transition_counts: list[list[int]] = field(default_factory=list)
    computed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class AdoptedStateSpace:
    """Configuration model for an adopted state space.

    Attributes:
        domain: Market domain (e.g. ``"PM-5M"``).
        strategy_name: Strategy name (e.g. ``"markov_persistence"``).
        states: Number of states (|S|).
        generator: Generator name (e.g. ``"directional"``).
        evidence_report_ref: SHA-256 of the evidence report JSON.
        operator: Human operator who approved the adoption.
        adopted_at: ISO-8601 timestamp of adoption.
        reason: Human-supplied justification for the change.
    """

    domain: str
    strategy_name: str
    states: int
    generator: str
    evidence_report_ref: str = ""
    operator: str = ""
    adopted_at: str = ""
    reason: str = ""
