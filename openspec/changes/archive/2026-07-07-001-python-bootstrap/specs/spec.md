# SDD Spec: 001 - Python Project Bootstrap

## Resumen

Esta spec cubre el bootstrap completo del proyecto Python de Trady.AI: estructura de paquetes, build system, tooling, configuración, seguridad básica, CLI esqueleto, base de datos SQLite, y tests iniciales. Establece la base determinística sobre la cual se construyen todas las fases posteriores (Fase 1 → Deterministic Core).

**RFC de referencia**: RFC-000 (Security & Operational Safety), RFC-001 (Deterministic Core Architecture)
**Fase del roadmap**: Fase 0 → Fase 1
**Boundary**: 100% determinístico. No hay componentes de inteligencia en esta spec.

---

## Archivos a crear

### 1. `pyproject.toml`

- **Propósito**: Definición única del paquete, build system, dependencias y configuración de tools.
- **Build system**: Hatchling (`build-backend = hatchling.build`)
- **Contenido exacto**:
  - `[build-system]`: requires = `["hatchling"]`, build-backend = `"hatchling.build"`
  - `[project]`: name = `trady-ai`, version = `"0.1.0"`, requires-python = `">=3.12"`
  - `[project.scripts]`: `trady-ai = "trady_ai.cli.main:cli"`
  - Dependencies: `pydantic-settings>=2.0`, `click>=8.0`, `structlog>=24.0`, `httpx>=0.27`, `sqlite-utils>=3.36`
  - Dev dependencies (optional-dependencies.dev): `pytest>=8.0`, `pytest-cov>=5.0`, `ruff>=0.5`, `mypy>=1.10`
- **Tool configs**:
  - `[tool.hatch.build.targets.wheel]`: packages = `["src/trady_ai"]`
  - `[tool.pytest.ini_options]`: testpaths = `["tests"]`, addopts = `"--cov=trady_ai --cov-report=term-missing"`
  - `[tool.ruff]`: line-length = 120, target-version = `"py312"`
  - `[tool.ruff.lint]`: select = `["E", "F", "I", "N", "W", "UP"]`
  - `[tool.mypy]`: strict = true, python_version = `"3.12"`, warn_return_any = true, warn_unused_configs = true
- **Dependencias**: Ninguna (archivo de configuración)
- **Comportamiento determinístico**: Versiones fijadas con `>=` mínimo para reproducibilidad. Lock file futuro (uv.lock o requirements.lock) no incluido en esta spec.
- **Tests**: N/A (config file)
- **Seguridad**: Define el surface de dependencias. Minimiza dependencias para reducir attack surface.

### 2. `src/trady_ai/__init__.py`

- **Propósito**: Entry point del paquete. Expone `__version__`.
- **Interfaz**: `__version__: str = "0.1.0"`
- **Dependencias**: Ninguna
- **Comportamiento determinístico**: Versión hardcodeada, sincronizada con pyproject.toml.
- **Tests**: `test_version_exists` — verifica que `__version__` está definido.
- **Seguridad**: Sin implicaciones.

### 3. `src/trady_ai/config/__init__.py`

- **Propósito**: Re-exporta `Settings` y `get_settings` para importación limpia.
- **Interfaz**: `from trady_ai.config.settings import Settings, get_settings`
- **Dependencias**: `trady_ai.config.settings`
- **Tests**: N/A (re-export)
- **Seguridad**: Sin implicaciones directas.

### 4. `src/trady_ai/config/settings.py`

- **Propósito**: Configuración centralizada vía pydantic-settings. Carga desde `.env` y variables de entorno.
- **Interfaz**:
  - `class Settings(BaseSettings)`:
    - `environment: Literal["development", "demo", "production"] = "development"`
    - `dry_run: bool = True` (MUST default True — RFC-000)
    - `log_level: str = "INFO"`
    - `db_path: Path = Path("data/trady_ai.db")`
    - `secrets_api_key: str = ""` (placeholder hasta Fase 2)
    - `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`
  - `def get_settings() -> Settings`: Singleton via `functools.lru_cache`. Retorna instancia de Settings.
