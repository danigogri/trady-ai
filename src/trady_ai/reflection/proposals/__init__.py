"""Bounded proposal generation for the Reflection Systems module.

ProposalGenerator creates parameter adjustment proposals constrained
to ADR-5 bounded ranges.
"""
from trady_ai.reflection.proposals.generator import ProposalGenerator

__all__ = [
    "ProposalGenerator",
]
