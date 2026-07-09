import os

import pytest

from trady_ai.config.settings import Settings
from trady_ai.security.secrets import (
    InsecurePermissionsError,
    SecretValidationError,
    check_file_permissions,
    validate_secrets,
)


def test_validate_secrets_rejects_placeholder():
    """Verifica que 'changeme' es rechazado."""
    settings = Settings(secrets_api_key="changeme")
    with pytest.raises(SecretValidationError):
        validate_secrets(settings)


def test_validate_secrets_rejects_empty():
    """Verifica que string vacío es rechazado."""
    settings = Settings(secrets_api_key="")
    with pytest.raises(SecretValidationError):
        validate_secrets(settings)


def test_validate_secrets_accepts_valid():
    """Verifica que un API key válido es aceptado."""
    settings = Settings(secrets_api_key="sk-live-abc123")
    validate_secrets(settings)  # No debe lanzar


def test_check_file_permissions_rejects_world_readable(tmp_path):
    """Verifica que permisos 0o644 son rechazados."""
    file_path = tmp_path / ".env"
    file_path.touch()
    os.chmod(file_path, 0o644)

    with pytest.raises(InsecurePermissionsError):
        check_file_permissions(file_path)


def test_check_file_permissions_accepts_restricted(tmp_path):
    """Verifica que permisos 0o600 son aceptados."""
    file_path = tmp_path / ".env"
    file_path.touch()
    os.chmod(file_path, 0o600)

    check_file_permissions(file_path)  # No debe lanzar


def test_check_file_permissions_missing_file():
    """Verifica que un archivo inexistente no lanza error."""
    from pathlib import Path

    check_file_permissions(Path("/tmp/nonexistent-file-12345.env"))  # No debe lanzar