- **Dependencias**: `pydantic-settings`, `pathlib`, `typing`, `functools`
- **Comportamiento determinístico**: Valores por defecto explícitos. `dry_run=True` garantiza que NINGUNA operación real se ejecuta sin override explícito. La configuración es inmutable post-inicialización (pydantic frozen).
- **Tests**:
  - `test_settings_defaults`: verifica `dry_run=True`, `environment="development"`, `log_level="INFO"`
  - `test_settings_from_env`: setea `TRADY_AI_DRY_RUN=false` y verifica override
  - `test_settings_env_validation`: verifica que `environment="invalid"` falla con ValidationError
  - `test_get_settings_singleton`: verifica que dos llamadas retornan la misma instancia
- **Seguridad**: `dry_run=True` por defecto es la protección #1 contra ejecución accidental. `extra="ignore"` previene que variables inesperadas se inyecten. Validación de tipos por pydantic.

### 5. `src/trady_ai/security/__init__.py`

- **Propósito**: Re-exporta funciones de seguridad.
- **Interfaz**: `from trady_ai.security.secrets import validate_secrets, check_file_permissions`
- **Dependencias**: `trady_ai.security.secrets`
- **Tests**: N/A (re-export)
- **Seguridad**: Módulo de seguridad — toda falla MUST ser fail-closed.

### 6. `src/trady_ai/security/secrets.py`

- **Propósito**: Validación de secrets y verificación de permisos de archivos sensibles.
- **Interfaz**:
  - `def validate_secrets(settings: Settings) -> None`: Valida que los secrets no contengan placeholders (`"changeme"`, `"your-key-here"`, `""`). Lanza `SecretValidationError` si falla.
  - `def check_file_permissions(path: Path) -> None`: Verifica que un archivo sensible (`.env`, keys) no tenga permisos de lectura mundial (0o044 or stricter). Lanza `InsecurePermissionsError` si falla.
  - `class SecretValidationError(ValueError)`: Excepción custom.
  - `class InsecurePermissionsError(PermissionError)`: Excepción custom.
- **Dependencias**: `pathlib`, `os`, `trady_ai.config.settings`
- **Comportamiento determinístico**: Validación puramente determinística — sin I/O externo, sin randomness. Solo compara strings y verifica bits de permisos.
- **Tests**:
  - `test_validate_secrets_rejects_placeholder`: `secrets_api_key="changeme"` → lanza SecretValidationError
  - `test_validate_secrets_rejects_empty`: `secrets_api_key=""` → lanza SecretValidationError
  - `test_validate_secrets_accepts_valid`: `secrets_api_key="sk-live-abc123"` → no lanza
  - `test_check_file_permissions_rejects_world_readable`: archivo con 0o644 → lanza InsecurePermissionsError
  - `test_check_file_permissions_accepts_restricted`: archivo con 0o600 → no lanza
  - `test_check_file_permissions_missing_file`: archivo inexistente → no lanza (skip gracefully)
- **Seguridad**: Fail-closed. Cualquier secret con placeholder MUST bloquear ejecución en producción. Permisos de archivos sensibles MUST ser verificados antes de lectura.

### 7. `src/trady_ai/cli/__init__.py`

- **Propósito**: Re-exporta el grupo CLI.
- **Interfaz**: `from trady_ai.cli.main import cli`
- **Dependencias**: `trady_ai.cli.main`
- **Tests**: N/A (re-export)
- **Seguridad**: Sin implicaciones.

### 8. `src/trady_ai/cli/main.py`

- **Propósito**: CLI entry point. Grupo Click con comandos iniciales.
- **Interfaz**:
  - `@click.group() def cli()`: Grupo principal.
  - `@cli.command() def status()`: Muestra configuración actual (environment, dry_run, db_path, log_level). NO muestra secrets.
  - `@cli.command() @click.option("--market") def analyze(market: str)`: Placeholder. Imprime mensaje de "not implemented" con dry_run status.
- **Dependencias**: `click`, `trady_ai.config.settings`, `structlog`
- **Comportamiento determinístico**: `status` es puramente determinístico — lee config y formatea output. `analyze` es stub que respeta dry_run.
- **Tests**:
  - `test_status_command`: invoca `status` via CliRunner, verifica que output contiene "dry_run" y "environment"
  - `test_status_no_secrets_leaked`: verifica que output NO contiene valores de secrets
  - `test_analyze_not_implemented`: invoca `analyze --market btc`, verifica mensaje "not implemented"
