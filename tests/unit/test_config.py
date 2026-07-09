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
