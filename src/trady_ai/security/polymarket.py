"""Polymarket execution-mode secret validation.

Validates Polymarket credentials conditionally based on execution_mode:
- dry_run: no validation (secrets may be empty)
- live: ALL secrets MUST be non-empty

This module is SEPARATE from security/secrets.py (placeholder validation)
per Option C decision — preserves the Phase 1 contract and its responsibilities.
"""

from typing import Literal

from trady_ai.config.settings import Settings


def validate_execution_secrets(
    settings: Settings,
    execution_mode: Literal["dry_run", "live"],
) -> None:
    """Validate Polymarket credentials based on execution mode.

    Args:
        settings: Settings instance with polymarket_* fields.
        execution_mode: 'dry_run' or 'live'.

    Raises:
        ValueError: If execution_mode == 'live' and any required field is empty.
    """
    if execution_mode == "dry_run":
        return

    missing = []
    if not settings.polymarket_api_key:
        missing.append("polymarket_api_key")
    if not settings.polymarket_secret:
        missing.append("polymarket_secret")
    if not settings.polymarket_passphrase:
        missing.append("polymarket_passphrase")
    if not settings.active_markets:
        missing.append("active_markets")

    if missing:
        raise ValueError(
            f"Live execution requires: {', '.join(missing)}. "
            f"Set via TRADY_AI_{{NAME}} env vars or .env file."
        )
