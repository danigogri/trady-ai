# SDD Design: 001 - Python Project Bootstrap

## Resumen del diseño

Bootstrap del proyecto Python Trady.AI con 4 módulos funcionales (config, security, cli, db) más placeholders para fases futuras. Arquitectura src-layout, build con Hatchling, toolchain unificada con Ruff + mypy. Diseñado alrededor del principio de **fallo temprano y explícito**: la configuración se valida en tiempo de construcción, los secrets se verifican antes de cualquier operación, y la DB se inicializa bajo demanda.

---

## Arquitectura de módulos

```
                    ┌───────────────────────────────────┐
                    │         trady-ai (CLI)            │
                    │    click group: cli               │
                    │    commands: status, analyze      │
                    └──────┬────────────┬───────────────┘
                           │            │
              ┌────────────┼────────────┼──────────────┐
              │            │            │              │
              ▼            ▼            ▼              ▼
    ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
    │   config    │ │ security │ │   cli    │ │     db       │
    │  settings   │ │  secrets │ │  main    │ │  database    │
    │  pydantic   │ │ validate │ │ commands │ │  sqlite-utils│
    │  singleton  │ │  perms   │ │ CliRunner│ │  _metadata   │
    └──────┬──────┘ └────┬─────┘ └──────────┘ └──────┬───────┘
           │             │                            │
           └─────────────┴────────────────────────────┘
                         │
                         ▼
                   ┌───────────┐
                   │  .env /   │
                   │  os.environ│
                   └───────────┘
```

**Reglas de dependencia**:
- `config` → 0 dependencias internas (raíz del grafo)
- `security` → depende de `config` (recibe `Settings`)
- `cli` → depende de `config` (lee settings), depende de `security` (validación early)
- `db` → depende de `config` (recibe `db_path`)
- `security`, `cli`, `db` son **independientes entre sí**

---

## Diseño detallado

### 1. `config/settings.py`

```python
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configuración validada e inmutable del sistema.

    Namespace de env vars: TRADY_AI_*
    Carga desde .env (si existe) + environment variables.
    """

    environment: Literal["development", "demo", "production"] = "development"
    dry_run: bool = True                          # RFC-000: MUST default True
    log_level: str = "INFO"
    db_path: Path = Path("data/trady_ai.db")
    secrets_api_key: str = ""                     # Placeholder hasta Fase 2

    model_config = SettingsConfigDict(
        env_prefix="TRADY_AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",                           # Seguridad: ignora vars inesperadas
        frozen=True,                              # Inmutable post-creación
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna instancia singleton de Settings.

    lru_cache garantiza una única construcción.
    La primera llamada parsea .env + env vars y valida tipos.
    Llamadas subsecuentes retornan la misma instancia (inmutable).
    """
    return Settings()
```

**Patrón singleton con `lru_cache`**: `functools.lru_cache(maxsize=1)` cachea el resultado de `Settings()`. La primera llamada ejecuta el constructor de pydantic-settings (lee `.env`, parsea env vars, valida tipos, aplica defaults). Llamadas siguientes retornan la instancia cacheada — cero overhead. En tests, se limpia con `get_settings.cache_clear()`.

**`frozen=True`**: pydantic genera `__setattr__` que lanza `TypeError` ante cualquier intento de mutación post-creación. Esto garantiza que ninguna parte del sistema pueda modificar la configuración en runtime — alineado con la filosofía determinística.

**`extra="ignore"`**: previene que variables de entorno inesperadas (p.ej., `TRADY_AI_SOMETHING_MALICIOUS`) se inyecten como atributos del modelo. Es una medida de seguridad por diseño.

### 2. `security/secrets.py`

```python
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
            "Ejecutá: chmod 600 {path}"
        )
```

**Filosofía de validación**: `validate_secrets` itera solo los campos explícitamente marcados como secrets. Esto permite agregar nuevos secrets en fases futuras sin cambiar la lógica de validación. La lista `secret_fields` es el punto único de extensión.