- **Seguridad**: `status` MUST NOT imprimir secrets ni API keys. Logging via structlog (no print) para evitar leaks en stdout no controlado.

### 9. `src/trady_ai/db/__init__.py`

- **Propósito**: Re-exporta funciones de base de datos.
- **Interfaz**: `from trady_ai.db.database import init_db, get_db`
- **Dependencias**: `trady_ai.db.database`
- **Tests**: N/A (re-export)
- **Seguridad**: Sin implicaciones.

### 10. `src/trady_ai/db/database.py`

- **Propósito**: Inicialización de SQLite y gestión de conexión.
- **Interfaz**:
  - `def init_db(db_path: Path) -> sqlite_utils.Database`: Crea/abre la base de datos en `db_path`. Crea tablas iniciales si no existen. Retorna Database instance.
  - `def get_db(settings: Settings) -> sqlite_utils.Database`: Wrapper que usa `settings.db_path`. Llama `init_db`.
  - Tablas iniciales: `_metadata(key TEXT PRIMARY KEY, value TEXT)` — para migraciones y versioning de schema.
- **Dependencias**: `sqlite_utils`, `pathlib`, `trady_ai.config.settings`
- **Comportamiento determinístico**: SQLite es determinístico por naturaleza. Schema versionado via `_metadata`. Sin operaciones no-determinísticas (sin `RANDOM()`, sin timestamps implícitos).
- **Tests**:
  - `test_db_creation`: verifica que el archivo SQLite se crea en la path especificada
  - `test_db_metadata_table`: verifica que la tabla `_metadata` existe post-init
  - `test_db_idempotent`: llamar `init_db` dos veces no falla ni duplica tablas
- **Seguridad**: DB path viene de settings (validada). No se ejecutan queries raw de fuentes externas. SQLite local-first = sin network surface.

### 11. `src/trady_ai/core/__init__.py`

- **Propósito**: Placeholder para Fase 1 (Deterministic Core).
- **Contenido**: Empty file (docstring only).
- **Seguridad**: Sin implicaciones.

### 12. `src/trady_ai/adapters/__init__.py`

- **Propósito**: Placeholder para Fase 2 (Platform Integration).
- **Contenido**: Empty file (docstring only).
- **Seguridad**: Sin implicaciones.

### 13. `src/trady_ai/strategies/__init__.py`

- **Propósito**: Placeholder para Fase 3 (Strategy Infrastructure).
- **Contenido**: Empty file (docstring only).
- **Seguridad**: Sin implicaciones.

### 14. `src/trady_ai/reflection/__init__.py`

- **Propósito**: Placeholder para Fase 4 (Reflection Systems).
- **Contenido**: Empty file (docstring only).
- **Seguridad**: Sin implicaciones.

### 15. `src/trady_ai/governance/__init__.py`

- **Propósito**: Placeholder para Fase 7 (Governance Hardening).
- **Contenido**: Empty file (docstring only).
- **Seguridad**: Sin implicaciones.

### 16. `tests/__init__.py`

- **Propósito**: Marca `tests/` como paquete Python.
- **Contenido**: Empty file.

### 17. `tests/conftest.py`

- **Propósito**: Fixtures compartidas para todos los tests.
- **Interfaz**:
  - `@pytest.fixture def tmp_settings(tmp_path) -> Settings`: Retorna Settings con `db_path` apuntando a `tmp_path`.
  - `@pytest.fixture def tmp_db(tmp_settings) -> sqlite_utils.Database`: Retorna DB inicializada en directorio temporal.
- **Dependencias**: `pytest`, `pathlib`, `trady_ai.config.settings`, `trady_ai.db.database`
- **Comportamiento determinístico**: Todos los fixtures usan `tmp_path` — aislamiento total, sin side effects.
- **Tests**: N/A (fixtures)
- **Seguridad**: Aislamiento de tests — ningún test accede a datos reales.

### 18. `tests/unit/test_config.py`

