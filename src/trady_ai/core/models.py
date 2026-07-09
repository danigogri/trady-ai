import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

NAMESPACE = uuid.NAMESPACE_URL


class MarketInput(BaseModel):
    """Raw input from CSV — a single market data tick."""

    timestamp: datetime
    market_id: str
    price: Decimal = Field(gt=Decimal("0"))
    volume: Decimal = Field(ge=Decimal("0"))
    source: str = "csv"


class MarketState(BaseModel):
    """Classified state of a market at a point in time."""

    market_id: str
    timestamp: datetime
    price: Decimal = Field(gt=Decimal("0"))
    volume: Decimal = Field(ge=Decimal("0"))
    state: Literal["UP", "DOWN", "NEUTRAL"]
    previous_state: Literal["UP", "DOWN", "NEUTRAL"] | None = None
    source: str = "state_tracker"


class Signal(BaseModel):
    """Output of a strategy — a trading signal with deterministic UUID5."""

    id: uuid.UUID
    timestamp: datetime
    market_id: str
    direction: Literal["LONG", "SHORT", "NEUTRAL"]
    confidence: float = Field(ge=0.0, le=1.0)
    strategy_name: str
    metadata: dict[str, Any] = {}

    def __init__(self, **data: Any) -> None:
        if "id" not in data:
            data["id"] = uuid.uuid5(
                NAMESPACE,
                f"{data.get('strategy_name', '')}:{data.get('market_id', '')}:"
                f"{data.get('timestamp', datetime.min).isoformat()}",
            )
        super().__init__(**data)


class Position(BaseModel):
    """An open or closed position with deterministic UUID5."""

    id: uuid.UUID
    market_id: str
    direction: Literal["LONG", "SHORT"]
    entry_price: Decimal = Field(gt=Decimal("0"))
    current_price: Decimal = Field(gt=Decimal("0"))
    size: Decimal = Field(gt=Decimal("0"))
    pnl: Decimal | None = None
    status: Literal["OPEN", "CLOSED"] = "OPEN"
    signal_id: uuid.UUID

    def __init__(self, **data: Any) -> None:
        if "id" not in data:
            market_id = data.get("market_id", "")
            signal_id = data.get("signal_id", uuid.UUID(int=0))
            data["id"] = uuid.uuid5(
                NAMESPACE,
                f"position:{market_id}:{signal_id}",
            )
        super().__init__(**data)


class Trade(BaseModel):
    """Execution record of a trade with deterministic UUID5."""

    id: uuid.UUID
    signal_id: uuid.UUID
    position_id: uuid.UUID
    action: Literal["OPEN", "CLOSE"]
    price: Decimal = Field(gt=Decimal("0"))
    size: Decimal = Field(gt=Decimal("0"))
    timestamp: datetime
    dry_run: bool = True

    def __init__(self, **data: Any) -> None:
        if "id" not in data:
            position_id = data.get("position_id", uuid.UUID(int=0))
            action = data.get("action", "")
            timestamp = data.get("timestamp", datetime.min)
            data["id"] = uuid.uuid5(
                NAMESPACE,
                f"trade:{position_id}:{action}:{timestamp.isoformat()}",
            )
        super().__init__(**data)


class ExecutionDecision(BaseModel):
    """Decision made by the engine after evaluating a signal + risk checks."""

    signal_id: uuid.UUID
    action: Literal["OPEN_LONG", "OPEN_SHORT", "CLOSE", "HOLD", "REJECT"]
    reason: str
    risk_check_passed: bool
    risk_check_details: dict[str, Any] = {}
    timestamp: datetime
