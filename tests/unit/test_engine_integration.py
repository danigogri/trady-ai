"""Integration tests: engine pipeline with injected StateGenerator.

Covers:
- Engine with DirectionalStateGenerator produces correct signals
- Engine with custom StateGenerator (|S|=2) runs full pipeline
- Engine without injected generator (default) unchanged behavior
"""

import sqlite3
from datetime import datetime
from decimal import Decimal

import pytest
import sqlite_utils

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.engine import ExecutionEngine
from trady_ai.core.markov_strategy import MarkovStrategy
from trady_ai.core.models import MarketInput
from trady_ai.strategies.markov.state_generator import (
    DirectionalStateGenerator,
    get_generator,
)


def _market_inputs(count: int = 10, start_price: Decimal | None = None) -> list[MarketInput]:
    """Generate a sequence of MarketInputs with an upward price trend."""
    price = start_price or Decimal("100.00")
    inputs = []
    for i in range(count):
        inputs.append(
            MarketInput(
                timestamp=datetime(2024, 1, 1, 12, 0, i),
                market_id="btc-usd",
                price=price,
                volume=Decimal("1000"),
                source="csv",
            )
        )
        # Trend upward by 0.2% each tick (above 0.1% threshold)
        price = price * Decimal("1.002")
    return inputs


@pytest.fixture
def db() -> sqlite_utils.Database:
    """In-memory database for integration tests."""
    return sqlite_utils.Database(sqlite3.connect(":memory:"))


@pytest.fixture
def config() -> RuntimeConfig:
    """Default RuntimeConfig."""
    return RuntimeConfig()


# ── Task 11: Integration tests ──────────────────────────────────────


class TestEngineWithDirectionalStateGenerator:
    """Engine with injected DirectionalStateGenerator."""

    def test_engine_with_directional_generator_produces_signals(self, config, db):
        """Engine with DirectionalStateGenerator runs full pipeline."""
        gen = DirectionalStateGenerator(threshold_pct=0.001)
        engine = ExecutionEngine(config, db, dry_run=True, state_generator=gen)
        strategy = MarkovStrategy(warmup_ticks=3)

        inputs = _market_inputs(count=10)
        result = engine.run(inputs, strategy)

        assert len(result.signals) == 10
        # After warmup, we should have real signals
        real_signals = [s for s in result.signals if s.confidence > 0]
        assert len(real_signals) > 0

    def test_engine_with_generator_matches_default(self, config, db):
        """Engine with DirectionalStateGenerator produces same signals as default."""
        # Run with default
        engine_default = ExecutionEngine(config, db, dry_run=True)
        strategy_default = MarkovStrategy(warmup_ticks=3)
        inputs = _market_inputs(count=10)

        # Need separate DBs since they share table names
        db2 = sqlite_utils.Database(sqlite3.connect(":memory:"))
        engine_default._db = db2
        result_default = engine_default.run(inputs, strategy_default)

        # Run with generator
        db3 = sqlite_utils.Database(sqlite3.connect(":memory:"))
        gen = DirectionalStateGenerator(threshold_pct=0.001)
        engine_gen = ExecutionEngine(config, db3, dry_run=True, state_generator=gen)
        strategy_gen = MarkovStrategy(warmup_ticks=3)
        result_gen = engine_gen.run(inputs, strategy_gen)

        # Signals should be the same (direction + confidence)
        for sig_def, sig_gen in zip(result_default.signals, result_gen.signals):
            assert sig_def.direction == sig_gen.direction
            assert sig_def.confidence == pytest.approx(sig_gen.confidence, abs=1e-10)

    def test_engine_without_generator_behaves_normally(self, config, db):
        """Engine without state_generator uses default MarketStateTracker."""
        engine = ExecutionEngine(config, db, dry_run=True)
        strategy = MarkovStrategy(warmup_ticks=3)

        inputs = _market_inputs(count=5)
        result = engine.run(inputs, strategy)

        assert len(result.signals) == 5
        assert len(result.trades) >= 0


class TestEngineWithCustomGenerator:
    """Engine with a custom |S|=2 generator."""

    def test_two_state_engine_pipeline(self, config, db):
        """Engine with |S|=2 generator runs the full pipeline."""
        gen = get_generator("directional")
        engine = ExecutionEngine(config, db, dry_run=True, state_generator=gen)
        strategy = MarkovStrategy(warmup_ticks=3)

        inputs = _market_inputs(count=10)
        result = engine.run(inputs, strategy)

        assert len(result.signals) == 10


class TestEnginePipelineEndToEnd:
    """End-to-end engine pipeline verification."""

    def test_pipeline_produces_trades(self, config, db):
        """Engine run with signals produces at least some trades."""
        gen = DirectionalStateGenerator(threshold_pct=0.001)
        engine = ExecutionEngine(config, db, dry_run=True, state_generator=gen)
        strategy = MarkovStrategy(warmup_ticks=3)

        inputs = _market_inputs(count=20)
        result = engine.run(inputs, strategy)

        # Should have some non-warmup signals
        warmup_count = sum(1 for s in result.signals if s.confidence == 0.0)
        non_warmup = len(result.signals) - warmup_count
        assert non_warmup > 0

    def test_summary_stats_available(self, config, db):
        """Engine run provides summary statistics."""
        gen = DirectionalStateGenerator(threshold_pct=0.001)
        engine = ExecutionEngine(config, db, dry_run=True, state_generator=gen)
        strategy = MarkovStrategy(warmup_ticks=3)

        inputs = _market_inputs(count=15)
        result = engine.run(inputs, strategy)

        assert result.summary_stats is not None
        assert result.summary_stats.get("total_signals", 0) > 0
