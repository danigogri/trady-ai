import pytest
from pydantic import ValidationError

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.config.settings import Settings


class TestSettingsPolymarket:
    def test_settings_polymarket_defaults(self):
        """Settings() has correct Polymarket default values."""
        settings = Settings()
        assert settings.polymarket_api_key == ""
        assert settings.polymarket_secret == ""
        assert settings.polymarket_passphrase == ""
        assert settings.polymarket_ws_url == "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        assert settings.polymarket_rest_url == "https://clob.polymarket.com"
        assert settings.active_markets == ""

    def test_settings_polymarket_from_env(self, monkeypatch):
        """Settings() picks up Polymarket values from env vars."""
        monkeypatch.setenv("TRADY_AI_POLYMARKET_API_KEY", "test-key")
        monkeypatch.setenv("TRADY_AI_ACTIVE_MARKETS", "0xabc,0xdef")

        settings = Settings()
        assert settings.polymarket_api_key == "test-key"
        assert settings.active_markets == "0xabc,0xdef"

    def test_get_active_market_ids_parses_comma_separated(self):
        """get_active_market_ids splits and strips comma-separated IDs."""
        settings = Settings(active_markets="0xabc, 0xdef, 0xghi")
        ids = settings.get_active_market_ids()
        assert ids == ["0xabc", "0xdef", "0xghi"]

    def test_get_active_market_ids_handles_empty_string(self):
        """get_active_market_ids returns [] when active_markets is empty."""
        settings = Settings()
        assert settings.get_active_market_ids() == []

    def test_get_active_market_ids_handles_single_market(self):
        """get_active_market_ids handles a single market ID."""
        settings = Settings(active_markets="0xabc")
        assert settings.get_active_market_ids() == ["0xabc"]

    def test_get_active_market_ids_filters_empty_segments(self):
        """get_active_market_ids filters out empty segments from trailing commas."""
        settings = Settings(active_markets="0xabc,,0xdef,")
        ids = settings.get_active_market_ids()
        assert ids == ["0xabc", "0xdef"]


class TestRuntimeConfigPolymarket:
    def test_execution_mode_default_is_dry_run(self):
        """RuntimeConfig() defaults to dry_run execution_mode."""
        config = RuntimeConfig()
        assert config.execution_mode == "dry_run"

    def test_execution_mode_can_be_live(self):
        """execution_mode can be set to 'live'."""
        config = RuntimeConfig(execution_mode="live")
        assert config.execution_mode == "live"

    def test_default_order_type_is_gtc(self):
        """RuntimeConfig() defaults to GTC order type."""
        config = RuntimeConfig()
        assert config.default_order_type == "GTC"

    def test_invalid_execution_mode_raises(self):
        """Invalid execution_mode value raises ValidationError."""
        with pytest.raises(ValidationError):
            RuntimeConfig(execution_mode="paper")

    def test_invalid_order_type_raises(self):
        """Invalid default_order_type value raises ValidationError."""
        with pytest.raises(ValidationError):
            RuntimeConfig(default_order_type="IOC")

    def test_runtime_config_still_frozen(self):
        """RuntimeConfig remains immutable with new fields."""
        config = RuntimeConfig()
        with pytest.raises((ValidationError, TypeError)):
            config.execution_mode = "live"  # type: ignore[misc]
