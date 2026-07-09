from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from trady_ai.config.runtime_config import RuntimeConfig


class Settings(BaseSettings):
    """Configuración validada e inmutable del sistema.

    Namespace de env vars: TRADY_AI_*
    Carga desde .env (si existe) + environment variables.
    """

    environment: Literal["development", "demo", "production"] = "development"
    dry_run: bool = True  # RFC-000: MUST default True
    log_level: str = "INFO"
    db_path: Path = Path("data/trady_ai.db")
    secrets_api_key: str = ""  # Placeholder hasta Fase 2

    # Runtime config defaults (can be overridden by CLI options)
    default_threshold_pct: float = 0.001
    default_warmup_ticks: int = 50
    default_position_size: str = "10.00"
    default_transaction_cost_pct: float = 0.0
    default_stop_loss_pct: float = 0.05

    def get_runtime_config(self) -> "RuntimeConfig":
        """Build a RuntimeConfig from the Settings defaults."""
        from decimal import Decimal

        from trady_ai.config.runtime_config import RuntimeConfig

        return RuntimeConfig(
            threshold_pct=self.default_threshold_pct,
            warmup_ticks=self.default_warmup_ticks,
            position_size=Decimal(self.default_position_size),
            transaction_cost_pct=self.default_transaction_cost_pct,
            stop_loss_pct=self.default_stop_loss_pct,
        )

    model_config = SettingsConfigDict(
        env_prefix="TRADY_AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Seguridad: ignora vars inesperadas
        frozen=True,  # Inmutable post-creación
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna instancia singleton de Settings.

    lru_cache garantiza una única construcción.
    La primera llamada parsea .env + env vars y valida tipos.
    Llamadas subsecuentes retornan la misma instancia (inmutable).
    """
    return Settings()
