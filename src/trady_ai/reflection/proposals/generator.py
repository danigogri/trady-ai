"""ProposalGenerator — bounded parameter adjustment proposals.

Stateless generator that translates drift events into parameter proposals
constrained by ADR-5 bounded ranges. Proposal values are always clamped
to [range_min, range_max].
"""
from __future__ import annotations

from datetime import UTC, datetime

from trady_ai.reflection.models import DriftEvent, Proposal

# ADR-5: Bounded parameter ranges for MarkovPersistenceEngine.
# ProposalGenerator MUST NOT propose values outside these ranges.
BOUNDED_PARAMETERS: dict[str, dict[str, float]] = {
    "warmup_ticks": {"min": 10, "max": 200},
    "threshold_pct": {"min": 0.0001, "max": 0.01},
}


class ProposalGenerator:
    """Generates bounded parameter adjustment proposals from drift signals.

    For each DriftEvent whose metric matches a BOUNDED_PARAMETERS key:
      1. Retrieve the current parameter value from ``current_params``.
      2. Compute the range midpoint.
      3. If current_value is outside [min, max]: propose the range midpoint.
      4. Otherwise: propose midpoint between current_value and range midpoint.
      5. Clamp proposed_value to [min, max].
      6. Create a Proposal with status="draft".
    """

    def generate(
        self,
        strategy_id: str,
        current_params: dict[str, float],
        drift_events: list[DriftEvent],
    ) -> list[Proposal]:
        """Generate proposals from drift events and current parameter values.

        Args:
            strategy_id: Strategy identifier.
            current_params: Current parameter values keyed by parameter name.
            drift_events: Detected drift events from DriftAnalyzer.

        Returns:
            List of Proposal objects (empty if no drift events match bounded
            parameters).
        """
        proposals: list[Proposal] = []
        generated_params: set[str] = set()

        for event in drift_events:
            param_name = event.metric
            if param_name not in BOUNDED_PARAMETERS:
                continue

            bounds = BOUNDED_PARAMETERS[param_name]
            range_min = bounds["min"]
            range_max = bounds["max"]
            range_midpoint = (range_min + range_max) / 2.0

            current_value = current_params.get(param_name)
            if current_value is None:
                continue

            # Range enforcement: out-of-range current → propose midpoint
            if current_value < range_min or current_value > range_max:
                proposed_value = range_midpoint
                justification = (
                    f"Current value {current_value} outside range [{range_min}, {range_max}]. "
                    f"Proposed safe midpoint {range_midpoint}."
                )
            else:
                # Drift-adjusted: midpoint between current and range midpoint
                proposed_value = (current_value + range_midpoint) / 2.0
                justification = (
                    f"Adjusted from {current_value} toward range midpoint "
                    f"{range_midpoint} based on drift event {event.metric}."
                )
                # Clamp if proposed would be outside range (defensive)
                original = proposed_value
                if proposed_value < range_min:
                    proposed_value = range_min
                    justification += (
                        f" Value clamped from {original} to {range_min} "
                        "(range boundary)."
                    )
                elif proposed_value > range_max:
                    proposed_value = range_max
                    justification += (
                        f" Value clamped from {original} to {range_max} "
                        "(range boundary)."
                    )

            proposals.append(
                Proposal(
                    strategy_id=strategy_id,
                    parameter_name=param_name,
                    current_value=current_value,
                    proposed_value=proposed_value,
                    range_min=range_min,
                    range_max=range_max,
                    justification=justification,
                    status="draft",
                    created_at=datetime.now(UTC),
                )
            )
            generated_params.add(param_name)

        return proposals
