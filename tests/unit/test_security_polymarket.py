"""Tests for validate_execution_secrets (BL-011).

Tests the 3 scenarios from spec Module 9:
1. dry_run allows empty secrets (no-op)
2. live with missing secrets raises ValueError
3. live with all secrets set passes
"""

from trady_ai.config.settings import Settings
from trady_ai.security.polymarket import validate_execution_secrets


def test_validate_execution_secrets_dry_run_allows_empty():
    """dry_run mode: no validation even when all polymarket secrets are empty."""
    settings = Settings(
        polymarket_api_key="",
        polymarket_secret="",
        polymarket_passphrase="",
        active_markets="",
    )
    validate_execution_secrets(settings, "dry_run")  # no raise


def test_validate_execution_secrets_live_missing_raises():
    """live mode: raises ValueError when secrets are empty."""
    settings = Settings(
        polymarket_api_key="",
        polymarket_secret="",
        polymarket_passphrase="",
        active_markets="",
    )
    try:
        validate_execution_secrets(settings, "live")
        raise AssertionError("Expected ValueError was not raised")
    except ValueError as e:
        assert "polymarket_api_key" in str(e)
        assert "polymarket_secret" in str(e)
        assert "polymarket_passphrase" in str(e)
        assert "active_markets" in str(e)


def test_validate_execution_secrets_live_complete_passes():
    """live mode: no error when all secrets present and active_markets configured."""
    settings = Settings(
        polymarket_api_key="test-key",
        polymarket_secret="test-secret",
        polymarket_passphrase="test-pass",
        active_markets="0xabc",
    )
    validate_execution_secrets(settings, "live")  # no raise
