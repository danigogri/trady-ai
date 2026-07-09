import shutil
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.engine import ExecutionEngine
from trady_ai.core.markov_strategy import MarkovStrategy
from trady_ai.core.models import MarketInput
from trady_ai.core.persistence import init_core_tables
from trady_ai.core.replay import replay, verify_replay


def _generate_market_inputs(count: int, start_price: Decimal = Decimal("100.00")) -> list[MarketInput]:
    """Generate deterministic market inputs with price movement."""
    base_ts = datetime(2024, 1, 1, 12, 0, 0)
    inputs = []
    price = start_price

    for i in range(count):
        cycle = (i // 10) % 4
        if cycle == 0:
            price = start_price * Decimal("1.02")
        elif cycle == 1:
            price = start_price * Decimal("1.00")
        elif cycle == 2:
            price = start_price * Decimal("0.98")
        else:
            price = start_price * Decimal("1.01")

        ts = base_ts + timedelta(seconds=i * 60)
        inputs.append(
            MarketInput(
                timestamp=ts,
                market_id="btc-usd",
                price=price,
                volume=Decimal("100.00"),
                source="csv",
            )
        )
        start_price = price

    return inputs


class TestReplay:
    def test_replay(self, tmp_path):
        """engine.run → persist → replay → verify_replay == True."""
        import sqlite_utils

        # Run engine on DB1
        db1_path = tmp_path / "original.db"
        db1 = sqlite_utils.Database(db1_path)
        init_core_tables(db1)

        config = RuntimeConfig()
        inputs = _generate_market_inputs(100)
        strategy = MarkovStrategy(warmup_ticks=50)
        engine = ExecutionEngine(config, db1, dry_run=True)
        original = engine.run(inputs, strategy)

        # Fresh DB copy for replay
        db2_path = tmp_path / "replay.db"
        shutil.copy(db1_path, db2_path)
        db2 = sqlite_utils.Database(db2_path)

        strategy2 = MarkovStrategy(warmup_ticks=50)
        replayed = replay(db2, strategy2, config)

        assert verify_replay(original, replayed) is True

    def test_replay_determinism(self, tmp_path):
        """Replay executed twice on identical DB copies → same results."""
        import sqlite_utils

        # Run engine
        db1_path = tmp_path / "original.db"
        db1 = sqlite_utils.Database(db1_path)
        init_core_tables(db1)

        config = RuntimeConfig()
        inputs = _generate_market_inputs(100)
        strategy = MarkovStrategy(warmup_ticks=50)
        engine = ExecutionEngine(config, db1, dry_run=True)
        engine.run(inputs, strategy)
        db1.close()

        # Two copies for determinism check
        db2_path = tmp_path / "replay1.db"
        shutil.copy(db1_path, db2_path)
        db3_path = tmp_path / "replay2.db"
        shutil.copy(db1_path, db3_path)

        db2 = sqlite_utils.Database(db2_path)
        db3 = sqlite_utils.Database(db3_path)

        result1 = replay(db2, MarkovStrategy(warmup_ticks=50), config)
        result2 = replay(db3, MarkovStrategy(warmup_ticks=50), config)

        assert verify_replay(result1, result2) is True

    def test_verify_replay_mismatch(self):
        """Different ExecutionResults → AssertionError."""
        from uuid import NAMESPACE_URL, uuid5

        from trady_ai.core.models import ExecutionDecision, Signal, Trade

        ts = datetime(2024, 1, 1, 12, 0, 0)
        sid = uuid5(NAMESPACE_URL, "test:signal")

        from trady_ai.core.engine import ExecutionResult

        # Different decision counts
        result_a = ExecutionResult(
            decisions=[
                ExecutionDecision(
                    signal_id=sid,
                    action="HOLD",
                    reason="Neutral signal",
                    risk_check_passed=True,
                    timestamp=ts,
                )
            ],
        )
        result_b = ExecutionResult(decisions=[])

        with pytest.raises(AssertionError, match="Decision count mismatch"):
            verify_replay(result_a, result_b)

        # Different signal directions
        sig_a = Signal(
            id=sid,
            timestamp=ts,
            market_id="btc-usd",
            direction="LONG",
            confidence=0.85,
            strategy_name="test",
        )
        sig_b = Signal(
            id=sid,
            timestamp=ts,
            market_id="btc-usd",
            direction="NEUTRAL",
            confidence=0.0,
            strategy_name="test",
        )

        result_c = ExecutionResult(signals=[sig_a])
        result_d = ExecutionResult(signals=[sig_b])

        with pytest.raises(AssertionError, match="direction mismatch"):
            verify_replay(result_c, result_d)

        # Different trade actions
        pos_id = uuid5(NAMESPACE_URL, "position:test")
        trade_a = Trade(
            signal_id=sid,
            position_id=pos_id,
            action="OPEN",
            price=Decimal("100.00"),
            size=Decimal("10.00"),
            timestamp=ts,
        )
        trade_b = Trade(
            signal_id=sid,
            position_id=pos_id,
            action="CLOSE",
            price=Decimal("100.00"),
            size=Decimal("10.00"),
            timestamp=ts,
        )

        result_e = ExecutionResult(trades=[trade_a])
        result_f = ExecutionResult(trades=[trade_b])

        with pytest.raises(AssertionError, match="action mismatch"):
            verify_replay(result_e, result_f)
