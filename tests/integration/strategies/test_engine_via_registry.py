"""Integration test: engine produces identical results via registry vs direct.

Verifies that loading a strategy via StrategyRegistry.get() yields
the same pipeline output as passing the strategy instance directly.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.core.engine import ExecutionEngine
from trady_ai.core.models import MarketInput
from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine
from trady_ai.strategies.registry import StrategyRegistry


def _generate_inputs(count: int, start_price: Decimal = Decimal("100.00")) -> list[MarketInput]:
    """Generate deterministic market inputs with price variation."""
    base_ts = datetime(2024, 1, 1, 12, 0, 0)
    inputs: list[MarketInput] = []
    price = start_price

    for i in range(count):
        cycle = (i // 10) % 4
        if cycle == 0:
            price = start_price * Decimal("1.02")
        elif cycle == 1:
            price = start_price
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

    return inputs


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def runtime_config():
    return RuntimeConfig()


@pytest.fixture
def inputs():
    return _generate_inputs(60)


class TestEngineViaRegistry:
    """Engine pipeline produces identical results via registry vs direct strategy."""

    def test_registry_path_matches_direct(self, inputs, runtime_config):
        """Engine with registry.get('PM-5M', 'markov_persistence') matches direct arg."""
        import sqlite3

        import sqlite_utils

        # ── Direct path ─────────────────────────────────────────────────
        db1 = sqlite_utils.Database(sqlite3.connect(":memory:"))
        engine1 = ExecutionEngine(runtime_config, db1)
        strategy_direct = MarkovPersistenceEngine(warmup_ticks=50)
        direct_result = engine1.run(inputs, strategy_direct)

        # ── Registry path ───────────────────────────────────────────────
        db2 = sqlite_utils.Database(sqlite3.connect(":memory:"))
        engine2 = ExecutionEngine(runtime_config, db2)
        registry = StrategyRegistry()
        registry.register(
            "PM-5M", "markov_persistence",
            lambda: MarkovPersistenceEngine(warmup_ticks=50),
        )
        strategy_registry = registry.get("PM-5M", "markov_persistence")
        registry_result = engine2.run(inputs, strategy_registry)

        # ── Compare signals ─────────────────────────────────────────────
        assert len(direct_result.signals) == len(registry_result.signals), (
            f"Signal count mismatch: {len(direct_result.signals)} vs {len(registry_result.signals)}"
        )

        for i, (ds, rs) in enumerate(zip(direct_result.signals, registry_result.signals)):
            assert ds.id == rs.id, f"Signal {i}: id mismatch"
            assert ds.direction == rs.direction, f"Signal {i}: direction mismatch"
            assert ds.confidence == pytest.approx(rs.confidence), f"Signal {i}: confidence mismatch"

    def test_registry_strategy_is_signal_strategy(self):
        """Strategy from registry IS-A SignalStrategy."""
        registry = StrategyRegistry()
        registry.register(
            "PM-5M", "markov_persistence",
            lambda: MarkovPersistenceEngine(warmup_ticks=50),
        )
        strategy = registry.get("PM-5M", "markov_persistence")
        from trady_ai.core.signal_strategy import SignalStrategy

        assert isinstance(strategy, SignalStrategy)
