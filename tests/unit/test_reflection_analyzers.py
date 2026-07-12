"""Tests for reflection analyzers: OutcomeAnalyzer, SignalQualityAnalyzer, DriftAnalyzer.

All analyzers are stateless and deterministic. Tests use fixture DB with known
rows and assert exact output.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest

from trady_ai.reflection.models import DriftEvent, OutcomeSummary, SignalQualityReport

# ── Fixture helpers ──────────────────────────────────────────────────────────


def _insert_signal(db, idx: int, timestamp: str, confidence: float = 0.5,
                   strategy_name: str = "markov_persistence") -> str:
    """Insert a signal row and return its UUID str id."""
    sig_id = str(uuid5(NAMESPACE_URL, f"signal:{idx}:{timestamp}"))
    db.execute(
        "INSERT INTO signals (id, timestamp, market_id, direction, confidence, strategy_name) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [sig_id, timestamp, "PM-5M", "LONG", confidence, strategy_name],
    )
    return sig_id


def _insert_position(db, pos_idx: int, pnl: Decimal | None, status: str,
                     signal_id: str, market_id: str = "PM-5M") -> str:
    """Insert a position row and return its UUID str id."""
    pos_id = str(uuid5(NAMESPACE_URL, f"pos:{pos_idx}:{market_id}"))
    db.execute(
        "INSERT INTO positions (id, market_id, direction, entry_price, current_price, "
        "size, pnl, status, signal_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [pos_id, market_id, "LONG", "100.0", "100.0", "1.0",
         str(pnl) if pnl is not None else None, status, signal_id],
    )
    return pos_id


def _insert_trade(db, trade_idx: int, signal_id: str, position_id: str,
                  timestamp: str, action: str = "CLOSE") -> str:
    """Insert a trade row and return its UUID str id."""
    trade_id = str(uuid5(NAMESPACE_URL, f"trade:{trade_idx}:{timestamp}"))
    db.execute(
        "INSERT INTO trades (id, signal_id, position_id, action, price, size, timestamp, dry_run) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [trade_id, signal_id, position_id, action, "100.0", "1.0", timestamp, 1],
    )
    return trade_id


def _insert_snapshot(db, strategy_name: str, domain: str, tick_number: int,
                     transition_counts: list[list[int]]) -> None:
    """Insert a strategy_snapshot row."""
    db.execute(
        "INSERT INTO strategy_snapshots "
        "(strategy_name, domain, tick_number, transition_counts, state_counts, "
        "warmup_ticks, threshold_pct, snapshot_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [strategy_name, domain, tick_number,
         json.dumps(transition_counts), json.dumps([10, 10, 10]),
         50, "0.001", datetime.now(UTC).isoformat()],
    )


# ── OutcomeAnalyzer Tests ────────────────────────────────────────────────────


class TestOutcomeAnalyzer:
    """OutcomeAnalyzer computes trade outcome statistics for a time range."""

    def test_empty_trades_returns_zeroed_summary(self, tmp_db) -> None:
        """No trades in range → zeroed OutcomeSummary."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert isinstance(result, OutcomeSummary)
        assert result.total_trades == 0
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.win_rate == 0.0
        assert result.total_pnl == Decimal("0")
        assert result.avg_pnl_per_trade == Decimal("0")
        assert result.max_drawdown == Decimal("0")

    def test_single_winning_trade(self, tmp_db) -> None:
        """Single winning trade → win_rate=1.0, pnl computed."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        sig_id = _insert_signal(tmp_db, 1, "2026-07-10T10:00:00")
        pos_id = _insert_position(tmp_db, 1, Decimal("50.00"), "CLOSED", sig_id)
        _insert_trade(tmp_db, 1, sig_id, pos_id, "2026-07-10T10:00:00")

        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_trades == 1
        assert result.winning_trades == 1
        assert result.losing_trades == 0
        assert result.win_rate == 1.0
        assert result.total_pnl == Decimal("50.00")
        assert result.avg_pnl_per_trade == Decimal("50.00")

    def test_single_losing_trade(self, tmp_db) -> None:
        """Single losing trade → win_rate=0.0, negative pnl."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        sig_id = _insert_signal(tmp_db, 2, "2026-07-10T10:00:00")
        pos_id = _insert_position(tmp_db, 2, Decimal("-30.00"), "CLOSED", sig_id)
        _insert_trade(tmp_db, 2, sig_id, pos_id, "2026-07-10T10:00:00")

        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_trades == 1
        assert result.winning_trades == 0
        assert result.losing_trades == 1
        assert result.win_rate == 0.0
        assert result.total_pnl == Decimal("-30.00")
        assert result.avg_pnl_per_trade == Decimal("-30.00")

    def test_mixed_trades_computes_win_rate_and_pnl(self, tmp_db) -> None:
        """7 winning, 3 losing → win_rate=0.7, total_pnl=150.0."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        pnls = [Decimal("50"), Decimal("30"), Decimal("20"), Decimal("10"),
                Decimal("40"), Decimal("5"), Decimal("15"),  # 7 winning
                Decimal("-10"), Decimal("-5"), Decimal("-5")]  # 3 losing
        for i, pnl in enumerate(pnls):
            ts = f"2026-07-10T10:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 100 + i, ts)
            pos_id = _insert_position(tmp_db, 100 + i, pnl, "CLOSED", sig_id)
            _insert_trade(tmp_db, 100 + i, sig_id, pos_id, ts)

        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_trades == 10
        assert result.winning_trades == 7
        assert result.losing_trades == 3
        assert result.win_rate == pytest.approx(0.7)
        assert result.total_pnl == Decimal("150")
        assert result.avg_pnl_per_trade == Decimal("15")

    def test_max_drawdown_calculation(self, tmp_db) -> None:
        """Sequence [50, -30, 20, -10] → max_drawdown=30."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        # PnL sequence: +50, -30, +20, -10
        # running: 50, 20, 40, 30
        # peak: 50, 50, 50, 50
        # drawdown: 0, 30, 10, 20 → max=30
        pnls = [Decimal("50"), Decimal("-30"), Decimal("20"), Decimal("-10")]
        for i, pnl in enumerate(pnls):
            ts = f"2026-07-10T10:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 200 + i, ts)
            pos_id = _insert_position(tmp_db, 200 + i, pnl, "CLOSED", sig_id)
            _insert_trade(tmp_db, 200 + i, sig_id, pos_id, ts)

        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.max_drawdown == Decimal("30")

    def test_max_drawdown_all_positive(self, tmp_db) -> None:
        """Sequence
        [10, 20, 30, 5, 15] → max_drawdown=25
        running: 10, 30, 60, 65, 80
        peak: 10, 30, 60, 65, 80
        drawdown: 0, 0, 0, 0, 0 → max=0

        Actually let me redo: [10, 20, 30, -45, 15]
        running: 10, 30, 60, 15, 30
        peak: 10, 30, 60, 60, 60
        drawdown: 0, 0, 0, 45, 30 → max=45
        """
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        pnls = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("-45"), Decimal("15")]
        for i, pnl in enumerate(pnls):
            ts = f"2026-07-10T10:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 300 + i, ts)
            pos_id = _insert_position(tmp_db, 300 + i, pnl, "CLOSED", sig_id)
            _insert_trade(tmp_db, 300 + i, sig_id, pos_id, ts)

        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.max_drawdown == Decimal("45")

    def test_deterministic_output(self, tmp_db) -> None:
        """Same input twice → same output."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        pnls = [Decimal("10"), Decimal("-5"), Decimal("20")]
        for i, pnl in enumerate(pnls):
            ts = f"2026-07-10T10:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 400 + i, ts)
            pos_id = _insert_position(tmp_db, 400 + i, pnl, "CLOSED", sig_id)
            _insert_trade(tmp_db, 400 + i, sig_id, pos_id, ts)

        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result1 = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        result2 = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result1.total_trades == result2.total_trades
        assert result1.win_rate == result2.win_rate
        assert result1.total_pnl == result2.total_pnl
        assert result1.max_drawdown == result2.max_drawdown

    def test_trades_outside_time_range_excluded(self, tmp_db) -> None:
        """Trades outside the time range are not counted."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        # Trade inside range
        sig1 = _insert_signal(tmp_db, 500, "2026-07-10T12:00:00")
        pos1 = _insert_position(tmp_db, 500, Decimal("10"), "CLOSED", sig1)
        _insert_trade(tmp_db, 500, sig1, pos1, "2026-07-10T12:00:00")
        # Trade outside range (too early)
        sig2 = _insert_signal(tmp_db, 501, "2026-07-09T12:00:00")
        pos2 = _insert_position(tmp_db, 501, Decimal("20"), "CLOSED", sig2)
        _insert_trade(tmp_db, 501, sig2, pos2, "2026-07-09T12:00:00")

        from trady_ai.reflection.analyzers.outcome import OutcomeAnalyzer

        analyzer = OutcomeAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_trades == 1
        assert result.total_pnl == Decimal("10")