- **Propósito**: Tests unitarios para módulo config.
- **Tests**:
  - `test_settings_defaults`: `get_settings()` retorna defaults correctos
  - `test_settings_from_env`: monkeypatch env vars → override funciona
  - `test_settings_env_validation`: environment inválido → ValidationError
  - `test_get_settings_singleton`: dos llamadas → misma instancia
- **Dependencias**: `pytest`, `monkeypatch`, `trady_ai.config.settings`

### 19. `tests/unit/test_security.py`

- **Propósito**: Tests unitarios para módulo security.
- **Tests**:
  - `test_validate_secrets_rejects_placeholder`
  - `test_validate_secrets_rejects_empty`
  - `test_validate_secrets_accepts_valid`
  - `test_check_file_permissions_rejects_world_readable`
  - `test_check_file_permissions_accepts_restricted`
  - `test_check_file_permissions_missing_file`
- **Dependencias**: `pytest`, `os`, `pathlib`, `trady_ai.security.secrets`

### 20. `tests/integration/test_db.py`

- **Propósito**: Tests de integración para módulo db.
- **Tests**:
  - `test_db_creation`: init_db crea archivo
  - `test_db_metadata_table`: tabla _metadata existe
  - `test_db_idempotent`: doble init no falla
- **Dependencias**: `pytest`, `pathlib`, `trady_ai.db.database`

### 21. `.env.example`

- **Propósito**: Template de variables de entorno. NO contiene secrets reales.
- **Contenido**:
  ```
  TRADY_AI_ENVIRONMENT=development
  TRADY_AI_DRY_RUN=true
  TRADY_AI_LOG_LEVEL=INFO
  TRADY_AI_DB_PATH=data/trady_ai.db
  TRADY_AI_SECRETS_API_KEY=
  ```
- **Seguridad**: Solo placeholders. Debe copiarse a `.env` y llenarse manualmente.

### 22. `.gitignore`

- **Propósito**: Excluir archivos sensibles y generados del VCS.
- **Contenido clave**:
  ```
  .env
  .env.production
  *.db
  data/
  __pycache__/
  *.pyc
  .mypy_cache/
  .pytest_cache/
  .ruff_cache/
  *.egg-info/
  dist/
  build/
  .venv/
  htmlcov/
  .coverage
  ```
- **Seguridad**: `.env`, `.env.production`, `*.db` y `data/` excluidos. Crítico para RFC-000.

### 23. `README.md`

- **Propósito**: Documentación mínima del proyecto. Setup, usage, estructura.
- **Contenido**: Quick start, instalación (`pip install -e .[dev]`), comandos CLI, estructura de directorios, cómo contribuir.
- **Seguridad**: Menciona explícitamente que `.env` nunca debe commitearse.

---

## Contratos

### Módulo config

| Contrato | Tipo | Detalle |
|----------|------|---------|
| `get_settings() -> Settings` | Function | Singleton cacheado. Retorna configuración validada. |
| `Settings.environment` | `Literal["development", "demo", "production"]` | Default: `"development"` |
| `Settings.dry_run` | `bool` | Default: `True`. **MUST NOT** ser False sin override explícito. |
| `Settings.log_level` | `str` | Default: `"INFO"` |
| `Settings.db_path` | `Path` | Default: `Path("data/trady_ai.db")` |
| `Settings.secrets_api_key` | `str` | Default: `""`. Placeholder hasta Fase 2. |

### Módulo security

| Contrato | Tipo | Detalle |
|----------|------|---------|
| `validate_secrets(settings) -> None` | Function | Lanza `SecretValidationError` si algún secret es placeholder o vacío. |
| `check_file_permissions(path) -> None` | Function | Lanza `InsecurePermissionsError` si archivo es world-readable. |
| `SecretValidationError` | Exception | Hereda de `ValueError`. |
| `InsecurePermissionsError` | Exception | Hereda de `PermissionError`. |

### Módulo cli

| Contrato | Tipo | Detalle |
|----------|------|---------|
| `trady-ai status` | Command | Muestra config actual. NO muestra secrets. |
| `trady-ai analyze --market <name>` | Command | Stub. Indica "not implemented". Respeta dry_run. |

### Módulo db

