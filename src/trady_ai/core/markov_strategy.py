"""Backward-compat re-export stub.

The MarkovStrategy class has been migrated to
``trady_ai.strategies.markov.persistence.MarkovPersistenceEngine``.
This stub re-exports it so existing imports from ``trady_ai.core.markov_strategy``
continue to work without modification.
"""
from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine as MarkovStrategy

__all__ = ["MarkovStrategy"]
