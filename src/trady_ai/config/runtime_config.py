from decimal import Decimal

from pydantic import BaseModel, Field


class RuntimeConfig(BaseModel):
    """Execution configuration — independent from infrastructure Settings.

    Controls thresholds, sizing, and costs for the deterministic engine.
    Frozen (immutable) after creation — no runtime mutation allowed.
    """

    threshold_pct: float = Field(default=0.001, gt=0.0, le=1.0)
    warmup_ticks: int = Field(default=50, gt=0)
    position_size: Decimal = Field(default=Decimal("10.00"), gt=Decimal("0"))
    transaction_cost_pct: float = Field(default=0.0, ge=0.0, lt=1.0)
    stop_loss_pct: float = Field(default=0.05, gt=0.0, lt=1.0)

    model_config = {"frozen": True, "arbitrary_types_allowed": True}
