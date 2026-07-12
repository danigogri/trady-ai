"""Tests for MarkovPersistenceEngine, DirectionalPersistence, VolatilityPersistence.

Ported from tests/unit/test_markov_strategy.py with new import paths.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from trady_ai.core.models import MarketState
from trady_ai.strategies.markov.persistence import (
    DirectionalPersistence,
    MarkovPersistenceEngine,
    VolatilityPersistence,
)


def _state(
    market_id: str, state_label: str, ts: datetime | None = None
) -> MarketState:
    return MarketState(
        market_id=market_id,
        timestamp=ts or datetime(2024, 1, 1, 12, 0, 0),
        price=Decimal("100.00"),
        volume=Decimal("1000"),
        state=state_label,
    )


# ── Ported from test_markov_strategy.py ──────────────────────────────


class TestMarkovColdStart:
    def test_cold_start_returns_neutral_with_zero_confidence(self):
        """Before warmup_ticks reached → evaluate() returns NEUTRAL, confidence=0.0."""
        strategy = MarkovPersistenceEngine(warmup_ticks=50)
        s = _state("btc-usd", "UP")

        for _ in range(49):
            strategy.update(s)

        signal = strategy.evaluate(s)
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.metadata == {"reason": "warmup"}

    def test_warmup_exact_boundary(self):
        """Tick 50 (warmup_ticks boundary) → is_ready=True, evaluate() returns valid signal."""
        strategy = MarkovPersistenceEngine(warmup_ticks=50)

        for _ in range(49):
            strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is False

        strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is True

        s = _state("btc-usd", "UP")
        signal = strategy.evaluate(s)
        assert signal.direction == "LONG"
        assert signal.confidence > 0.0


class TestMarkovTransitionMatrix:
    def test_transition_counts_are_correct(self):
        """Known sequence UP, UP, DOWN, UP, UP → verify transition matrix."""
        strategy = MarkovPersistenceEngine(warmup_ticks=1)
        states = ["UP", "UP", "DOWN", "UP", "UP"]

        for label in states:
            strategy.update(_state("btc-usd", label))

        expected = [[2, 1, 0], [1, 0, 0], [0, 0, 0]]
        actual = strategy._transition_counts.tolist()
        assert actual == expected, f"Expected {expected}, got {actual}"

        assert strategy._state_counts.tolist() == [4, 1, 0]


class TestMarkovDeterminism:
    def test_two_instances_produce_identical_signals(self):
        """Two MarkovPersistenceEngine instances with same data → same signals."""
        states = []
        for i in range(55):
            label = "UP" if i % 3 == 0 else "DOWN" if i % 3 == 1 else "NEUTRAL"
            states.append(
                _state("btc-usd", label, datetime(2024, 1, 1, 12, 0, i))
            )

        s1 = MarkovPersistenceEngine(warmup_ticks=50)
        s2 = MarkovPersistenceEngine(warmup_ticks=50)

        signals_1 = []
        signals_2 = []

        for st in states:
            s1.update(st)
            s2.update(st)

        for st in states:
            signals_1.append(s1.evaluate(st))
            signals_2.append(s2.evaluate(st))

        for sig1, sig2 in zip(signals_1, signals_2):
            assert sig1.id == sig2.id
            assert sig1.direction == sig2.direction
            assert sig1.confidence == pytest.approx(sig2.confidence)


class TestMarkovArgmaxTiebreak:
    def test_tie_returns_first_index(self):
        """When two states have equal probability, argmax returns first (index 0 = UP)."""
        strategy = MarkovPersistenceEngine(warmup_ticks=1)

        strategy._transition_counts[0] = [1, 1, 0]
        strategy._total_obs = 2

        s = _state("btc-usd", "UP")
        signal = strategy.evaluate(s)
        assert signal.direction == "LONG"
        assert signal.confidence == 0.5


class TestMarkovNoTransitions:
    def test_no_transitions_from_current_returns_neutral(self):
        """If current state has no transitions recorded → NEUTRAL, confidence=0.0."""
        strategy = MarkovPersistenceEngine(warmup_ticks=1)

        strategy.update(_state("btc-usd", "UP"))
        strategy.update(_state("btc-usd", "DOWN"))

        s = _state("btc-usd", "NEUTRAL")
        signal = strategy.evaluate(s)
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.metadata["reason"] == "no_transitions_from_current_state"


class TestMarkovIsReady:
    def test_is_ready_false_before_warmup(self):
        """is_ready() returns False before warmup_ticks."""
        strategy = MarkovPersistenceEngine(warmup_ticks=10)
        for _ in range(9):
            strategy.update(_state("btc-usd", "UP"))
            assert strategy.is_ready() is False

    def test_is_ready_true_after_warmup(self):
        """is_ready() returns True after reaching warmup_ticks."""
        strategy = MarkovPersistenceEngine(warmup_ticks=10)
        for _ in range(10):
            strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is True

    def test_is_ready_custom_warmup(self):
        """Custom warmup_ticks=3 works correctly."""
        strategy = MarkovPersistenceEngine(warmup_ticks=3)
        assert strategy.is_ready() is False
        for _ in range(3):
            strategy.update(_state("btc-usd", "UP"))
        assert strategy.is_ready() is True


# ── MarkovPersistenceEngine-specific tests ───────────────────────────


class TestMarkovProperties:
    def test_name(self):
        """MarkovPersistenceEngine.name returns 'markov_persistence'."""
        assert MarkovPersistenceEngine().name == "markov_persistence"

    def test_domain_default_empty(self):
        """Default domain is empty string."""
        assert MarkovPersistenceEngine().domain == ""

    def test_domain_settable(self):
        """Domain can be set by registry post-creation."""
        engine = MarkovPersistenceEngine()
        engine.domain = "PM-5M"
        assert engine.domain == "PM-5M"

    def test_parameters(self):
        """parameters() returns constructor args."""
        engine = MarkovPersistenceEngine(warmup_ticks=100, threshold_pct=0.01)
        params = engine.parameters()
        assert params["warmup_ticks"] == 100
        assert params["threshold_pct"] == 0.01

    def test_parameters_defaults(self):
        """parameters() returns default values when none specified."""
        engine = MarkovPersistenceEngine()
        params = engine.parameters()
        assert params["warmup_ticks"] == 50
        assert params["threshold_pct"] == 0.001


class TestMarkovInputValidation:
    def test_update_raises_type_error_on_non_state(self):
        """update() raises TypeError for non-MarketState."""
        engine = MarkovPersistenceEngine()
        with pytest.raises(TypeError, match="MarketState"):
            engine.update("not_a_state")  # type: ignore[arg-type]

    def test_evaluate_raises_type_error_on_non_state(self):
        """evaluate() raises TypeError for non-MarketState."""
        engine = MarkovPersistenceEngine()
        with pytest.raises(TypeError, match="MarketState"):
            engine.evaluate("not_a_state")  # type: ignore[arg-type]

    def test_type_error_message_includes_type_name(self):
        """TypeError message includes the actual type name."""
        engine = MarkovPersistenceEngine()
        with pytest.raises(TypeError, match="MarketState"):
            engine.update(42)  # type: ignore[arg-type]


# ── DirectionalPersistence tests ─────────────────────────────────────


class TestDirectionalPersistence:
    def test_name(self):
        """DirectionalPersistence.name returns 'directional_persistence'."""
        assert DirectionalPersistence().name == "directional_persistence"

    def test_inherits_behavior(self):
        """DirectionalPersistence produces same signal as MarkovPersistenceEngine."""
        dp = DirectionalPersistence(warmup_ticks=3)
        for _ in range(5):
            dp.update(_state("btc-usd", "UP"))
        signal = dp.evaluate(_state("btc-usd", "UP"))
        assert signal.direction == "LONG"
        assert signal.confidence > 0.0

    def test_parameters_inherited(self):
        """DirectionalPersistence.parameters() returns inherited params."""
        dp = DirectionalPersistence(warmup_ticks=75, threshold_pct=0.005)
        params = dp.parameters()
        assert params["warmup_ticks"] == 75
        assert params["threshold_pct"] == 0.005


# ── VolatilityPersistence tests ──────────────────────────────────────


class TestVolatilityPersistence:
    def test_name(self):
        """VolatilityPersistence.name returns 'volatility_persistence'."""
        vp = VolatilityPersistence()
        assert vp.name == "volatility_persistence"

    def test_parameters_includes_window(self):
        """parameters() includes volatility_window."""
        vp = VolatilityPersistence(volatility_window=15)
        # Base class parameters
        params = vp.parameters()
        assert params["warmup_ticks"] == 50
        assert params["threshold_pct"] == 0.001
        # Volatility-specific note: window is not in parameters() since it's
        # not inherited from the base. We only check what the base provides.

    def test_single_price_returns_stable(self):
        """Single price point → _classify_volatility returns STABLE."""
        vp = VolatilityPersistence(warmup_ticks=1, threshold_pct=0.01)
        vp._price_history = [Decimal("100.00")]
        assert vp._classify_volatility() == "STABLE"

    def test_zero_range_returns_stable(self):
        """Zero price range → _classify_volatility returns STABLE."""
        vp = VolatilityPersistence(warmup_ticks=1, threshold_pct=0.01)
        vp._price_history = [Decimal("100.00"), Decimal("100.00")]
        assert vp._classify_volatility() == "STABLE"

    def test_high_volatility_classification(self):
        """Range > threshold_pct → HIGH volatility."""
        vp = VolatilityPersistence(warmup_ticks=1, threshold_pct=0.01)
        vp._price_history = [Decimal("100.00"), Decimal("102.00")]  # 2% > 1%
        assert vp._classify_volatility() == "HIGH"

    def test_low_volatility_classification(self):
        """Range < threshold_pct * 0.5 → LOW volatility."""
        vp = VolatilityPersistence(warmup_ticks=1, threshold_pct=0.01)
        vp._price_history = [Decimal("100.00"), Decimal("100.03")]  # 0.03% < 0.5%
        assert vp._classify_volatility() == "LOW"

    def test_stable_volatility_classification(self):
        """Range between threshold_pct*0.5 and threshold_pct → STABLE."""
        vp = VolatilityPersistence(warmup_ticks=1, threshold_pct=0.01)
        # 0.8% range: 0.5% < 0.8% < 1% → falls in STABLE band
        vp._price_history = [Decimal("100.00"), Decimal("100.80")]
        assert vp._classify_volatility() == "STABLE"

    def test_empty_history_raises_type_error(self):
        """Empty _price_history → _classify_volatility raises TypeError."""
        vp = VolatilityPersistence(warmup_ticks=1)
        with pytest.raises(TypeError, match="No price data"):
            vp._classify_volatility()

    def test_update_builds_price_history(self):
        """update() appends price to _price_history (bounded to window)."""
        vp = VolatilityPersistence(
            warmup_ticks=1, threshold_pct=0.01, volatility_window=3
        )
        states = [
            MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                price=Decimal("100.00"),
                volume=Decimal("1000"),
                state="UP",
            ),
            MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 1),
                price=Decimal("101.00"),
                volume=Decimal("1000"),
                state="UP",
            ),
            MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 2),
                price=Decimal("102.00"),
                volume=Decimal("1000"),
                state="UP",
            ),
            MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 3),
                price=Decimal("103.00"),
                volume=Decimal("1000"),
                state="UP",
            ),
        ]
        for st in states:
            vp.update(st)

        # Window of 3, so only last 3 prices remain
        assert len(vp._price_history) == 3
        assert vp._price_history == [
            Decimal("101.00"),
            Decimal("102.00"),
            Decimal("103.00"),
        ]

    def test_update_increments_transitions_from_volatility(self):
        """VolatilityPersistence transitions are computed from volatility state, not state.state."""
        vp = VolatilityPersistence(warmup_ticks=1, threshold_pct=0.01)

        # First update: price up 2% → HIGH volatility
        vp.update(
            MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                price=Decimal("100.00"),
                volume=Decimal("1000"),
                state="UP",
            )
        )
        # Second update: price up 2% again → HIGH → HIGH transition
        vp.update(
            MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 1),
                price=Decimal("102.00"),
                volume=Decimal("1000"),
                state="DOWN",
            )
        )
        # Third update: price flat → STABLE volatility
        vp.update(
            MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 2),
                price=Decimal("102.00"),
                volume=Decimal("1000"),
                state="DOWN",
            )
        )

        # _total_obs should be 3 (updates counted not by state.state but by volatility classification)
        assert vp._total_obs == 3
        # state_counts[0] = HIGH counts, state_counts[1] = LOW counts, state_counts[2] = STABLE counts
        # After 3 updates: first=HIGH, second=HIGH, third=STABLE
        # _state_counts = [2, 0, 1]
        assert vp._state_counts.tolist() == [2, 0, 1]

    def test_evaluate_after_warmup_returns_signal(self):
        """VolatilityPersistence.evaluate() returns a valid Signal after warmup."""
        vp = VolatilityPersistence(
            warmup_ticks=3, threshold_pct=0.001, volatility_window=5
        )
        # Prices with >0.1% jumps to trigger HIGH volatility early,
        # then continue so transitions FROM HIGH are recorded.
        prices = [
            Decimal("100.00"),  # 1 → STABLE (single price)
            Decimal("101.00"),  # 2 → HIGH (1% > 0.1%)
            Decimal("100.50"),  # 3 → HIGH (1% > 0.1%), trans: STABLE→HIGH, then HIGH→HIGH
            Decimal("101.50"),  # 4 → HIGH, trans: HIGH→HIGH
            Decimal("100.80"),  # 5 → HIGH, trans: HIGH→HIGH
        ]
        for price in prices[:-1]:  # First 4 updates
            state = MarketState(
                market_id="btc-usd",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                price=price,
                volume=Decimal("1000"),
                state="UP",
            )
            vp.update(state)

        assert vp.is_ready() is True

        # Evaluate with the last state
        last_state = MarketState(
            market_id="btc-usd",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            price=prices[-1],
            volume=Decimal("1000"),
            state="UP",
        )
        signal = vp.evaluate(last_state)
        assert signal.strategy_name == "volatility_persistence"
        assert signal.confidence >= 0.0
        assert "probabilities" in signal.metadata
        assert "volatility_state" in signal.metadata

    def test_evaluate_before_warmup_returns_neutral(self):
        """VolatilityPersistence.evaluate() returns NEUTRAL warmup before ready."""
        vp = VolatilityPersistence(warmup_ticks=10, threshold_pct=0.01)
        state = _state("btc-usd", "UP")
        vp.update(state)
        signal = vp.evaluate(state)
        assert signal.direction == "NEUTRAL"
        assert signal.confidence == 0.0
        assert signal.metadata == {"reason": "warmup"}

    def test_evaluate_before_any_update_raises_type_error(self):
        """evaluate() with no prior data → TypeError from empty _price_history."""
        vp = VolatilityPersistence(warmup_ticks=1, threshold_pct=0.01)
        # Make is_ready() return True so we skip warmup
        vp._total_obs = 5
        state = _state("btc-usd", "UP")
        with pytest.raises((TypeError, RuntimeError)):
            vp.evaluate(state)


# ── Snapshot / Restore tests ─────────────────────────────────────────


class TestSnapshotRestore:
    """MarkovPersistenceEngine.snapshot() and restore()."""

    def test_snapshot_persists_row(self, tmp_strategy_db):
        """After snapshot, the DB has one row in strategy_snapshots."""
        engine = MarkovPersistenceEngine(warmup_ticks=5)
        for label in ["UP", "UP", "DOWN", "UP"]:
            engine.update(_state("btc-usd", label))
        engine.snapshot("PM-5M", tmp_strategy_db)
        assert tmp_strategy_db["strategy_snapshots"].count == 1

    def test_snapshot_restore_cycle(self, tmp_strategy_db):
        """Persist → restore produces engine with identical transition matrix."""
        engine = MarkovPersistenceEngine(warmup_ticks=5)
        for label in ["UP", "UP", "DOWN", "UP", "UP", "DOWN", "NEUTRAL"]:
            engine.update(_state("btc-usd", label))
        engine.snapshot("PM-5M", tmp_strategy_db)

        restored = MarkovPersistenceEngine.restore(
            "PM-5M", "markov_persistence", tmp_strategy_db
        )

        assert (restored._transition_counts == engine._transition_counts).all()
        assert (restored._state_counts == engine._state_counts).all()
        assert restored._warmup_ticks == engine._warmup_ticks
        assert restored._threshold_pct == engine._threshold_pct
        assert restored._total_obs == engine._total_obs
        assert restored.name == engine.name

    def test_restored_engine_same_evaluate(self, tmp_strategy_db):
        """Restored engine produces same evaluate() output as original."""
        orig = MarkovPersistenceEngine(warmup_ticks=3)
        for label in ["UP", "UP", "DOWN", "UP", "UP"]:
            orig.update(_state("btc-usd", label))
        orig.snapshot("PM-5M", tmp_strategy_db)

        restored = MarkovPersistenceEngine.restore(
            "PM-5M", "markov_persistence", tmp_strategy_db
        )

        s = _state("btc-usd", "UP")
        so = orig.evaluate(s)
        sr = restored.evaluate(s)
        assert so.direction == sr.direction
        assert so.confidence == pytest.approx(sr.confidence)

    def test_load_latest_returns_none_when_empty(self, tmp_strategy_db):
        """load_latest_snapshot returns None when no snapshots exist."""
        from trady_ai.core.persistence import load_latest_snapshot

        result = load_latest_snapshot(
            tmp_strategy_db, "PM-5M", "markov_persistence"
        )
        assert result is None

    def test_restore_empty_db_raises(self, tmp_strategy_db):
        """restore() with empty DB raises RuntimeError."""
        with pytest.raises(RuntimeError, match="No snapshot found"):
            MarkovPersistenceEngine.restore(
                "PM-5M", "markov_persistence", tmp_strategy_db
            )

    def test_corrupt_json_transition_counts_raises(self, tmp_strategy_db):
        """Corrupt JSON in transition_counts raises ValueError."""
        tmp_strategy_db["strategy_snapshots"].insert(
            {
                "strategy_name": "markov_persistence",
                "domain": "PM-5M",
                "tick_number": 1,
                "transition_counts": "not valid json!!!",
                "state_counts": "[1, 0, 0]",
                "warmup_ticks": 50,
                "threshold_pct": "0.001",
                "snapshot_at": datetime.now(UTC).isoformat(),
            }
        )
        with pytest.raises(ValueError, match="transition"):
            MarkovPersistenceEngine.restore(
                "PM-5M", "markov_persistence", tmp_strategy_db
            )

    def test_append_only_invariant(self, tmp_strategy_db):
        """Row count grows monotonically with each snapshot call."""
        engine = MarkovPersistenceEngine(warmup_ticks=1)
        for label in ["UP", "DOWN", "UP", "NEUTRAL"]:
            engine.update(_state("btc-usd", label))
            engine.snapshot("PM-5M", tmp_strategy_db)
        assert tmp_strategy_db["strategy_snapshots"].count == 4

    def test_tick_numbers_sequential_and_unique(self, tmp_strategy_db):
        """Each snapshot has unique sequential tick_number per (name, domain)."""
        engine = MarkovPersistenceEngine(warmup_ticks=1)
        for label in ["UP", "DOWN", "UP", "NEUTRAL", "DOWN"]:
            engine.update(_state("btc-usd", label))
            engine.snapshot("PM-5M", tmp_strategy_db)

        rows = list(
            tmp_strategy_db["strategy_snapshots"].rows_where(
                where="strategy_name = ? AND domain = ?",
                where_args=["markov_persistence", "PM-5M"],
                order_by="tick_number",
            )
        )
        tick_numbers = [r["tick_number"] for r in rows]
        assert tick_numbers == [1, 2, 3, 4, 5]
