# Tasks: Python Project Bootstrap — Fase 0

## Review Workload Forecast

| Campo | Valor |
|-------|-------|
| Estimated changed lines | ~510 (23 archivos, 14 código + 5 tests + 4 config/docs) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (~250): Foundation + Config + Security + tests → PR 2 (~260): CLI + DB + Integration tests + docs + verification |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium
```

### Suggested Work Units

| Unit | Goal | PR | Status |
|------|------|----|--------|
| 1 | Structure + pyproject.toml + Config + Security + unit tests | PR 1 | ✅ Completado |
| 2 | CLI + DB + Integration tests + conftest + docs + verification | PR 2 | ⏳ Pendiente |

---

## Phase 1: Foundation (6 tareas)

### ✅ 1.1 Crear estructura de directorios y `.gitignore`
**Archivos**: `.gitignore`, `src/trady_ai/{config,security,cli,db,core,adapters,strategies,reflection,governance}/`, `tests/unit/`, `tests/integration/` | **Dep**: —

**Qué**: Crear árbol completo de directorios. `.gitignore` con exclusiones de la spec (`.env`, `.env.production`, `*.db`, `data/`, `__pycache__/`, `*.pyc`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `dist/`, `build/`, `.venv/`, `htmlcov/`, `.coverage`).

**CA**: `ls src/trady_ai/` muestra 9 subdirectorios; `.gitignore` contiene `.env`, `*.db`, `data/`.

### ✅ 1.2 Crear `pyproject.toml`
**Archivos**: `pyproject.toml` | **Dep**: 1.1

**Qué**: Build system Hatchling, `name = "trady-ai"`, `version = "0.1.0"`, `requires-python = ">=3.12"`, entry point `trady-ai = "trady_ai.cli.main:cli"`. Deps: pydantic-settings>=2.0, click>=8.0, structlog>=24.0, httpx>=0.27, sqlite-utils>=3.36. Dev: pytest>=8.0, pytest-cov>=5.0, ruff>=0.5, mypy>=1.10. Tool configs: ruff line-length=120 target py312, ruff.lint select E/F/I/N/W/UP, mypy strict python_version 3.12, pytest testpaths=tests con --cov=trady_ai --cov-report=term-missing.

**CA**: `pip install -e ".[dev]"` exitosa; `trady-ai --help` muestra grupo click.

**Riesgos**: Versiones sin pin exacto → lock file post-bootstrap.

### ✅ 1.3 Crear `__init__.py` raíz y placeholders de fases futuras
**Archivos**: `src/trady_ai/__init__.py`, `src/trady_ai/core/__init__.py`, `src/trady_ai/adapters/__init__.py`, `src/trady_ai/strategies/__init__.py`, `src/trady_ai/reflection/__init__.py`, `src/trady_ai/governance/__init__.py`, `tests/__init__.py` | **Dep**: 1.1

**Qué**: Raíz: `__version__ = "0.1.0"`. Placeholders: docstring con nombre de fase futura. `tests/__init__.py`: vacío.

**CA**: `from trady_ai import __version__` → `"0.1.0"`; importar cualquier placeholder no falla.

### ✅ 1.4 Implementar `config/settings.py`
**Archivos**: `src/trady_ai/config/__init__.py`, `src/trady_ai/config/settings.py` | **Dep**: 1.2

**Qué**: `Settings(BaseSettings)` con fields: `environment: Literal["development","demo","production"] = "development"`, `dry_run: bool = True`, `log_level: str = "INFO"`, `db_path: Path = Path("data/trady_ai.db")`, `secrets_api_key: str = ""`. `model_config`: env_prefix="TRADY_AI_", env_file=".env", extra="ignore", frozen=True. `get_settings()` con `@lru_cache(maxsize=1)`. Re-export en `__init__.py`.

**CA**: `get_settings().dry_run is True`; `environment="invalid"` → `ValidationError`; instancia frozen inmutable; segunda llamada retorna mismo objeto.

### ✅ 1.5 Implementar `security/secrets.py`
**Archivos**: `src/trady_ai/security/__init__.py`, `src/trady_ai/security/secrets.py` | **Dep**: 1.4

**Qué**: `SecretValidationError(ValueError)`, `InsecurePermissionsError(PermissionError)`. `validate_secrets(settings)`: itera `secret_fields` = {"secrets_api_key"}, rechaza valores en `PLACEHOLDER_PATTERNS = {"changeme", "your-key-here", "placeholder", ""}`. `check_file_permissions(path)`: si existe, verifica `st_mode & stat.S_IROTH` → raise si hay bit other-read. Re-export en `__init__.py`.

**CA**: `validate_secrets(Settings(secrets_api_key="changeme"))` → `SecretValidationError`; `check_file_permissions(path_0o644)` → `InsecurePermissionsError`; archivo inexistente → no-error.

### ✅ 1.6 Crear `.env.example` y `README.md`
**Archivos**: `.env.example`, `README.md` | **Dep**: 1.1

**Qué**: `.env.example` con vars: `TRADY_AI_ENVIRONMENT=development`, `TRADY_AI_DRY_RUN=true`, `TRADY_AI_LOG_LEVEL=INFO`, `TRADY_AI_DB_PATH=data/trady_ai.db`, `TRADY_AI_SECRETS_API_KEY=`. README: título, quick start (`pip install -e ".[dev]"`), estructura de directorios, comandos CLI, advertencia de seguridad (`.env` nunca al VCS).

**CA**: `.env.example` no contiene secrets reales; README menciona advertencia de `.env`.

---

## Phase 2: CLI + DB (2 tareas)

### ✅ 2.1 Implementar `cli/main.py`
**Archivos**: `src/trady_ai/cli/__init__.py`, `src/trady_ai/cli/main.py` | **Dep**: 1.4

**Qué**: `@click.group()` `cli()`. `@cli.command()` `status()`: obtiene `get_settings()`, click.echo con environment, dry_run, log_level, db_path — NUNCA secrets_api_key. `@cli.command()` `@click.option("--market")` `analyze(market)`: stub que imprime `"not implemented (dry_run={settings.dry_run})"`. Logger structlog.

**CA**: `trady-ai status` muestra environment y dry_run; output NO contiene API key; `trady-ai analyze --market btc` imprime "not implemented".

**Riesgos**: Leak accidental de secrets en status → mitigado con output explícito campo por campo (sin iterar Settings).

### ✅ 2.2 Implementar `db/database.py`
**Archivos**: `src/trady_ai/db/__init__.py`, `src/trady_ai/db/database.py` | **Dep**: 1.4

**Qué**: `init_db(db_path)`: `db_path.parent.mkdir(parents=True, exist_ok=True)`, `sqlite_utils.Database(db_path)`, crea tabla `_metadata(key TEXT PRIMARY KEY, value TEXT)` con `if_not_exists=True`. Retorna Database. `get_db(settings)`: wrapper que usa `settings.db_path`.

**CA**: `init_db(tmp_path / "test.db")` crea el archivo; `_metadata` table existe; llamar `init_db` x2 no falla ni duplica.

---

## Phase 3: Testing (5 tareas)

### ✅ 3.1 Crear `tests/conftest.py`
**Archivos**: `tests/conftest.py` | **Dep**: 1.4, 2.2

**Qué**: `@pytest.fixture` `tmp_settings(tmp_path)`: `Settings(db_path=str(tmp_path / "test.db"))`. `@pytest.fixture` `tmp_db(tmp_settings)`: `init_db(tmp_settings.db_path)`. `get_settings.cache_clear()` en autouse si es necesario.

**CA**: Fixtures usan `tmp_path` exclusivamente; ningún test accede a filesystem real.

### ✅ 3.2 Escribir `tests/unit/test_config.py`
**Archivos**: `tests/unit/test_config.py` | **Dep**: 3.1

**Qué**: 4 tests: `test_settings_defaults` (dry_run=True, environment="development"); `test_settings_from_env` (monkeypatch `TRADY_AI_DRY_RUN` → false); `test_settings_env_validation` (environment="invalid" → `ValidationError`); `test_get_settings_singleton` (`cache_clear()` entre llamadas, verificar `is`).

**CA**: 4/4 pasan; coverage de config ≥ 95%.

### ✅ 3.3 Escribir `tests/unit/test_security.py`
**Archivos**: `tests/unit/test_security.py` | **Dep**: 3.1

**Qué**: 6 tests: placeholder reject ("changeme"); empty reject (""); valid accept ("sk-live-abc123"); world-readable reject (`tmp_path` + `os.chmod(0o644)`); restricted accept (`os.chmod(0o600)`); missing file skip (path inexistente).

**CA**: 6/6 pasan; coverage de security ≥ 95%.

### ✅ 3.4 Escribir `tests/unit/test_cli.py`
**Archivos**: `tests/unit/test_cli.py` | **Dep**: 3.1

**Qué**: 3 tests via `CliRunner`: `test_status_command` (output contiene "dry_run", "environment"); `test_status_no_secrets_leaked` (output NO contiene secrets_api_key ni valores de API key); `test_analyze_not_implemented` (output contiene "not implemented").

**CA**: 3/3 pasan; coverage de cli ≥ 90%.

### ✅ 3.5 Escribir `tests/integration/test_db.py`
**Archivos**: `tests/integration/test_db.py` | **Dep**: 3.1

**Qué**: 3 tests: `test_db_creation` (verificar archivo .db existe post-init); `test_db_metadata_table` (query `_metadata` table exists); `test_db_idempotent` (init_db ×2 no falla).

**CA**: 3/3 pasan; coverage de db ≥ 90%.

---

## Phase 4: Verification (1 tarea)

### ✅ 4.1 Verificación final
**Archivos**: Todos los anteriores | **Dep**: 1.2, 1.4, 1.5, 2.1, 2.2, 3.2, 3.3, 3.4, 3.5

**Qué**: Ejecutar batería completa: `pip install -e ".[dev]"` → ok; `pytest --cov=trady_ai --cov-report=term-missing` → todos pasan, ≥ 80% coverage; `ruff check .` → 0 errores; `mypy src/` → 0 errores. Validar checklist de seguridad RFC-000: dry_run=True default, `trady-ai status` sin secrets, `.env` en `.gitignore`, validate_secrets bloquea placeholders, frozen=True.

**CA**: Todos los comandos exitosos; coverage ≥ 80%; security checklist completo.

---

## Resumen

| Fase | Tareas | Estado |
|------|--------|--------|
| Phase 1: Foundation | 1.1–1.6 (6/6) | ✅ Implementado |
| Phase 2: CLI + DB | 2.1–2.2 (2/2) | ✅ Implementado |
| Phase 3: Testing | 3.1–3.5 (5/5) | ✅ Implementado |
| Phase 4: Verification | 4.1 (1/1) | ✅ Completado |
| **Total PR #2** | **5 tareas** | **✅ Completado** |

---

## Dependencias entre tareas

```
1.1 (dirs + gitignore)
 ├─ 1.2 (pyproject.toml)
 │    └─ 1.4 (config/settings) ──┐
 │                               ├─ 1.5 (security/secrets)
 │                               ├─ 2.1 (cli/main)
 │                               └─ 2.2 (db/database)
 ├─ 1.3 (__init__ placeholders)
 └─ 1.6 (.env.example + README)
                                      └─ 3.1 (conftest.py)
                                           ├─ 3.2 (test_config)
                                           ├─ 3.3 (test_security)
                                           ├─ 3.4 (test_cli)
                                           └─ 3.5 (test_db)
                                                     └─ 4.1 (verification)
```

## Orden de ejecución recomendado

1. **Tareas 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6**: Foundation completa. Al llegar acá ya tenés `pip install -e .[dev]` funcionando y los módulos config/security implementados.
2. **Tareas 2.1 → 2.2**: CLI y DB. Independientes entre sí, ambos dependen de config.
3. **Tarea 3.1**: conftest.py (necesario para todos los tests).
4. **Tareas 3.2 → 3.3 → 3.4 → 3.5**: Tests en cualquier orden (todos dependen de 3.1).
5. **Tarea 4.1**: Verification final. Correr todo y validar security checklist.

Si se opta por PRs encadenados:
- **PR 1**: 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 + 3.1 + 3.2 + 3.3 (~250 líneas)
- **PR 2**: 2.1 → 2.2 + 3.4 → 3.5 + 4.1 (~260 líneas)
