from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trady_ai.core.ingestion import read_csv


def _csv_str(rows: list[str]) -> str:
    """Build a minimal CSV string with header + rows."""
    header = "timestamp,market_id,price,volume"
    return header + "\n" + "\n".join(rows)


def _write_csv(tmp_path: Path, content: str, filename: str = "test.csv") -> Path:
    path = tmp_path / filename
    path.write_text(content)
    return path


class TestIngestionValid:
    def test_valid_csv_returns_market_inputs(self, tmp_path):
        """Well-formed CSV → list of MarketInput with correct values."""
        content = _csv_str([
            "2024-01-01T12:00:00,BTC-USD,50000.00,100.50",
            "2024-01-01T12:01:00,BTC-USD,50100.00,150.25",
        ])
        path = _write_csv(tmp_path, content)

        results = read_csv(path)
        assert len(results) == 2

        assert results[0].market_id == "btc-usd"
        assert results[0].price == Decimal("50000.00")
        assert results[0].volume == Decimal("100.50")
        assert results[0].timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert results[0].source == "csv"

        assert results[1].market_id == "btc-usd"
        assert results[1].price == Decimal("50100.00")
        assert results[1].volume == Decimal("150.25")

    def test_multiple_markets(self, tmp_path):
        """CSV with multiple market IDs is parsed correctly."""
        content = _csv_str([
            "2024-01-01T12:00:00,BTC-USD,50000.00,100.00",
            "2024-01-01T12:00:00,ETH-USD,3000.00,500.00",
        ])
        path = _write_csv(tmp_path, content)

        results = read_csv(path)
        assert results[0].market_id == "btc-usd"
        assert results[1].market_id == "eth-usd"


class TestIngestionInvalidColumns:
    def test_missing_column_raises_value_error(self, tmp_path):
        """CSV missing 'volume' column → ValueError."""
        content = "timestamp,market_id,price\n2024-01-01T12:00:00,BTC-USD,50000.00\n"
        path = _write_csv(tmp_path, content)

        with pytest.raises(ValueError, match="missing required columns"):
            read_csv(path)

    def test_missing_multiple_columns(self, tmp_path):
        """CSV missing multiple columns → ValueError."""
        content = "timestamp,market_id\n2024-01-01T12:00:00,BTC-USD\n"
        path = _write_csv(tmp_path, content)

        with pytest.raises(ValueError, match="missing required columns"):
            read_csv(path)


class TestIngestionMissingFile:
    def test_nonexistent_file_raises_file_not_found(self):
        """Non-existent CSV path → FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            read_csv(Path("/nonexistent/path.csv"))


class TestIngestionEmptyCsv:
    def test_empty_csv_raises_value_error(self, tmp_path):
        """CSV with only headers → ValueError."""
        content = "timestamp,market_id,price,volume\n"
        path = _write_csv(tmp_path, content)

        with pytest.raises(ValueError, match="no data rows"):
            read_csv(path)


class TestIngestionInvalidTimestamp:
    def test_bad_timestamp_raises_value_error(self, tmp_path):
        """Invalid timestamp format → ValueError with context."""
        content = _csv_str([
            "not-a-timestamp,BTC-USD,50000.00,100.00",
        ])
        path = _write_csv(tmp_path, content)

        with pytest.raises(ValueError, match="Invalid timestamp at row 1"):
            read_csv(path)

    def test_empty_timestamp_raises_value_error(self, tmp_path):
        """Empty timestamp → ValueError."""
        content = _csv_str([
            ",BTC-USD,50000.00,100.00",
        ])
        path = _write_csv(tmp_path, content)

        with pytest.raises(ValueError, match="Invalid timestamp at row 1"):
            read_csv(path)


class TestIngestionInvalidPrice:
    def test_non_numeric_price_raises_value_error(self, tmp_path):
        """Non-numeric price → ValueError with context."""
        content = _csv_str([
            "2024-01-01T12:00:00,BTC-USD,abc,100.00",
        ])
        path = _write_csv(tmp_path, content)

        with pytest.raises(ValueError, match="Invalid price at row 1"):
            read_csv(path)


class TestIngestionOrderPreserved:
    def test_row_order_is_preserved(self, tmp_path):
        """CSV row order = list order."""
        content = _csv_str([
            "2024-01-01T12:00:00,BTC-USD,100.00,10.00",
            "2024-01-01T12:01:00,BTC-USD,101.00,11.00",
            "2024-01-01T12:02:00,BTC-USD,102.00,12.00",
        ])
        path = _write_csv(tmp_path, content)

        results = read_csv(path)
        assert len(results) == 3
        assert results[0].price == Decimal("100.00")
        assert results[1].price == Decimal("101.00")
        assert results[2].price == Decimal("102.00")
