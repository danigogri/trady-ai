from decimal import Decimal

import pytest
from pydantic import ValidationError

from trady_ai.config.runtime_config import RuntimeConfig


class TestRuntimeConfigDefaults:
    def test_defaults(self):
        """RuntimeConfig() creates with expected default values."""
        config = RuntimeConfig()
        assert config.threshold_pct == 0.001
        assert config.warmup_ticks == 50
        assert config.position_size == Decimal("10.00")
        assert config.transaction_cost_pct == 0.0
        assert config.stop_loss_pct == 0.05

    def test_custom_values(self):
        """RuntimeConfig can be constructed with custom values."""
        config = RuntimeConfig(
            threshold_pct=0.01,
            warmup_ticks=100,
            position_size=Decimal("100.00"),
            transaction_cost_pct=0.001,
            stop_loss_pct=0.1,
        )
        assert config.threshold_pct == 0.01
        assert config.warmup_ticks == 100
        assert config.position_size == Decimal("100.00")
        assert config.transaction_cost_pct == 0.001
        assert config.stop_loss_pct == 0.1

    def test_frozen(self):
        """RuntimeConfig is immutable — mutation raises ValidationError."""
        config = RuntimeConfig()
        with pytest.raises(ValidationError):
            config.threshold_pct = 0.5

    def test_invalid_threshold(self):
        """threshold_pct=0 is invalid (must be > 0)."""
        with pytest.raises(ValidationError):
            RuntimeConfig(threshold_pct=0.0)

    def test_invalid_warmup(self):
        """warmup_ticks=0 is invalid (must be > 0)."""
        with pytest.raises(ValidationError):
            RuntimeConfig(warmup_ticks=0)

    def test_invalid_cost(self):
        """transaction_cost_pct=1.0 is invalid (must be < 1)."""
        with pytest.raises(ValidationError):
            RuntimeConfig(transaction_cost_pct=1.0)

    def test_invalid_stop_loss(self):
        """stop_loss_pct=0.0 is invalid (must be > 0)."""
        with pytest.raises(ValidationError):
            RuntimeConfig(stop_loss_pct=0.0)
