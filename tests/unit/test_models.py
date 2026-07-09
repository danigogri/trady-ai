import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trady_ai.core.models import (
    NAMESPACE,
    ExecutionDecision,
    MarketInput,
    MarketState,
    Position,
    Signal,
    Trade,
)


class TestSignal:
    def test_uuid_deterministic(self):
        """Same input produces the same UUID5."""
        ts = datetime(2024, 1, 1, 12, 0, 0)
        s1 = Signal(
            timestamp=ts,
            market_id="btc-usd",
            direction="LONG",
            confidence=0.8,
            strategy_name="markov_persistence",
        )
        s2 = Signal(
            timestamp=ts,
            market_id="btc-usd",
            direction="LONG",
            confidence=0.8,
            strategy_name="markov_persistence",
        )
        assert s1.id == s2.id
        expected = uuid.uuid5(NAMESPACE, f"markov_persistence:btc-usd:{ts.isoformat()}")
        assert s1.id == expected

    def test_different_input_different_uuid(self):
        """Different inputs produce different UUIDs."""
        ts1 = datetime(2024, 1, 1, 12, 0, 0)
        ts2 = datetime(2024, 1, 2, 12, 0, 0)
        s1 = Signal(timestamp=ts1, market_id="btc-usd", direction="LONG", confidence=0.8, strategy_name="strat_a")
        s2 = Signal(timestamp=ts2, market_id="btc-usd", direction="LONG", confidence=0.8, strategy_name="strat_a")
        assert s1.id != s2.id

    def test_confidence_bounds(self):
        """confidence=1.5 is out of range → ValidationError."""
        with pytest.raises(ValidationError):
            Signal(
                timestamp=datetime(2024, 1, 1),
                market_id="btc-usd",
                direction="LONG",
                confidence=1.5,
                strategy_name="test",
            )

    def test_confidence_lower_bound(self):
        """confidence=0.0 is valid."""
        s = Signal(
            timestamp=datetime(2024, 1, 1),
            market_id="btc-usd",
            direction="NEUTRAL",
            confidence=0.0,
            strategy_name="test",
        )
        assert s.confidence == 0.0

    def test_invalid_direction(self):
        """Invalid direction literal raises ValidationError."""
        with pytest.raises(ValidationError):
            Signal(
                timestamp=datetime(2024, 1, 1),
                market_id="btc-usd",
                direction="INVALID",  # type: ignore
                confidence=0.5,
                strategy_name="test",
            )


class TestPosition:
    def test_uuid_deterministic(self):
        """Same input produces the same UUID5."""
        signal_id = uuid.uuid5(NAMESPACE, "test:btc-usd:2024-01-01T12:00:00")
        p1 = Position(
            market_id="btc-usd",
            direction="LONG",
            entry_price=Decimal("100.00"),
            current_price=Decimal("100.00"),
            size=Decimal("10.00"),
            signal_id=signal_id,
        )
        p2 = Position(
            market_id="btc-usd",
            direction="LONG",
            entry_price=Decimal("100.00"),
            current_price=Decimal("100.00"),
            size=Decimal("10.00"),
            signal_id=signal_id,
        )
        assert p1.id == p2.id
        expected = uuid.uuid5(NAMESPACE, f"position:btc-usd:{signal_id}")
        assert p1.id == expected


class TestTrade:
    def test_uuid_deterministic(self):
        """Same input produces the same UUID5."""
        pos_id = uuid.uuid5(NAMESPACE, "position:btc-usd:some-signal")
        ts = datetime(2024, 1, 1, 12, 0, 0)
        t1 = Trade(
            signal_id=uuid.UUID(int=1),
            position_id=pos_id,
            action="OPEN",
            price=Decimal("100.00"),
            size=Decimal("10.00"),
            timestamp=ts,
        )
        t2 = Trade(
            signal_id=uuid.UUID(int=1),
            position_id=pos_id,
            action="OPEN",
            price=Decimal("100.00"),
            size=Decimal("10.00"),
            timestamp=ts,
        )
        assert t1.id == t2.id
        expected = uuid.uuid5(NAMESPACE, f"trade:{pos_id}:OPEN:{ts.isoformat()}")
        assert t1.id == expected


class TestMarketInput:
    def test_price_positive(self):
        """price must be greater than 0."""
        with pytest.raises(ValidationError):
            MarketInput(
                timestamp=datetime(2024, 1, 1),
                market_id="btc-usd",
                price=Decimal("-1"),
                volume=Decimal("100"),
            )

    def test_price_zero(self):
        """price=0 is invalid (gt=0)."""
        with pytest.raises(ValidationError):
            MarketInput(
                timestamp=datetime(2024, 1, 1),
                market_id="btc-usd",
                price=Decimal("0"),
                volume=Decimal("100"),
            )

    def test_valid_construction(self):
        """Valid MarketInput constructs without error."""
        mi = MarketInput(
            timestamp=datetime(2024, 1, 1),
            market_id="btc-usd",
            price=Decimal("50000.00"),
            volume=Decimal("100.50"),
        )
        assert mi.source == "csv"
        assert mi.price == Decimal("50000.00")

    def test_volume_negative(self):
        """volume must be >= 0."""
        with pytest.raises(ValidationError):
            MarketInput(
                timestamp=datetime(2024, 1, 1),
                market_id="btc-usd",
                price=Decimal("100"),
                volume=Decimal("-1"),
            )


class TestMarketState:
    def test_default_source(self):
        """MarketState default source is 'state_tracker'."""
        ms = MarketState(
            market_id="btc-usd",
            timestamp=datetime(2024, 1, 1),
            price=Decimal("100.00"),
            volume=Decimal("1000"),
            state="UP",
        )
        assert ms.source == "state_tracker"
        assert ms.previous_state is None

    def test_previous_state(self):
        """previous_state can be set."""
        ms = MarketState(
            market_id="btc-usd",
            timestamp=datetime(2024, 1, 1),
            price=Decimal("100.00"),
            volume=Decimal("1000"),
            state="DOWN",
            previous_state="UP",
        )
        assert ms.previous_state == "UP"


class TestExecutionDecision:
    def test_all_actions(self):
        """Each valid action constructs successfully."""
        ts = datetime(2024, 1, 1)
        for action in ("OPEN_LONG", "OPEN_SHORT", "CLOSE", "HOLD", "REJECT"):
            d = ExecutionDecision(
                signal_id=uuid.UUID(int=1),
                action=action,
                reason="test",
                risk_check_passed=True,
                timestamp=ts,
            )
            assert d.action == action

    def test_invalid_action(self):
        """Invalid action literal raises ValidationError."""
        with pytest.raises(ValidationError):
            ExecutionDecision(
                signal_id=uuid.UUID(int=1),
                action="INVALID",  # type: ignore
                reason="test",
                risk_check_passed=True,
                timestamp=datetime(2024, 1, 1),
            )