**`check_file_permissions`**: usa `os.stat()` en lugar de `Path.stat()` para acceso directo a los bits del modo. Verifica solo el bit `S_IROTH` (lectura para "others") porque ese es el riesgo principal en entornos compartidos. Archivos inexistentes se skippean — el punto es verificar archivos que existen, no reportar ausencias.

### 3. `cli/main.py`

```python
import click
from trady_ai.config.settings import get_settings

logger = structlog.get_logger()


@click.group()
def cli():
    """Trady.AI — Infraestructura financiera determinística."""
    # Inicialización temprana: config + seguridad
    pass


@cli.command()
def status():
    """Muestra configuración actual del sistema.

    Output formateado con valores clave de configuración.
    NUNCA imprime valores de secrets (API keys, etc.).
    """
    settings = get_settings()
    click.echo("Trady.AI Status")
    click.echo(f"  Environment: {settings.environment}")
    click.echo(f"  Dry run:     {settings.dry_run}")
    click.echo(f"  Log level:   {settings.log_level}")
    click.echo(f"  DB path:     {settings.db_path}")
    # NOTA: NO incluir settings.secrets_api_key


@cli.command()
@click.option("--market", default="btc", help="Mercado a analizar")
def analyze(market: str):
    """Analiza un mercado (placeholder hasta Fase 1).

    Este comando es un stub que confirma que el CLI funciona
    pero delega la implementación real a Fase 1+.
    """
    settings = get_settings()
    click.echo(f"Analyze command: market={market}")
    click.echo(f"  Status: not implemented (dry_run={settings.dry_run})")
```

**Entry point**: `trady-ai = trady_ai.cli.main:cli` en `pyproject.toml`. Click registra el grupo y los comandos automáticamente.

**Seguridad en output**: `status` construye el mensaje explícitamente — no itera atributos de Settings (para evitar leaks accidentales si se agregan nuevos campos). Secrets se omiten a propósito.

**Testing con CliRunner**: Click provee `CliRunner` que invoca comandos en aislamiento (sin subprocess real). Permite verificar `output`, `exit_code`, y excepciones.

### 4. `db/database.py`

```python
from pathlib import Path
import sqlite_utils
from trady_ai.config.settings import Settings


def init_db(db_path: Path) -> sqlite_utils.Database:
    """Inicializa la base de datos SQLite.

    1. Crea el directorio padre si no existe (Path.mkdir)
    2. Abre/crea el archivo SQLite via sqlite_utils.Database()
    3. Crea tablas iniciales si no existen (CREATE IF NOT EXISTS)
    4. Retorna la instancia Database

    Es IDEMPOTENTE: llamarlo múltiples veces no falla ni duplica datos.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(db_path)

    # Tabla de metadata: versionado de schema y estado del sistema
    db["_metadata"].create(
        {
            "key": str,
            "value": str,
        },
        pk="key",
        if_not_exists=True,
    )

    return db


def get_db(settings: Settings | None = None) -> sqlite_utils.Database:
    """Wrapper que obtiene db_path de settings y llama init_db."""
    if settings is None:
        settings = get_settings()
    return init_db(settings.db_path)
```

**Por qué `sqlite_utils.Database()` y no `sqlite3.connect()`**: `sqlite_utils` es un wrapper delgado sobre sqlite3 que provee:
- Creación de tablas con `create(..., if_not_exists=True)` — idempotente
- Inserción/query con sintaxis de dict
- Sin ORM, sin migrations engine, sin magic
- 100% determinístico

**`Path.mkdir(parents=True, exist_ok=True)`**: crea `data/` si no existe. Sin esto, sqlite_utils fallaría si el directorio no existe. `parents=True` crea toda la jerarquía necesaria.

---

## Flujo de inicialización

