from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from trady_ai.core.models import MarketInput
from trady_ai.core.normalization import normalize


class TestNormalizationTimestamps:
    def test_naive_timestamp_gets_utc(self):
        """naive timestamp → UTC (tzinfo set to UTC)."""
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            market_id="btc-usd",
            price=Decimal("100.00"),
            volume=Decimal("1000"),
        )
        result = normalize(inp)
        assert result.timestamp.tzinfo is not None
        assert result.timestamp.utcoffset() == UTC.utcoffset(None)
        assert result.timestamp.hour == 12  # same hour since assumed UTC

    def test_timestamp_with_tz_converted_to_utc(self):
        """Timestamp with EST → converted to UTC (hour changes)."""
        est_tz = timezone(timedelta(hours=-5))
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=est_tz),
            market_id="btc-usd",
            price=Decimal("100.00"),
            volume=Decimal("1000"),
        )
        result = normalize(inp)
        assert result.timestamp.tzinfo is not None
        # EST 12:00 = UTC 17:00
        assert result.timestamp.hour == 17

    def test_utc_timestamp_unchanged(self):
        """Timestamp already in UTC → unchanged."""
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            market_id="btc-usd",
            price=Decimal("100.00"),
            volume=Decimal("1000"),
        )
        result = normalize(inp)
        assert result.timestamp.hour == 12
        assert result.timestamp.tzinfo is UTC or result.timestamp.utcoffset() == UTC.utcoffset(None)


class TestNormalizationDecimals:
    def test_price_and_volume_unchanged(self):
        """Price and volume remain as Decimal, unchanged."""
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            market_id="btc-usd",
            price=Decimal("100.50"),
            volume=Decimal("200.75"),
        )
        result = normalize(inp)
        assert result.price == Decimal("100.50")
        assert result.volume == Decimal("200.75")
        assert isinstance(result.price, Decimal)
        assert isinstance(result.volume, Decimal)


class TestNormalizationMarketId:
    def test_market_id_stripped_and_lowered(self):
        """market_id with whitespace and uppercase → stripped + lowercase."""
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            market_id="  BTC-USD  ",
            price=Decimal("100.00"),
            volume=Decimal("1000"),
        )
        result = normalize(inp)
        assert result.market_id == "btc-usd"

    def test_market_id_already_lowercase(self):
        """market_id already lowercase → unchanged."""
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            market_id="btc-usd",
            price=Decimal("100.00"),
            volume=Decimal("1000"),
        )
        result = normalize(inp)
        assert result.market_id == "btc-usd"


class TestNormalizationIdempotent:
    def test_normalize_twice_same_result(self):
        """Calling normalize() twice produces identical output."""
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            market_id="  BTC-USD  ",
            price=Decimal("100.00"),
            volume=Decimal("1000"),
        )
        first = normalize(inp)
        second = normalize(first)
        assert first.timestamp == second.timestamp
        assert first.market_id == second.market_id
        assert first.price == second.price
        assert first.volume == second.volume
        assert first.source == second.source

    def test_normalize_of_normalized_source_unchanged(self):
        """Second normalize does not modify already-correct fields."""
        inp = MarketInput(
            timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            market_id="btc-usd",
            price=Decimal("100.00"),
            volume=Decimal("1000"),
        )
        first = normalize(inp)
        second = normalize(first)
        assert first.market_id == second.market_id
        assert first.timestamp == second.timestamp
