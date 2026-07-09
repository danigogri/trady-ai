from dataclasses import dataclass, field

import sqlite_utils
import structlog

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.models import MarketInput, Trade
from trady_ai.core.normalization import normalize
from trady_ai.core.observability import compute_summary
from trady_ai.core.persistence import (
    init_core_tables,
    persist_execution_log,
    persist_signal,
    persist_trade,
)
from trady_ai.core.position_manager import PositionManager
from trady_ai.core.risk import RiskEnforcer
from trady_ai.core.signal_strategy import SignalStrategy
from trady_ai.core.state import MarketStateTracker

logger = structlog.get_logger()


@dataclass
class ExecutionResult:
    """Result of a full engine run."""

    decisions: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    signals: list = field(default_factory=list)
    final_positions: list = field(default_factory=list)
    summary_stats: dict = field(default_factory=dict)


class ExecutionEngine:
    """Deterministic execution engine — orchestrates the full pipeline tick by tick.

    Pipeline per tick (9 steps):
      1. normalize(raw_input) → MarketInput
      2. state_tracker.update(normalized) → MarketState
      3. strategy.update(state)
      4. signal = strategy.evaluate(state)
      5. risk_enforcer.evaluate(signal, positions, config) → ExecutionDecision
      6. Execute: open/close position → Trade
      7. Persist signal, execution_log, trade → SQLite
      8. Log via structlog
      9. Loop

    Fail-fast: any exception propagates immediately — no try/except silence.
    """

    def __init__(self, config: RuntimeConfig, db: sqlite_utils.Database, dry_run: bool = True):
        self._config = config
        self._db = db
        self._dry_run = dry_run
        self._state_tracker = MarketStateTracker(config.threshold_pct)
        self._risk_enforcer = RiskEnforcer()
        self._position_manager = PositionManager()

    def run(self, inputs: list[MarketInput], strategy: SignalStrategy) -> ExecutionResult:
        """Run the full pipeline over a list of market inputs.

        Args:
            inputs: List of raw MarketInput ticks.
            strategy: SignalStrategy implementation (e.g. MarkovStrategy).

        Returns:
            ExecutionResult with decisions, trades, signals, positions, and summary.
        """
        init_core_tables(self._db)
        result = ExecutionResult()

        for tick_num, raw_input in enumerate(inputs, 1):
            # 1. Normalize
            normalized = normalize(raw_input)

            # 2. Classify market state
            state = self._state_tracker.update(normalized)

            # 3. Update strategy
            strategy.update(state)

            # 4. Generate signal
            signal = strategy.evaluate(state)
            result.signals.append(signal)

            # 5. Evaluate risk
            positions = self._position_manager.get_open_positions()
            decision = self._risk_enforcer.evaluate(signal, positions, self._config)
            result.decisions.append(decision)

            # 6. Execute decision
            trade = None
            if decision.action in ("OPEN_LONG", "OPEN_SHORT"):
                p = self._position_manager.open_position(
                    signal, state.price, self._config.position_size, self._config
                )
                trade = Trade(
                    signal_id=signal.id,
                    position_id=p.id,
                    action="OPEN",
                    price=state.price,
                    size=p.size,
                    timestamp=state.timestamp,
                    dry_run=self._dry_run,
                )
            elif decision.action == "CLOSE":
                for p in self._position_manager.get_open_positions():
                    closed = self._position_manager.close_position(p, state.price, self._config)
                    trade = Trade(
                        signal_id=signal.id,
                        position_id=p.id,
                        action="CLOSE",
                        price=state.price,
                        size=closed.size,
                        timestamp=state.timestamp,
                        dry_run=self._dry_run,
                    )

            if trade:
                result.trades.append(trade)

            # 7. Persist
            persist_signal(self._db, signal)
            persist_execution_log(self._db, tick_num, normalized, state, signal, decision, trade)
            if trade:
                persist_trade(self._db, trade)

            # 8. Log
            logger.info(
                "tick",
                tick=tick_num,
                market=state.market_id,
                signal=signal.direction,
                decision=decision.action,
            )

        # Finalize
        result.final_positions = self._position_manager.get_all_positions()
        result.summary_stats = compute_summary(
            result.decisions, result.trades, result.final_positions
        )
        return result