# ── SignalQualityAnalyzer Tests ─────────────────────────────────────────────


class TestSignalQualityAnalyzer:
    """SignalQualityAnalyzer measures signal accuracy and confidence."""

    def test_empty_signals_returns_zeroed(self, tmp_db) -> None:
        """No signals in range → zeroed report."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert isinstance(result, SignalQualityReport)
        assert result.total_signals == 0
        assert result.signals_with_trades == 0
        assert result.signal_accuracy == 0.0
        assert result.avg_confidence == 0.0

    def test_all_signals_have_trades(self, tmp_db) -> None:
        """Every signal has a trade → accuracy=1.0."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        for i in range(5):
            ts = f"2026-07-10T10:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 1000 + i, ts, confidence=0.6)
            pos_id = _insert_position(tmp_db, 1000 + i, Decimal("10"), "CLOSED", sig_id)
            _insert_trade(tmp_db, 1000 + i, sig_id, pos_id, ts)

        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_signals == 5
        assert result.signals_with_trades == 5
        assert result.signal_accuracy == 1.0

    def test_no_signals_have_trades(self, tmp_db) -> None:
        """No signals have trades → accuracy=0.0."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        for i in range(3):
            _insert_signal(tmp_db, 2000 + i, f"2026-07-10T10:{i:02d}:00", confidence=0.5)

        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_signals == 3
        assert result.signals_with_trades == 0
        assert result.signal_accuracy == 0.0

    def test_partial_signal_accuracy(self, tmp_db) -> None:
        """3 of 5 signals have trades → accuracy=0.6."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        # Signals 0,1,2 have trades; 3,4 do not
        for i in range(3):
            ts = f"2026-07-10T10:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 3000 + i, ts, confidence=0.5)
            pos_id = _insert_position(tmp_db, 3000 + i, Decimal("10"), "CLOSED", sig_id)
            _insert_trade(tmp_db, 3000 + i, sig_id, pos_id, ts)
        for i in range(3, 5):
            _insert_signal(tmp_db, 3000 + i, f"2026-07-10T10:{i:02d}:00", confidence=0.5)

        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_signals == 5
        assert result.signals_with_trades == 3
        assert result.signal_accuracy == pytest.approx(0.6)

    def test_avg_confidence_calculation(self, tmp_db) -> None:
        """Signals with confidences [0.5, 0.7, 0.9] → avg=0.7."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        confidences = [0.5, 0.7, 0.9]
        for i, conf in enumerate(confidences):
            _insert_signal(tmp_db, 4000 + i, f"2026-07-10T10:{i:02d}:00", confidence=conf)

        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.total_signals == 3
        assert result.avg_confidence == pytest.approx(0.7)

    def test_confidence_binning_empty(self, tmp_db) -> None:
        """GIVEN no signals THEN confidence_bins has zeroed bins."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")
        assert result.confidence_bins == {
            "high": {"count": 0.0, "winning": 0.0, "win_rate": 0.0},
            "low": {"count": 0.0, "winning": 0.0, "win_rate": 0.0},
        }

    def test_confidence_binning_high_low(self, tmp_db) -> None:
        """GIVEN 20 signals with varying confidence (10 high, 10 low)
        WHEN SignalQualityAnalyzer runs
        THEN confidence_bins shows high and low bins with correct win rates."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)

        # 10 high-confidence signals (>= 0.7), 8 with profitable trades
        for i in range(10):
            ts = f"2026-07-10T10:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 5000 + i, ts, confidence=0.8)
            if i < 8:
                pos_id = _insert_position(tmp_db, 5000 + i, Decimal("50"), "CLOSED", sig_id)
                _insert_trade(tmp_db, 5000 + i, sig_id, pos_id, ts)
            # Signals 8 and 9 have no trades at all

        # 10 low-confidence signals (< 0.7), 3 with profitable trades
        for i in range(10):
            ts = f"2026-07-10T11:{i:02d}:00"
            sig_id = _insert_signal(tmp_db, 5010 + i, ts, confidence=0.3)
            if i < 3:
                pos_id = _insert_position(tmp_db, 5010 + i, Decimal("50"), "CLOSED", sig_id)
                _insert_trade(tmp_db, 5010 + i, sig_id, pos_id, ts)
            # Signals 3-9 have no trades at all

        from trady_ai.reflection.analyzers.signal_quality import SignalQualityAnalyzer

        analyzer = SignalQualityAnalyzer()
        result = analyzer.analyze(tmp_db, "PM-5M", "2026-07-10T00:00:00", "2026-07-10T23:59:59")

        assert result.total_signals == 20
        # 8 (high profitable) + 3 (low profitable) = 11 signals with trades
        assert result.signals_with_trades == 11
        assert result.signal_accuracy == pytest.approx(11 / 20)
        assert result.avg_confidence == pytest.approx((10 * 0.8 + 10 * 0.3) / 20)

        bins = result.confidence_bins
        assert "high" in bins
        assert "low" in bins

        # High bin: 10 signals, 8 winning
        assert bins["high"]["count"] == 10.0
        assert bins["high"]["winning"] == 8.0
        assert bins["high"]["win_rate"] == pytest.approx(0.8)

        # Low bin: 10 signals, 3 winning
        assert bins["low"]["count"] == 10.0
        assert bins["low"]["winning"] == 3.0
        assert bins["low"]["win_rate"] == pytest.approx(0.3)


# ── DriftAnalyzer Tests ────────────────────────────────────────────────────


class TestDriftAnalyzer:
    """DriftAnalyzer detects deviations in transition matrices."""

    def test_no_snapshots_returns_empty(self, tmp_db) -> None:
        """No snapshots in DB → empty list."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        result = analyzer.analyze(tmp_db, "markov_persistence", "PM-5M")
        assert result == []

    def test_single_snapshot_returns_empty(self, tmp_db) -> None:
        """Only one snapshot → empty list (cannot compare)."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 100,
                         [[10, 2, 1], [2, 15, 3], [1, 2, 10]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        result = analyzer.analyze(tmp_db, "markov_persistence", "PM-5M")
        assert result == []

    def test_no_drift_below_threshold(self, tmp_db) -> None:
        """Similar snapshots → no drift (deviations < 15%)."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 100,
                         [[100, 10, 5], [8, 120, 6], [3, 4, 90]])
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 200,
                         [[105, 11, 5], [9, 125, 6], [3, 4, 95]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        result = analyzer.analyze(tmp_db, "markov_persistence", "PM-5M")
        assert result == []

    def test_drift_above_threshold_detected(self, tmp_db) -> None:
        """Large deviation → DriftEvent returned."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        # transition_counts for [0][0] (UP→UP): 100 vs 50 = 50% deviation
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 100,
                         [[100, 10, 5], [8, 120, 6], [3, 4, 90]])
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 200,
                         [[50, 10, 5], [8, 120, 6], [3, 4, 90]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        result = analyzer.analyze(tmp_db, "markov_persistence", "PM-5M")
        assert len(result) == 1
        event = result[0]
        assert isinstance(event, DriftEvent)
        assert event.strategy_id == "markov_persistence"
        assert event.domain == "PM-5M"
        assert event.previous_value == 100.0
        assert event.current_value == 50.0
        assert event.threshold == 0.15
        assert event.deviation_pct == pytest.approx(50.0)

    def test_explicit_ticks_baseline_comparison(self, tmp_db) -> None:
        """Specifying baseline_tick and comparison_tick works."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 50,
                         [[200, 10, 5], [8, 200, 6], [3, 4, 200]])
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 100,
                         [[100, 10, 5], [8, 120, 6], [3, 4, 90]])
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 200,
                         [[50, 10, 5], [8, 120, 6], [3, 4, 90]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        result = analyzer.analyze(tmp_db, "markov_persistence", "PM-5M",
                                  baseline_tick=50, comparison_tick=200)
        assert len(result) >= 1
        # The [0][0] went from 200→50: 75% deviation
        events = {e.metric: e for e in result}
        assert "transition_0_0" in events
        assert events["transition_0_0"].previous_value == 200.0
        assert events["transition_0_0"].current_value == 50.0

    def test_only_one_tick_raises_valueerror(self, tmp_db) -> None:
        """Only baseline_tick provided → ValueError."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 100,
                         [[100, 10, 5], [8, 120, 6], [3, 4, 90]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        with pytest.raises(ValueError, match="both baseline_tick"):
            analyzer.analyze(tmp_db, "markov_persistence", "PM-5M",
                             baseline_tick=100, comparison_tick=None)

    def test_only_comparison_tick_raises_valueerror(self, tmp_db) -> None:
        """Only comparison_tick provided → ValueError."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 100,
                         [[100, 10, 5], [8, 120, 6], [3, 4, 90]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        with pytest.raises(ValueError, match="both baseline_tick"):
            analyzer.analyze(tmp_db, "markov_persistence", "PM-5M",
                             baseline_tick=None, comparison_tick=200)

    def test_drift_multiple_metrics(self, tmp_db) -> None:
        """Multiple cells exceed threshold → multiple DriftEvents."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        # [0][0]: 100→50 (50% drift), [1][1]: 120→60 (50% drift)
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 100,
                         [[100, 10, 5], [8, 120, 6], [3, 4, 90]])
        _insert_snapshot(tmp_db, "markov_persistence", "PM-5M", 200,
                         [[50, 10, 5], [8, 60, 6], [3, 4, 90]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        result = analyzer.analyze(tmp_db, "markov_persistence", "PM-5M")
        assert len(result) == 2
        metrics = {e.metric for e in result}
        assert "transition_0_0" in metrics
        assert "transition_1_1" in metrics

    def test_drift_empty_snapshot_range(self, tmp_db) -> None:
        """No snapshots for this strategy/domain → empty list."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        _insert_snapshot(tmp_db, "other_strategy", "OTHER-DOM", 100,
                         [[100, 10, 5], [8, 120, 6], [3, 4, 90]])

        from trady_ai.reflection.analyzers.drift import DriftAnalyzer

        analyzer = DriftAnalyzer()
        result = analyzer.analyze(tmp_db, "markov_persistence", "PM-5M")
        assert result == []
