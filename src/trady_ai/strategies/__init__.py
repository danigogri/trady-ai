"""Strategy Infrastructure — Fase 3.

Provides ``StrategyBase`` (ABC refining ``SignalStrategy``) and
``StrategyRegistry`` (factory-backed registry with singleton-per-key
semantics).
"""

from trady_ai.strategies.base import StrategyBase
from trady_ai.strategies.registry import StrategyRegistry

__all__ = [
    "StrategyBase",
    "StrategyRegistry",
]
