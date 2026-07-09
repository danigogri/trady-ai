from decimal import Decimal

from trady_ai.config.settings import Settings, get_settings


def test_get_runtime_config_defaults():
    """get_runtime_config() returns RuntimeConfig with Settings defaults."""
    get_settings.cache_clear()
    settings = Settings()
    config = settings.get_runtime_config()

    assert config.threshold_pct == 0.001
    assert config.warmup_ticks == 50
    assert config.position_size == Decimal("10.00")
    assert config.transaction_cost_pct == 0.0
    assert config.stop_loss_pct == 0.05


def test_get_runtime_config_override():
    """Overriding Settings defaults → RuntimeConfig reflects the change."""
    get_settings.cache_clear()
    settings = Settings(default_threshold_pct=0.005, default_warmup_ticks=100)
    config = settings.get_runtime_config()

    assert config.threshold_pct == 0.005
    assert config.warmup_ticks == 100
    # These should still be defaults
    assert config.position_size == Decimal("10.00")
    assert config.stop_loss_pct == 0.05
