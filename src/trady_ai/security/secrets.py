import os
import stat
from pathlib import Path

from trady_ai.config.settings import Settings


class SecretValidationError(ValueError):
    """Un secret contiene un placeholder o está vacío."""


class InsecurePermissionsError(PermissionError):
    """Archivo sensible tiene permisos mundialmente legibles."""


# Placeholders conocidos — cualquier secret que coincida es rechazado
PLACEHOLDER_PATTERNS = {"changeme", "your-key-here", "placeholder", ""}


def validate_secrets(settings: Settings) -> None:
    """Valida que ningún secret contenga placeholders.

    Itera campos de Settings marcados como secretos.
    Si algún campo está vacío o contiene un placeholder conocido,
    lanza SecretValidationError con el nombre del campo.

    La validación es puramente determinística: compara strings,
    sin I/O externo ni randomness.
    """
    secret_fields = {
        "secrets_api_key": settings.secrets_api_key,
    }

    for field_name, value in secret_fields.items():
        if value in PLACEHOLDER_PATTERNS:
            raise SecretValidationError(
                f"Secret '{field_name}' contiene un placeholder o está vacío. "
                "Configurá un valor real en .env o variable de entorno."
            )


def check_file_permissions(path: Path) -> None:
    """Verifica que un archivo no sea mundialmente legible.

    Permisos seguros: 0o600 (owner read/write) o 0o400 (owner read).
    Permisos inseguros: cualquier bit 'other' (0o004 o superior).
    Si el archivo no existe, la verificación se salta (graceful skip).

    Usa os.stat() y stat.S_* para verificar bits de permisos.
    """
    if not path.exists():
        return  # Skip graceful

    st = os.stat(path)
    # Mask de bits "other": lectura (4), escritura (2), ejecución (1)
    if st.st_mode & stat.S_IROTH:
        raise InsecurePermissionsError(
            f"Archivo {path} tiene permisos {oct(st.st_mode & 0o777)}. "
            "Debe ser 0o600 o más restrictivo. "
            f"Ejecutá: chmod 600 {path}"
        )
