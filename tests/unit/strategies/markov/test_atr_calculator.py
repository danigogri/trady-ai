"""RED tests for ATRCalculator — these should fail until ATRCalculator is implemented."""

from decimal import Decimal

from trady_ai.strategies.markov.atr_calculator import ATRCalculator


class TestATRCalculatorFirstTick:
    """Task 1.1: first-tick returns None for any market."""

    def test_first_tick_returns_none(self):
        """First update() call returns None (no previous price)."""
        calc = ATRCalculator()
        assert calc.update("btc-usd", Decimal("100.00")) is None

    def test_first_tick_per_market(self):
        """Each new market's first tick returns None."""
        calc = ATRCalculator()
        assert calc.update("btc-usd", Decimal("100.00")) is None
        assert calc.update("eth-usd", Decimal("50.00")) is None

    def test_second_tick_returns_decimal(self):
        """Second update() returns a Decimal τ value."""
        calc = ATRCalculator()
        calc.update("btc-usd", Decimal("100.00"))
        result = calc.update("btc-usd", Decimal("100.50"))
        assert result is not None
        assert isinstance(result, Decimal)


class TestATRCalculatorEmptyBuffer:
    """Task 1.1: threshold() on unknown market returns 0."""

    def test_threshold_unknown_returns_zero(self):
        """threshold() for market with no data → Decimal('0')."""
        calc = ATRCalculator()
        assert calc.threshold("unknown") == Decimal("0")

    def test_threshold_after_clear_returns_zero(self):
        """threshold() after clear() → Decimal('0')."""
        calc = ATRCalculator()
        calc.update("btc-usd", Decimal("100.00"))
        calc.clear("btc-usd")
        assert calc.threshold("btc-usd") == Decimal("0")


class TestATRCalculatorBufferLimit:
    """Task 1.1: buffer_size enforced — oldest prices dropped."""

    def test_buffer_does_not_exceed_limit(self):
        """More updates than buffer_size → oldest prices discarded."""
        calc = ATRCalculator(buffer_size=5)
        for i in range(10):
            calc.update("btc-usd", Decimal(str(100 + i)))
        # After 10 updates with buffer_size=5, we have prices [105..109] (5 items)
        # We can't directly observe the buffer, but we can verify the threshold
        # is computed from the last entries only
        threshold = calc.threshold("btc-usd")
        assert threshold != Decimal("0")

    def test_two_markets_independent_buffers(self):
        """Different markets have independent buffers, both can be at capacity."""
        calc = ATRCalculator(buffer_size=5)
        # Fill btc with 6 updates (overflow)
        for i in range(6):
            calc.update("btc-usd", Decimal(str(100 + i)))
        # Only 1 update for eth
        calc.update("eth-usd", Decimal("50.00"))
        # Both should work
        btc_t = calc.threshold("btc-usd")
        eth_t = calc.update("eth-usd", Decimal("50.50"))
        assert btc_t != Decimal("0")
        assert eth_t is not None


class TestATRCalculatorDeterministic:
    """Task 1.1: same input sequence → same τ (determinism)."""

    def test_deterministic_threshold(self):
        """Same price sequence produces identical τ."""
        prices = [Decimal(str(100 + i)) for i in range(25)]
        calc1 = ATRCalculator(alpha=2.0, period=20)
        calc2 = ATRCalculator(alpha=2.0, period=20)
        for p in prices:
            calc1.update("btc-usd", p)
        for p in prices:
            calc2.update("btc-usd", p)
        assert calc1.threshold("btc-usd") == calc2.threshold("btc-usd")

    def test_different_alpha_produces_scaled_threshold(self):
        """Higher alpha → proportionally higher τ."""
        prices = [Decimal(str(100 + i * 2)) for i in range(25)]
        calc1 = ATRCalculator(alpha=1.0, period=20)
        calc2 = ATRCalculator(alpha=2.0, period=20)
        for p in prices:
            calc1.update("btc-usd", p)
        for p in prices:
            calc2.update("btc-usd", p)
        # τ should scale with alpha
        t1 = calc1.threshold("btc-usd")
        t2 = calc2.threshold("btc-usd")
        assert abs(t2 - 2 * t1) < Decimal("0.0001")

    def test_threshold_stabilizes_with_steady_data(self):
        """With steady small changes, τ stabilizes around expected value."""
        calc = ATRCalculator(alpha=2.0, period=20)
        # Generate 30 ticks with +0.01 incremental changes
        price = Decimal("100.00")
        for _ in range(30):
            calc.update("btc-usd", price)
            price += Decimal("0.01")
        t = calc.threshold("btc-usd")
        # With alpha=2.0 and change=0.01 on ~price=100.30:
        # ATR ≈ 0.01, τ ≈ 2.0 * 0.01 / 100.30 ≈ 0.000199
        assert Decimal("0.0001") < t < Decimal("0.0003")


class TestATRCalculatorClear:
    """Task 1.1: clear() resets market state."""

    def test_clear_resets_market_and_next_tick_is_none(self):
        """After clear(), the next update for that market is treated as first tick → None."""
        calc = ATRCalculator()
        calc.update("btc-usd", Decimal("100.00"))
        calc.update("btc-usd", Decimal("100.50"))
        calc.clear("btc-usd")
        assert calc.update("btc-usd", Decimal("200.00")) is None

    def test_clear_other_market_untouched(self):
        """clear() on one market does not affect another market's state."""
        calc = ATRCalculator()
        calc.update("btc-usd", Decimal("100.00"))
        calc.update("btc-usd", Decimal("100.50"))
        calc.update("eth-usd", Decimal("50.00"))
        calc.clear("btc-usd")
        # eth should still have data
        result = calc.update("eth-usd", Decimal("50.50"))
        assert result is not None
        assert isinstance(result, Decimal)