| Contrato | Tipo | Detalle |
|----------|------|---------|
| `init_db(db_path) -> Database` | Function | Crea/abre SQLite. Crea tablas iniciales. Idempotente. |
| `get_db(settings) -> Database` | Function | Wrapper sobre `init_db` usando `settings.db_path`. |

---

## Tests requeridos

### Unit tests (mínimo 10)

| Test | Módulo | Verifica |
|------|--------|----------|
| `test_version_exists` | `__init__` | `__version__` definido |
| `test_settings_defaults` | config | Defaults correctos |
| `test_settings_from_env` | config | Override vía env vars |
| `test_settings_env_validation` | config | Environment inválido → error |
| `test_get_settings_singleton` | config | Singleton funciona |
| `test_validate_secrets_rejects_placeholder` | security | Placeholder rechazado |
| `test_validate_secrets_rejects_empty` | security | Vacío rechazado |
| `test_validate_secrets_accepts_valid` | security | Válido aceptado |
| `test_check_file_permissions_rejects_world_readable` | security | 0o644 rechazado |
| `test_check_file_permissions_accepts_restricted` | security | 0o600 aceptado |
| `test_check_file_permissions_missing_file` | security | Missing file → skip |
| `test_status_command` | cli | Output correcto |
| `test_status_no_secrets_leaked` | cli | No filtra secrets |
| `test_analyze_not_implemented` | cli | Stub funciona |

### Integration tests (mínimo 3)

| Test | Módulo | Verifica |
|------|--------|----------|
| `test_db_creation` | db | SQLite se crea |
| `test_db_metadata_table` | db | Tabla _metadata existe |
| `test_db_idempotent` | db | Doble init no falla |

### Coverage target: ≥ 80%

---

## Seguridad

### Principios RFC-000 aplicados

1. **dry_run=True por defecto**: Ninguna operación real se ejecuta sin override explícito. Es la protección fundamental contra ejecución accidental en sistemas financieros.
2. **Secrets validation**: Placeholders como `"changeme"` o `"your-key-here"` son rechazados activamente. Fail-closed.
3. **File permissions**: `.env` y archivos sensibles deben tener permisos restrictivos (0o600). Verificación automática.
4. **No secret leakage**: El comando `trady-ai status` MUST NOT imprimir valores de secrets. Logging via structlog con redacción de campos sensibles.
5. **Least privilege**: El paquete instala solo las dependencias necesarias. Sin extras innecesarios.
6. **`.gitignore` exhaustivo**: `.env`, `.env.production`, `*.db`, `data/` excluidos del VCS.
7. **Local-first**: SQLite como DB — sin network surface, sin credenciales de DB remotas.

### Boundary determinístico

Todo el comportamiento de esta spec es 100% determinístico:
- Configuración: valores por defecto explícitos, validación determinística
- Seguridad: comparación de strings, verificación de bits de permisos
- DB: schema fijo, sin timestamps implícitos, sin randomness
- CLI: output formateado deterministicamente desde config

---

## Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Sin lock file → dependencias no reproducibles entre installs | Medium | Agregar lock file en follow-up inmediato (uv o pip-tools) |
| `lru_cache` en `get_settings()` → tests pueden compartir estado | Low | Usar `monkeypatch` y `tmp_settings` fixture. Documentar que tests deben invalidar cache si modifican env. |
| `check_file_permissions` no funciona en Windows | Low | Documentar limitación. En Windows, skip con warning. |
| Placeholder modules vacíos → imports pueden fallar | Low | Cada `__init__.py` tiene docstring. Imports explícitos solo de módulos implementados. |
| Coverage < 80% si se agregan más módulos sin tests | Medium | CI gate en follow-up. Configurar threshold en pyproject.toml. |

---

## Criterios de aceptación

- [ ] `pip install -e .[dev]` funciona sin errores
- [ ] `trady-ai status` muestra config por defecto sin errores
- [ ] `pytest` pasa con ≥ 80% coverage
- [ ] `ruff check .` sin errores
- [ ] `mypy src/` sin errores
- [ ] `dry_run=True` por defecto (verificable via `trady-ai status`)
- [ ] `.env.production` está en `.gitignore`
- [ ] `trady-ai status` NO imprime valores de secrets
