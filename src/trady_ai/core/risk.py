from decimal import Decimal
from typing import Any, Literal, cast

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.models import ExecutionDecision, Position, Signal


class RiskEnforcer:
    """Evaluates signals against risk rules and produces ExecutionDecision.

    Pipeline of 5 sequential checks (C0–C5), fail-fast on invalid config.
    Deterministic: same signal + same positions + same config → same decision.
    """

    def __init__(self, max_open_positions: int = 1, max_position_size: Decimal = Decimal("1000.00")):
        self.max_open_positions = max_open_positions
        self.max_position_size = max_position_size

    def evaluate(
        self,
        signal: Signal,
        positions: list[Position],
        config: RuntimeConfig,
    ) -> ExecutionDecision:
        """Evaluate a signal against risk rules and return an ExecutionDecision.

        Args:
            signal: The signal to evaluate.
            positions: All positions (open and closed).
            config: Runtime configuration for thresholds and sizing.

        Returns:
            ExecutionDecision with action: OPEN_LONG, OPEN_SHORT, CLOSE, HOLD, or REJECT.

        Raises:
            ValueError: If config.position_size is not positive.
        """
        # C0: Neutral signal → HOLD immediately
        if signal.direction == "NEUTRAL":
            return ExecutionDecision(
                signal_id=signal.id,
                action="HOLD",
                reason="Neutral signal",
                risk_check_passed=True,
                risk_check_details={},
                timestamp=signal.timestamp,
            )

        # Fail-fast: position_size must be positive
        if config.position_size <= Decimal("0"):
            raise ValueError("position_size must be positive")

        open_positions = [p for p in positions if p.status == "OPEN"]
        details: dict[str, Any] = {
            "max_open_positions": self.max_open_positions,
            "current_open": len(open_positions),
        }

        # C1: Max open positions
        if len(open_positions) >= self.max_open_positions:
            return ExecutionDecision(
                signal_id=signal.id,
                action="REJECT",
                reason="Max open positions reached",
                risk_check_passed=False,
                risk_check_details=details,
                timestamp=signal.timestamp,
            )

        # C2: Position size limit
        if config.position_size > self.max_position_size:
            return ExecutionDecision(
                signal_id=signal.id,
                action="REJECT",
                reason="Position size exceeds maximum",
                risk_check_passed=False,
                risk_check_details=details,
                timestamp=signal.timestamp,
            )

        # C3: Stop loss — check each open position
        stop_threshold = Decimal(str(1 - config.stop_loss_pct))
        for p in open_positions:
            if p.direction == "LONG" and p.current_price < p.entry_price * stop_threshold:
                details["stop_loss_triggered"] = str(p.id)
                return ExecutionDecision(
                    signal_id=signal.id,
                    action="CLOSE",
                    reason=f"Stop loss triggered for position {p.id}",
                    risk_check_passed=True,
                    risk_check_details=details,
                    timestamp=signal.timestamp,
                )

        # C4: Duplicate market — already open for this market
        if any(p.market_id == signal.market_id for p in open_positions):
            return ExecutionDecision(
                signal_id=signal.id,
                action="REJECT",
                reason="Position already open for this market",
                risk_check_passed=False,
                risk_check_details=details,
                timestamp=signal.timestamp,
            )

        # C5: Direction → action
        action = "OPEN_LONG" if signal.direction == "LONG" else "OPEN_SHORT"
        return ExecutionDecision(
            signal_id=signal.id,
            action=cast(Literal["OPEN_LONG", "OPEN_SHORT", "CLOSE", "HOLD", "REJECT"], action),
            reason=f"Signal {signal.direction} approved",
            risk_check_passed=True,
            risk_check_details=details,
            timestamp=signal.timestamp,
        )
