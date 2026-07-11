"""Unit tests for ExecutionEngine.run_from_store()."""
from unittest.mock import MagicMock

import pytest

from trady_ai.core.engine import ExecutionEngine, ExecutionResult
from trady_ai.core.models import MarketInput
from trady_ai.core.persistence import append_event, init_event_store
from trady_ai.core.signal_strategy import SignalStrategy


def _insert_events(db, count: int = 5) -> list[int]:
    """Insert count events into event_store and return their seq numbers."""
    init_event_store(db)
    seqs = []
    for i in range(count):
        ev = {
            "event_id": f"id:{i}",
            "market_id": "btc-usd",
            "price": f"{50000 + i * 100}.00",
            "volume": "100.00",
            "timestamp": f"2024-01-01T12:{i:02d}:00Z",
            "event_type": "tick",
            "source": "polymarket",
            "raw_payload": '{"test": true}',
        }
        seq = append_event(db, ev)
        seqs.append(seq)
    return seqs


# ── TestRunFromStore ─────────────────────────────────────────────────────────


class TestRunFromStore:
    def test_run_from_store_delegates_to_run(self, tmp_db, sample_runtime_config):
        """run_from_store reads events and passes them + strategy to run()."""
        seqs = _insert_events(tmp_db, 5)
        assert len(seqs) == 5

        engine = ExecutionEngine(sample_runtime_config, tmp_db)
        engine.run = MagicMock(return_value=ExecutionResult())

        strategy = MagicMock(spec=SignalStrategy)
        engine.run_from_store(strategy, since_seq=0)

        engine.run.assert_called_once()
        args, _ = engine.run.call_args
        inputs, passed_strategy = args[0], args[1]

        assert len(inputs) == 5
        assert all(isinstance(inp, MarketInput) for inp in inputs)
        assert inputs[0].market_id == "btc-usd"
        assert inputs[0].source == "polymarket"
        assert passed_strategy is strategy

    def test_run_from_store_with_since_seq(self, tmp_db, sample_runtime_config):
        """since_seq filters events: only seq > since_seq are passed."""
        seqs = _insert_events(tmp_db, 5)
        assert seqs == [1, 2, 3, 4, 5]

        engine = ExecutionEngine(sample_runtime_config, tmp_db)
        engine.run = MagicMock(return_value=ExecutionResult())

        strategy = MagicMock(spec=SignalStrategy)
        engine.run_from_store(strategy, since_seq=3)

        engine.run.assert_called_once()
        args, _ = engine.run.call_args
        inputs = args[0]

        assert len(inputs) == 2  # seq 4 and 5

    def test_run_from_store_raises_on_negative_seq(self, tmp_db,
                                                   sample_runtime_config):
        """since_seq < 0 raises ValueError (from get_events)."""
        engine = ExecutionEngine(sample_runtime_config, tmp_db)
        strategy = MagicMock(spec=SignalStrategy)

        with pytest.raises(ValueError, match="since_seq must be >= 0"):
            engine.run_from_store(strategy, since_seq=-1)

    def test_run_from_store_empty_store(self, tmp_db, sample_runtime_config):
        """run_from_store with empty store passes empty inputs to run()."""
        init_event_store(tmp_db)

        engine = ExecutionEngine(sample_runtime_config, tmp_db)
        engine.run = MagicMock(return_value=ExecutionResult())

        strategy = MagicMock(spec=SignalStrategy)
        engine.run_from_store(strategy, since_seq=0)

        engine.run.assert_called_once()
        args, _ = engine.run.call_args
        inputs = args[0]
        assert inputs == []
