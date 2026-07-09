from datetime import UTC

from trady_ai.core.models import MarketInput


def normalize(market_input: MarketInput) -> MarketInput:
    """Normalize a MarketInput deterministically.

    - Timestamp → UTC (assume UTC if naive, convert if it has tzinfo)
    - market_id → strip + lowercase
    - source → default "csv" if empty
    - Idempotent: calling normalize() twice produces the same result.
    """
    ts = market_input.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    else:
        ts = ts.astimezone(UTC)

    mid = market_input.market_id.strip().lower()
    source = market_input.source or "csv"

    return MarketInput(
        timestamp=ts,
        market_id=mid,
        price=market_input.price,
        volume=market_input.volume,
        source=source,
    )
