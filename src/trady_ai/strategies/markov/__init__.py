"""Markov Persistence Engine — N×N transition matrix strategy and variants.

Provides:
    - MarkovPersistenceEngine: state-prediction via Markov chain argmax
    - DirectionalPersistence: alias for semantic clarity (same state space)
    - VolatilityPersistence: volatility-regime classification (HIGH/LOW/STABLE)
    - StateGenerator: pluggable state classification ABC
    - DirectionalStateGenerator: threshold-based UP/DOWN/NEUTRAL classifier
    - VolatilityStateGenerator: volatility-regime classifier (HIGH/LOW/STABLE)
    - get_generator: factory function for named generators
"""

from trady_ai.strategies.markov.persistence import (
    DirectionalPersistence,
    MarkovPersistenceEngine,
    VolatilityPersistence,
)
from trady_ai.strategies.markov.state_generator import (
    DirectionalStateGenerator,
    StateGenerator,
    VolatilityStateGenerator,
    get_generator,
)

__all__ = [
    "DirectionalPersistence",
    "DirectionalStateGenerator",
    "MarkovPersistenceEngine",
    "StateGenerator",
    "VolatilityPersistence",
    "VolatilityStateGenerator",
    "get_generator",
]
