from pathlib import Path

import pytest
from pydantic import ValidationError

from trady_ai import __version__
from trady_ai.config.settings import Settings, get_settings


def test_version_exists():
    """Verifica que __version__ está definido y coincide con pyproject.toml."""
    assert __version__ == "0.1.0"


def test_settings_defaults():
    """Verifica que los valores por defecto son correctos."""
    settings = Settings()
    assert settings.dry_run is True
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.db_path == Path("data/trady_ai.db")
    assert settings.secrets_api_key == ""


def test_settings_from_env(monkeypatch):
    """Verifica override de settings vía variables de entorno."""
    monkeypatch.setenv("TRADY_AI_DRY_RUN", "false")
    monkeypatch.setenv("TRADY_AI_ENVIRONMENT", "production")
    monkeypatch.setenv("TRADY_AI_LOG_LEVEL", "DEBUG")

    settings = Settings()
    assert settings.dry_run is False
    assert settings.environment == "production"
    assert settings.log_level == "DEBUG"


def test_settings_env_validation():
    """Verifica que environment inválido lanza ValidationError."""
    with pytest.raises(ValidationError):
        Settings(environment="invalid")


def test_get_settings_singleton():
    """Verifica que get_settings retorna la misma instancia (singleton)."""
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b


def test_settings_frozen():
    """Verifica que Settings es inmutable post-creación."""
    settings = Settings()
    with pytest.raises((TypeError, ValidationError)):
        settings.dry_run = False


# ── Binance settings (REQ-BC-001 through REQ-BC-005) ─────────────────────────


def test_binance_settings_defaults():
    """REQ-BC-001/002: Default WS/REST URLs are Binance testnet."""
    settings = Settings()
    assert settings.binance_ws_url == "wss://testnet.binance.vision/ws"
    assert settings.binance_rest_url == "https://testnet.binance.vision"


def test_binance_settings_override(monkeypatch):
    """REQ-BC-001/002: Explicit env vars override defaults."""
    monkeypatch.setenv("TRADY_AI_BINANCE_WS_URL", "wss://stream.binance.com:9443/ws")
    monkeypatch.setenv("TRADY_AI_BINANCE_REST_URL", "https://api.binance.com")
    settings = Settings()
    assert settings.binance_ws_url == "wss://stream.binance.com:9443/ws"
    assert settings.binance_rest_url == "https://api.binance.com"


def test_binance_active_symbols_default_empty():
    """REQ-BC-003: active_symbols defaults to empty string."""
    settings = Settings()
    assert settings.active_symbols == ""


def test_binance_get_active_symbols_multiple(monkeypatch):
    """REQ-BC-003: Comma-separated symbols parsed correctly."""
    monkeypatch.setenv("TRADY_AI_ACTIVE_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT")
    settings = Settings()
    result = settings.get_active_symbols()
    assert result == ["BTCUSDT", "ETHUSDT", "BNBUSDT"]


def test_binance_get_active_symbols_whitespace(monkeypatch):
    """REQ-BC-003: Whitespace around symbols is stripped."""
    monkeypatch.setenv("TRADY_AI_ACTIVE_SYMBOLS", " BTCUSDT , ETHUSDT ")
    settings = Settings()
    result = settings.get_active_symbols()
    assert result == ["BTCUSDT", "ETHUSDT"]


def test_binance_get_active_symbols_empty():
    """REQ-BC-003: No TRADY_AI_ACTIVE_SYMBOLS → empty list."""
    settings = Settings()
    assert settings.get_active_symbols() == []


def test_binance_get_active_symbols_empty_after_set(monkeypatch):
    """REQ-BC-003: Empty string after set → empty list."""
    monkeypatch.setenv("TRADY_AI_ACTIVE_SYMBOLS", "")
    settings = Settings()
    assert settings.get_active_symbols() == []


def test_binance_settings_frozen(monkeypatch):
    """REQ-BC-005: Binance settings are immutable."""
    settings = Settings()
    with pytest.raises((TypeError, ValidationError)):
        settings.binance_ws_url = "changed"
    with pytest.raises((TypeError, ValidationError)):
        settings.binance_rest_url = "changed"
    with pytest.raises((TypeError, ValidationError)):
        settings.active_symbols = "changed"


# ── Bybit settings (REQ-BYC-001 through REQ-BYC-005) ─────────────────────────


def test_bybit_settings_defaults():
    """REQ-BYC-001/002: Default WS/REST URLs are Bybit testnet."""
    settings = Settings()
    assert settings.bybit_ws_url == "wss://stream-testnet.bybit.com/v5/public/spot"
    assert settings.bybit_rest_url == "https://api-testnet.bybit.com"


def test_bybit_settings_explicit_override(monkeypatch):
    """REQ-BYC-001/002: Explicit env vars override defaults."""
    monkeypatch.setenv("TRADY_AI_BYBIT_WS_URL", "wss://stream.bybit.com/v5/public/spot")
    monkeypatch.setenv("TRADY_AI_BYBIT_REST_URL", "https://api.bybit.com")
    settings = Settings()
    assert settings.bybit_ws_url == "wss://stream.bybit.com/v5/public/spot"
    assert settings.bybit_rest_url == "https://api.bybit.com"


def test_bybit_settings_immutable():
    """REQ-BYC-005: Bybit settings are immutable."""
    settings = Settings()
    with pytest.raises((TypeError, ValidationError)):
        settings.bybit_ws_url = "changed"
    with pytest.raises((TypeError, ValidationError)):
        settings.bybit_rest_url = "changed"