```
$ trady-ai status
  │
  ├─ 1. click resuelve comando "status"
  │
  ├─ 2. status() → get_settings()
  │     │
  │     ├─ 2a. lru_cache miss → Settings()
  │     │     ├─ pydantic-settings busca .env (no requerido)
  │     │     ├─ Lee variables de entorno TRADY_AI_*
  │     │     ├─ Valida tipos (ej: environment debe ser Literal válido)
  │     │     ├─ Aplica defaults para lo no especificado
  │     │     └─ Retorna instancia frozen (inmutable)
  │     │
  │     └─ 2b. lru_cache hit → retorna instancia cacheada
  │
  ├─ 3. status() formatea output (sin secrets)
  │
  └─ 4. click escribe a stdout
```

```
$ trady-ai analyze --market eth
  │
  ├─ 1. click resuelve comando "analyze" con --market=eth
  │
  ├─ 2. analyze() → get_settings()
  │
  ├─ 3. analyze() imprime "not implemented (dry_run=True)"
  │
  └─ 4. click retorna (exit 0)
```

**Nota**: `validate_secrets()` e `init_db()` NO se llaman automáticamente en el bootstrap. Se invocan cuando el comando las necesita. Para Fase 1, el CLI principal llamará validación early antes de ejecutar cualquier operación real.

---

## Decisiones técnicas

### src layout vs flat layout

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **src layout** (`src/trady_ai/`) | Aísla imports, previene confusiones con tests, estándar de la comunidad | ✅ **Elegido** |
| Flat layout (`trady_ai/`) | Más simple, pero `pytest` puede importar el código incorrecto si no hay `--import-mode` | ❌ Descartado |

**Rationale**: `src` layout fuerza a instalar el paquete (`pip install -e .`) antes de importar. Esto previene que los tests importen el código fuente directo (saltándose `pyproject.toml`). Es el layout recomendado por la guía de empaquetado de Python y el estándar de Hatchling.

### pydantic-settings vs python-dotenv vs environs

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **pydantic-settings** | Validación de tipos, `env_prefix`, `.env` loading, integración con pydantic | ✅ **Elegido** |
| python-dotenv | Solo carga `.env`, sin validación, sin tipado | ❌ Descartado |
| environs | Menos mantenido, ecosistema más chico | ❌ Descartado |

**Rationale**: Determinismo requiere validación en tiempo de construcción. `pydantic-settings` garantiza que cualquier typo en `.env` se detecte al arrancar, no en runtime. `python-dotenv` carga strings crudos — un `environment=prod` (sin `uction`) pasaría silenciosamente.

### click vs typer vs argparse

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **click** | CliRunner para tests, maduro, simple para grupos + comandos | ✅ **Elegido** |
| typer | Construido sobre click, más "moderno" pero añade abstracción innecesaria | ❌ Descartado |
| argparse | Stdlib — sin CliRunner, los tests requieren subprocess | ❌ Descartado |

**Rationale**: `click` es battle-tested en infraestructura financiera. `CliRunner` permite tests determinísticos sin forks ni subprocess — crítico para la filosofía determinística.

### structlog vs loguru vs logging estándar

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **structlog** | Logging estructurado, processors pipeline, fácil redactar campos | ✅ **Elegido** |
| loguru | Global state, difícil de testear, sin pipeline de procesadores | ❌ Descartado |
| logging stdlib | Requiere boilerplate para output estructurado, sin redacción built-in | ❌ Descartado |

**Rationale**: `structlog` permite construir procesadores que redacten secrets automáticamente antes de escribir logs. Es la opción más segura para RFC-000 compliance.

### sqlite-utils vs SQLAlchemy vs raw sqlite3

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **sqlite-utils** | Thin wrapper, `create(if_not_exists)`, schema declarativo, sin ORM | ✅ **Elegido** |
| SQLAlchemy | Overkill para 1 tabla, ORM complexity, migrations engine innecesario | ❌ Descartado |
| raw sqlite3 | Más boilerplate, CREATE TABLE manual, sin helpers | ❌ Descartado |

