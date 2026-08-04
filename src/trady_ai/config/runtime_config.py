from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    """Execution configuration — independent from infrastructure Settings.

    Controls thresholds, sizing, and costs for the deterministic engine.
    Frozen (immutable) after creation — no runtime mutation allowed.
    """

    threshold_pct: float = Field(default=0.001, gt=0.0, le=1.0)
    alpha: float = Field(default=0.0, ge=0.0, le=10.0)
    atr_period: int = Field(default=20, gt=1, le=200)
    warmup_ticks: int = Field(default=50, gt=0)
    position_size: Decimal = Field(default=Decimal("10.00"), gt=Decimal("0"))
    transaction_cost_pct: float = Field(default=0.0, ge=0.0, lt=1.0)
    stop_loss_pct: float = Field(default=0.05, gt=0.0, lt=1.0)

    # Execution mode
    execution_mode: Literal["dry_run", "live"] = "dry_run"

    # Order defaults
    default_order_type: Literal["GTC"] = "GTC"

    model_config = {"frozen": True, "arbitrary_types_allowed": True}
