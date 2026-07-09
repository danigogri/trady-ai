import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from trady_ai.core.models import MarketInput

REQUIRED_COLUMNS = {"timestamp", "market_id", "price", "volume"}


def read_csv(path: Path) -> list[MarketInput]:
    """Read a CSV file and return a list of validated MarketInputs.

    Column requirements (case-sensitive): timestamp, market_id, price, volume.
    Fail-fast: any validation error raises an explicit exception with context.

    Args:
        path: Path to the CSV file.

    Returns:
        List of MarketInput in CSV row order.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If columns are missing, data is empty, or a field is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open(newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"CSV file is empty or has no headers: {path}")

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"CSV missing required columns: {missing}. "
                f"Expected: {REQUIRED_COLUMNS}. "
                f"Got: {set(reader.fieldnames)}"
            )

        rows: list[MarketInput] = []
        for i, raw in enumerate(reader, start=1):
            try:
                timestamp = datetime.fromisoformat(raw["timestamp"])
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Invalid timestamp at row {i}: {raw['timestamp']!r}"
                ) from exc

            try:
                price = Decimal(raw["price"])
            except Exception as exc:
                raise ValueError(
                    f"Invalid price at row {i}: {raw['price']!r}"
                ) from exc

            try:
                volume = Decimal(raw["volume"])
            except Exception as exc:
                raise ValueError(
                    f"Invalid volume at row {i}: {raw['volume']!r}"
                ) from exc

            market_id = raw["market_id"].strip().lower()

            rows.append(
                MarketInput(
                    timestamp=timestamp,
                    market_id=market_id,
                    price=price,
                    volume=volume,
                    source="csv",
                )
            )

    if not rows:
        raise ValueError("CSV file contains no data rows")

    return rows