**Rationale**: En Fase 0 solo necesitamos crear una tabla de metadata y abrir la DB. `sqlite-utils` da lo justo sin agregar complejidad de ORM. Es un wrapper delgado — no oculta sqlite3, solo lo hace más seguro.

### httpx vs requests vs aiohttp

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **httpx** | API moderna, sync+async, connection pooling, timeouts por defecto | ✅ **Elegido** |
| requests | En mantenimiento, sin async, sin type hints nativos | ❌ Descartado |
| aiohttp | Async-only, innecesario hasta Fase 2+ | ❌ Descartado |

**Rationale**: `httpx` es la evolución natural de `requests`. Se incluye como dependencia ahora para que esté disponible cuando Fase 1 necesite hacer llamadas HTTP. No se usa en Fase 0.

### Ruff vs black + isort + flake8 + pylint

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| **Ruff** | 100x más rápido, un solo tool, misma calidad de reglas, zero config para projects chicos | ✅ **Elegido** |
| black + isort + flake8 + pylint | 4 tools independientes, config duplicada, orden de ejecución, más lento | ❌ Descartado |

**Rationale**: Ruff implementa las mismas reglas que Flake8 (vía rust-cpython bindings) + isort + pyupgrade + pep8-naming en un solo binario de Rust. Para un proyecto que arranca, tener 4 archivos de config (`.flake8`, `pyproject.toml` para black, `setup.cfg` para isort) es ruido innecesario.

---

## Manejo de errores

### Escenario: No existe `.env`

```python
# Comportamiento: default
settings = get_settings()
# → Settings(environment="development", dry_run=True, ...)
# pydantic-settings NO falla si .env no existe (default behavior).
# Usa defaults del modelo + env vars del sistema.
```

No es un error. `.env` es opt-in para desarrollo local. En producción, las vars se setean via sistema operativo (systemd, Docker, etc.).

### Escenario: El directorio `data/` no existe

```python
init_db(Path("data/trady_ai.db"))
# → db_path.parent.mkdir(parents=True, exist_ok=True) crea "data/"
# → sqlite_utils crea el archivo .db
# → Retorna Database instance
```

`Path.mkdir` con `parents=True` crea toda la jerarquía. `exist_ok=True` previene errores si ya existe.

### Escenario: Secrets inválidos

```python
# En CLI (Fase 1+):
settings = get_settings()
validate_secrets(settings)
# → SecretValidationError si algún secret es placeholder/vacío
# → El CLI muestra el error y sale con exit code 1
# → NUNCA continua con secrets inválidos (fail-closed)
```

El error es explícito: dice qué campo falló y por qué. No hay fallback silencioso.

### Escenario: DB corrupta

```python
try:
    db = sqlite_utils.Database("data/trady_ai.db")
    # Si el archivo existe pero está corrupto:
    # → sqlite3.DatabaseError: file is not a database
except sqlite3.DatabaseError:
    # La excepción se propaga — no se intenta reparación automática
    # El usuario debe eliminar/restaurar el archivo manualmente
    raise
```

No hay recovery automático. La corrupción de DB es un evento que requiere intervención humana. Esto es consistente con el principio de "fail early, fail explicitly".

### Escenario: Archivo `.env` con world-readable permissions

```python
check_file_permissions(Path(".env"))
# → os.stat() detecta S_IROTH (0o004) → InsecurePermissionsError
# → Mensaje incluye el path y el comando para reparar
```

El error incluye la acción correctiva (`chmod 600 .env`). No es fail-silent.

---

## Testing strategy

### Principios

- **Aislamiento total**: todos los tests usan `tmp_path` — nunca tocan el filesystem real
- **Sin mocking innecesario**: donde sea posible, probamos el código real (no mocks)
- **Determinístico**: sin fixtures globales, sin estado compartido entre tests
- **Coverage target**: ≥ 80%

### Fixtures (conftest.py)

