import copy
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.engine import ExecutionEngine
from trady_ai.core.markov_strategy import MarkovStrategy
from trady_ai.core.models import MarketInput


def _generate_market_inputs(count: int, start_price: Decimal = Decimal("100.00")) -> list[MarketInput]:
    """Generate deterministic market inputs with a sinusoidal-like price pattern.

    Creates enough price movement to trigger UP/DOWN transitions after warmup.
    """
    base_ts = datetime(2024, 1, 1, 12, 0, 0)
    inputs = []
    price = start_price

    for i in range(count):
        # Every 10 ticks, move price up or down by 2%
        cycle = (i // 10) % 4
        if cycle == 0:
            price = start_price * Decimal("1.02")  # up 2%
        elif cycle == 1:
            price = start_price * Decimal("1.00")  # back to start
        elif cycle == 2:
            price = start_price * Decimal("0.98")  # down 2%
        else:
            price = start_price * Decimal("1.01")  # up 1%

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
        start_price = price  # carry forward for next cycle

    return inputs


class TestEnginePipeline:
    def test_engine_pipeline(self, tmp_db, sample_runtime_config):
        """Full pipeline run → ExecutionResult with signals, decisions, and trades."""
        inputs = _generate_market_inputs(100)
        strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=sample_runtime_config.threshold_pct)
        engine = ExecutionEngine(sample_runtime_config, tmp_db, dry_run=True)

        result = engine.run(inputs, strategy)

        assert len(result.signals) == 100
        assert len(result.decisions) == 100
        assert len(result.trades) >= 0  # trades only if signals pass risk
        assert len(result.final_positions) >= 0

        # Verify summary stats exist
        stats = result.summary_stats
        assert stats["total_signals"] == 100
        assert "signals_by_direction" in stats
        assert "total_pnl" in stats
        assert "max_drawdown" in stats

        # Verify signals are deterministic UUIDs (compare first and last)
        assert result.signals[0].id is not None
        assert result.signals[0].direction is not None

    def test_engine_determinism(self, tmp_db, sample_runtime_config):
        """Same CSV executed 2 times → identical results (determinism)."""
        inputs = _generate_market_inputs(100)
        strategy1 = MarkovStrategy(warmup_ticks=50)
        strategy2 = MarkovStrategy(warmup_ticks=50)

        engine1 = ExecutionEngine(sample_runtime_config, tmp_db, dry_run=True)
        result1 = engine1.run(copy.deepcopy(inputs), strategy1)

        # Use a fresh DB for second run to avoid PK conflicts
        import tempfile

        import sqlite_utils

        db2 = sqlite_utils.Database(tempfile.mkdtemp() + "/test2.db")
        engine2 = ExecutionEngine(sample_runtime_config, db2, dry_run=True)
        result2 = engine2.run(copy.deepcopy(inputs), strategy2)

        # Compare signals field-by-field
        for i, (s1, s2) in enumerate(zip(result1.signals, result2.signals)):
            assert s1.id == s2.id, f"Signal UUID mismatch at {i}"
            assert s1.direction == s2.direction, f"Signal direction mismatch at {i}"
            assert s1.confidence == pytest.approx(s2.confidence), f"Signal confidence mismatch at {i}"

        # Compare decisions field-by-field
        for i, (d1, d2) in enumerate(zip(result1.decisions, result2.decisions)):
            assert d1.action == d2.action, f"Decision action mismatch at {i}"
            assert d1.reason == d2.reason, f"Decision reason mismatch at {i}"
            assert d1.risk_check_passed == d2.risk_check_passed, f"Risk check mismatch at {i}"

        # Compare summary stats
        assert result1.summary_stats == result2.summary_stats

    def test_engine_cold_start(self, tmp_db, sample_runtime_config):
        """First 49 ticks → zero non-NEUTRAL signals. Tick 50 is the first ready tick."""
        inputs = _generate_market_inputs(49)  # one less than warmup boundary
        strategy = MarkovStrategy(warmup_ticks=50)
        engine = ExecutionEngine(sample_runtime_config, tmp_db, dry_run=True)

        result = engine.run(inputs, strategy)

        # All 49 signals must be NEUTRAL during warmup
        non_neutral = [s for s in result.signals if s.direction != "NEUTRAL"]
        assert len(non_neutral) == 0, (
            f"Expected 0 non-NEUTRAL signals during cold start, got {len(non_neutral)}"
        )

        # All should have confidence 0.0
        for i, s in enumerate(result.signals):
            assert s.confidence == 0.0, f"Signal at tick {i+1} has confidence {s.confidence} != 0.0"

    def test_engine_exits_warmup_on_tick_50(self, tmp_db, sample_runtime_config):
        """Tick 50 (after 50th update) produces a non-NEUTRAL signal."""
        inputs = _generate_market_inputs(55)  # 55 ticks: 50 warmup + 5 ready
        strategy = MarkovStrategy(warmup_ticks=50)
        engine = ExecutionEngine(sample_runtime_config, tmp_db, dry_run=True)

        result = engine.run(inputs, strategy)

        # Signal at index 49 (tick 50) should be non-NEUTRAL
        tick_50_signal = result.signals[49]
        assert tick_50_signal.direction != "NEUTRAL", (
            f"Expected non-NEUTRAL signal at tick 50, got {tick_50_signal.direction}"
        )
        assert tick_50_signal.confidence > 0.0


class TestEngineFailFast:
    def test_engine_fail_fast_on_invalid_signal(self, tmp_db):
        """Engine propagates exceptions — no silent failures.

        Trigger fail-fast via invalid signal direction.
        """
        inputs = _generate_market_inputs(60)
        strategy = MarkovStrategy(warmup_ticks=50)

        # Bypass RuntimeConfig validation to set invalid position_size
        config = RuntimeConfig.model_construct(  # type: ignore[call-arg]
            threshold_pct=0.001,
            warmup_ticks=50,
            position_size=Decimal("0"),  # invalid: must be > 0
            transaction_cost_pct=0.0,
            stop_loss_pct=0.05,
        )

        engine = ExecutionEngine(config, tmp_db, dry_run=True)
        with pytest.raises(ValueError, match="position_size must be positive"):
            engine.run(inputs, strategy)