```python
@pytest.fixture
def tmp_settings(tmp_path):
    """Settings con db_path en directorio temporal."""
    return Settings(db_path=str(tmp_path / "test.db"))

@pytest.fixture
def tmp_db(tmp_settings):
    """DB inicializada en tmp_path."""
    return init_db(tmp_settings.db_path)
```

### Capas de test

| Capa | Qué prueba | Cómo |
|------|-----------|------|
| **Unit (config)** | Defaults, env override, validación, singleton | `monkeypatch` para env vars, `get_settings.cache_clear()` entre tests |
| **Unit (security)** | Validación de placeholders, permisos | `tmp_path` + `os.chmod`, comparación directa de strings |
| **Unit (cli)** | Output de comandos, no-leakage de secrets | `CliRunner.invoke()`, verificar `result.output` |
| **Integration (db)** | Creación de DB, metadata table, idempotencia | `tmp_path`, `sqlite_utils.Database()` real |

### Consideraciones técnicas

- `get_settings()` usa `lru_cache` → llamar `get_settings.cache_clear()` en cada test que modifica env vars
- `CliRunner` aísla el contexto de click, pero comparte el proceso → `cache_clear()` debe llamarse antes de cada test de CLI
- `monkeypatch` de pytest restaura automáticamente al final del test

---

## Security implementation

### Cómo se implementa `dry_run`

`dry_run: bool = True` en Settings es el flag de seguridad fundamental. Por defecto, toda operación se ejecuta en modo simulado. Comandos reales (Fase 1+) verifican `settings.dry_run` antes de ejecutar:

```python
def execute_trade(order: Order) -> None:
    settings = get_settings()
    if settings.dry_run:
        logger.info("dry_run=True — trade simulated", order=order)
        return
    # ... ejecución real ...
```

Ninguna operación real puede ocurrir sin override explícito (`TRADY_AI_DRY_RUN=false`).

### Cómo se validan permisos de archivos

`check_file_permissions` usa `os.stat()` con bitmask `stat.S_IROTH` (0o004). Solo verifica el bit de lectura para "others". No verifica owner/grupo porque:
- El owner debería poder leer/escribir (0o600 es el target)
- El grupo puede ser seguro en entornos controlados
- El riesgo real es world-readable en sistemas compartidos

### Cómo se previene leakage de secrets

1. **CLI `status`**: output construido manualmente con campos explícitos — no itera `Settings.__dict__`
2. **Logging**: `structlog` permite agregar un processor que redacte campos con regex `sk-*` o `secret_*`
3. **`.gitignore`**: `.env`, `.env.production`, y `*.db` excluidos del VCS
4. **`.env.example`**: solo placeholders, sin valores reales

### Checklist de seguridad post-implementación

- [ ] `trady-ai status` no imprime `secrets_api_key`
- [ ] `dry_run=True` es el default (verificable via CLI)
- [ ] `.env` está en `.gitignore` (no se puede commiteaar accidentalmente)
- [ ] `validate_secrets("changeme")` lanza error
- [ ] `check_file_permissions(0o644)` lanza error
- [ ] `.env.example` no contiene secrets reales
- [ ] `extra="ignore"` en Settings — vars desconocidas no se inyectan
- [ ] `frozen=True` — settings no se puede modificar en runtime

---

## Riesgos técnicos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| `lru_cache` comparte estado entre tests | Baja | `cache_clear()` en cada test; fixture `tmp_settings` para aislamiento |
| Sin lock file → dependencias no reproducibles | Media | Agregar lock file post-bootstrap (uv o pip-tools) |
| `sqlite-utils` puede no manejar schemas complejos | Baja | Es un wrapper delgado — migrar a SQLAlchemy en Fase 2+ si es necesario |
| Empty `__init__.py` en placeholders → imports rotos | Baja | Cada `__init__` tiene docstring; imports solo de módulos implementados |
| Windows no soporta `os.stat().st_mode` igual | Baja | `check_file_permissions` skip en Windows con `sys.platform` check |
