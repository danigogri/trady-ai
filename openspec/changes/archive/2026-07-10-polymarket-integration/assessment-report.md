# Assessment Report + Documento Contrato — Backlog Fase 2 (BL-009 a BL-017)

**Estado**: Propuesta para aprobación del usuario
**Fecha**: 2026-07-09
**Fuente hallazgos**: `openspec/changes/polymarket-integration/verify-report.md` (commit `eee2999`, verify #1 FAIL)
**Protocolo**: SDD-CYCLE-GOVERNANCE.md §7 (Assessment de 2 niveles)
**Regla**: Este documento es análisis. CERO código tocado hasta aprobación explícita del usuario.

---

## Convenciones del documento

- **Riesgo protocolo**: 🟢 trivial (aplicar directo con `assessment: trivial` en commit) | 🟡 requiere Assessment (acá está) | 🔴 requiere Assessment + Documento Contrato extendido
- **Verificación post-fix**: tras cada BL, gates full (`mypy`, `ruff`, `pytest`, coverage). Solo se hace amend del commit WIP cuando un grupo lógico completa.
- **No tocar**: `openspec/specs/003-...spec.md` (do-not-change), `security/secrets.py` `validate_secrets` existente (Option C), tests existentes de Fase 1.

---

# Orden 1 — BL-012: corregir apply-progress (doc edit)

## Assessment Report

**Hallazgo**: `openspec/changes/polymarket-integration/apply-progress.md` línea 6 afirma:
```
**Tests**: 195 passed | **Coverage**: 89% | **ruff**: 0 | **mypy**: 0 new
```
- Tests, coverage, ruff: verificado TRUE
- **"mypy: 0 new"**: verificado **FALSE** — hay 19 errores en código nuevo (persistence.py: 2, polymarket.py: 17)

Línea 61: `## Deviations from Design` → `**None.** Implementation follows spec + design exactly. All 12 architectural decisions honored.`
- Verificado **FALSE**: hay 2 desvíos (raw_payload nullable, gap-fill simplificado)

**Causa raíz**: el apply-phase reportó verde sin correr mypy, o lo corrió pero interpretó "0 new" como "0 errores NUEVOS respecto a baseline Fase 1" (que era 0 — entonces cualquier error en código nuevo ES nuevo).

**Impacto**: aplicó engañoso al lector. Verify #1 atrapó esto como CRITICAL (hallazgo #2). Es exactamente el patrón que verify debe atrapar.

**Alternativas**:
- (A) Editar inline corrigiendo "mypy: 0 new" → "mypy: 19 errors (post-verify, being fixed via BL-009)" + agregar "Deviations from Design" con 2 items — **Recomendada**
- (B) Borrar apply-progress y regenerar desde cero — descartada (pierde la palabra del aplicador)

## Documento Contrato

- **Archivos afectados**: `openspec/changes/polymarket-integration/apply-progress.md` (1)
- **Líneas afectadas**: línea 6 (corregir gate mypy), línea 59-61 (agregar desvíos)
- **Qué se cambia**:
  - Línea 6: `mypy: 0 new` → `mypy: 19 errors (post-verify, fixing via BL-009)`
  - Sección "Deviations from Design" (líneas 59-61): reemplazar `**None.**...` con lista de 2 desvíos reales:
    1. `raw_payload` nullable (TEXT) vs design TEXT NOT NULL → siendo fixed via BL-015
    2. `_handle_reconnect` simplified (fetch current, no historical gap fill) vs design "REST fetch since timestamp" → siendo fixed via BL-014
- **Qué NO se toca**: claims verdaderos (pytest, coverage, ruff, tasks completas), decisiones de implementación, edge cases.
- **Verification gate**: doc edit, no requiere mypy/ruff/pytest. Confirmar que el archivo es markdown válido.
- **Riesgo**: 🟢 trivial — doc edit.

---

# Orden 2 — BL-010 + BL-011: validate_execution_secrets + tests (unidad conectada)

## Assessment Report

**Hallazgo**: `validate_polymarket_secrets(settings: Any, execution_mode: str)` definida en `cli/main.py` línea 9 pero **nunca invocada** desde `capture` (línea 197) ni `run` (línea 159). Sin tests.

Verificado con `grep -n "validate_polymarket_secrets"` en cli/main.py: solo la definición (línea 9), zero invocaciones.

**Espec Module 9** (líneas 1057-1059 del spec) exige:
- `trady-ai capture` calls `validate_secrets` before connecting WS.
- `trady-ai run` calls `validate_secrets` before executing.

**En live mode**, esto permitiría capturar/ejecutar sin validar credentials — bug de seguridad real.

**Causa raíz**: la función se creó en cli/main.py (lugar equivocado — debería estar en security/) pero nunca se cableó a los comandos. Posiblemente el implementador pensó "después lo invoco" y se olvidó.

**Decisiones de implementación (Option C del review, aprobada por usuario)**:
- Mantener `validate_secrets(settings)` existente en `src/trady_ai/security/secrets.py` SIN CAMBIOS
- Mover `validate_polymarket_secrets` de `cli/main.py` a NUEVO archivo `src/trady_ai/security/polymarket.py`
- Renombrar a `validate_execution_secrets(settings, execution_mode)` para honrar contrato del spec Module 9

**Alternativas para el módulo destino**:
- (A) `src/trady_ai/security/polymarket.py` (nuevo archivo) — **Recomendada**: máxima cohesión con security/secrets.py existente, separación clara de responsabilidades (placeholder vs execution-mode)
- (B) Añadir a security/secrets.py existente — descartada: mezcla dos responsabilidades distintas, arriesga romper Option C
- (C) Dejar en cli/main.py pero invocarla — descartada: indica el spec Module 9 implícito que pertenece a security layer

**Alternativas para invocación**:
- (A) Llamar `validate_execution_secrets(settings, config.execution_mode)` al inicio de `capture()` y `run()` post-settings load, pre-conn — **Recomendada**: fail-fast, cero overhead en dry_run
- (B) Llamar solo en `run()` — descartada: captura en live mode también necesita creds (WS auth)
- (C) En ambos + volverla lazy — descartada: añade complejidad innecesaria

## Documento Contrato

- **Archivos afectados**: 3
  1. `src/trady_ai/security/polymarket.py` (NUEVO)
  2. `src/trady_ai/cli/main.py` (MODIFICADO)
  3. `tests/unit/test_security_polymarket.py` (NUEVO)
- **Líneas afectadas**:
  - cli/main.py: eliminar definición líneas 9-36 (~28 líneas), agregar import + 2 invocaciones (1 en run ≈ 2 líneas, 1 en capture ≈ 2 líneas)
  - security/polymarket.py: nueva función `validate_execution_secrets(settings: Settings, execution_mode: Literal["dry_run", "live"]) -> None` con la misma lógica pero firma tipada
- **Qué se cambia**:
  - Crear `security/polymarket.py` con la función renombrada, firma tipada (`Settings` en vez de `Any`, `Literal[...]` en vez de `str`)
  - Eliminar la definición de `cli/main.py` (líneas 9-36)
  - Agregar `from trady_ai.security.polymarket import validate_execution_secrets` a cli/main.py
  - En `run()` (después de línea 168 `config = settings.get_runtime_config()`): agregar `validate_execution_secrets(settings, config.execution_mode)`
  - En `capture()` (después de línea 203 `settings = get_settings()`): agregar `validate_execution_secrets(settings, settings.get_runtime_config().execution_mode)`
  - Crear `test_security_polymarket.py` con 3 tests (dry_run no-op, live missing raises, live complete pasa)
- **Qué NO se toca**:
  - `security/secrets.py` existente (Option C, contract preservation)
  - Otros tests existentes
  - Lógica del rest de cli/main.py
- **Verification gate**:
  - mypy: sin errores nuevos en security/polymarket.py ni cli/main.py
  - ruff: clean
  - pytest: ≥198 passed (3 tests nuevos minimum)
  - coverage security/polymarket.py: 100%
- **Riesgo**: 🟡 requiere Assessment (aprobada arriba) — aplica directo post-aprobación.

---

# Orden 3 — BL-009: mypy 19 errors (annotations)

## Assessment Report

**Hallazgo**: 19 errores mypy en código nuevo, todos `type-arg` o `no-any-return`:

- `persistence.py`:
  - línea 215: `event: dict` → `dict[str, Any]` (parameter type-arg)
  - línea 305: `cursor.fetchone()[0]` retorna `Any` desde `int` function → wrap con `int(...)` o variable tipada
- `polymarket.py` (17 errores, mismos patrones):
  - Returns REST tipados como `dict`/`list[dict]` bare (líneas 72, 86, 106, 128, 168, 187, 209, 294, 320) → parametrizar a `dict[str, Any]`/`list[dict[str, Any]]`
  - Línea 231: `queue: asyncio.Queue` → `asyncio.Queue[dict[str, Any]]`
  - `no-any-return` en 6 métodos (84, 104, 124, 166, 185, 205) por retour `resp.json()` que es `Any` → hacer cast o anotar el return type del método correctamente (no cualquier cosa adicional)

**Causa raíz**: los mock spec firmas decían `list[dict]` y `dict` directos — imprecisos. mypy strict pide `list[dict[str, Any]]` etc.

**Impacto**: bloquea acceptance criteria del spec línea 1222 ("mypy sin errores en código nuevo").

**Alternativas**:
- (A) Parametrizar annotations + cast en `int(...)` para persistence:305 — **Recomendada**: mínima superficie, mismo patrón que BL-001/BL-002 de Fase 1
- (B) Usar TypedDicts para responses REST — descartada: over-specification, Polymarket API responses son dicts dinámicos
- (C) `# type: ignore` en las 19 líneas — descartada: ensucia, no resuelve, solo valida tarde

**Nota sobre `no-any-return`**: Estos surgen porque `resp.json()` retorna `Any`. Al anotar el return type del método como `dict[str, Any]`, mypy sigue marcando el return porque el método declared `dict[str, Any]` pero recibe `Any`. Solución: `cast(dict[str, Any], resp.json())` o, más limpio, declarar `ReturnType` y usar `cast`.

## Documento Contrato

- **Archivos afectados**: 2
  1. `src/trady_ai/adapters/polymarket.py` (17 fixes)
  2. `src/trady_ai/core/persistence.py` (2 fixes)
- **Líneas afectadas** (mapping exacto):
  - polymarket.py: todas las firmas REST methods (9 signatures) + 1 Queue + 6 returns que requieren cast
  - persistence.py: línea 215 (dict→dict[str, Any]) y 305 (fetchone()[0]→int(...))
- **Qué se cambia**: annotations de tipos solamente. Cero lógica, cero runtime.
- **Qué NO se toca**: comportamiento de métodos, respuestas, validaciones.
- **Verification gate**:
  - mypy: `Success: no issues found in 28 source files` (de 19 → 0)
  - ruff: clean
  - pytest: 198 passed (sin regresión tras BL-010+011)
- **Riesgo**: 🟢 trivial — annotations + casts, misma familia que BL-001..002/006/007.

---

# Orden 4 — BL-014: gap-fill real + integration test

## Assessment Report

**Hallazgo**: `_handle_reconnect` (polymarket.py líneas 469-490) hoy hace:
```python
for mid in market_ids:
    try:
        data = self._adapter.get_market_data(mid)  # fetch CURRENT data
        self._capture_one(data)
    except httpx.HTTPStatusError:
        pass
```

**Design dice**: "REST fetch events since last timestamp" (líneas 411-423 del spec). Hoy solo pide el estado actual del mercado, no eventos históricos desde el `last_ts`.

**Espec Module 2 scenarios** (líneas 531-535): "Scenario: reconnect fills gap via REST — selects timestamp from seq=42, REST fetches events since that timestamp, gap events inserted via _capture_one, WS reconnected". El scenario BDD NO se puede escribir hoy porque la impl no hace eso.

**Test missing**: `test_reconnect_gap_fill` declarado en Testing Strategy línea 1182 del spec.

**Causa raíz**: el implementador simplificó "para que pase tests simples" sin implementar el gap fill histórico real. Probablemente 404 en el endpoint histórico lo desvió y optó por `get_market_data` como workaround.

**Limitación concreta honesta**: Polymarket CLOB API NO tiene un endpoint público documentado de "events since timestamp". El `get_market_data` retorna el snapshot actual. Un gap-fill real requeriría entweder:
- (A) Polling iterativo de `get_market_data` con timestamps simulados — workaround híbrido, no es gap-fill real pero es "lo más cercano" sin auth
- (B) Usar un endpoint histórico si existe (revisar Polymarket docs) — requiere investigación
- (C) Documentar como limitación conocida de Fase 2 + test el escenario actual (snapshot en reconnect, no gap fill histórico) — **Recomendada para Fase 2**

**Trade-off key**: si investigamos al (B) y el endpoint existe, hacemos el fix "de verdad". Si no, declaramos la limitación y ajustamos el scenario del spec/deviation.

**ESTE BL NECESITA INVESTIGACIÓN PREVIA** antes de saber cuánto trabajo es. Es el único BL donde la "solución" depende de información externa a la disposición inmediata.

**Alternativas**:
- (A) Investigar Polymarket CLOB API docs (via context7 o webfetch) para ver si hay endpoint histórico → implementar si existe, o declarar limitación + ajustar si no
- (B) Asumir limitación, ajustar dev spec, escribir test del comportamiento actual (snapshot, no gap fill histoire) → más rápido pero desconoce si existe el endpoint
- (C) Defer BL-014 a Fase 2.5 — descartada: deja WARNING pendiente en verify

## Documento Contrato

- **PASO 0 (investigación previa, antes de tocar código)**:
  - Consultar Polymarket CLOB API docs (webfetch https://docs.polymarket.com o context7) buscando endpoint "events since timestamp" o "historical market data"
  - Documentar el finding en una sección "BL-014 Research" del verify-report (amend)
  - Si existe endpoint: proceder con fix (A)
  - Si no existe: declarar limitación conocida Fase 2 + ajustar scenarios del design/spec con nota "snapshot-based reconnect for Phase 2, historical gap fill deferred to Phase 3+"

- **Archivos afectados** (depende del Paso 0):
  - Si (A): `src/trady_ai/adapters/polymarket.py` (`_handle_reconnect` reescrito) + `tests/integration/test_polymarket_integration.py` (nuevo test)
  - Si (B): `src/trady_ai/adapters/polymarket.py` (docstring aclarando limitación) + `openspec/changes/polymarket-integration/design.md` (deviation nota) + `tests/integration/test_polymarket_integration.py` (test del snapshot-reconnect actual)
- **Qué se cambia**: depende del Paso 0. Lo concreto se define post-investigación.
- **Qué NO se toca**: schema, EventCapture thread lifecycle, dedup logic.
- **Verification gate**:
  - mypy: clean
  - ruff: clean
  - pytest: 199 passed (1 integration test nuevo)
  - El scenario BDD "reconnect fills gap via REST" del spec debe tener un test que lo cubra (sea real-gap o snapshot-with-limitation-note)
- **Riesgo**: 🔴 requiere Paso 0 investigación + (potencial) reescritura de `_handle_reconnect` con nueva lógica de fetching histópiconal. Assessment conoce el riesgo; Documento Contrato se completa post-Paso 0.

---

# Orden 5 — BL-013: status command (UX ya decidida)

## Assessment Report

**Hallazgo**: `status` command (cli/main.py líneas 46-63) muestra Environment, Dry run, Log level, DB path, Event store count/max_seq, Active markets. Spec Module 7 (líneas 954-959) exige agregar:
- "Capture: running/stopped"
- "Execution mode: dry_run/live"

**Decisión usuario ya tomada**: capture state SIEMPRE "stopped" en Fase 2 (EventCapture efímero, no overengineering pidfile). Documentar como limitación en docstring.

**Causa raíz**: implementación partial del status command, quedó a medio completar.

**Impacto**: WARNING, no CRITICAL. Output incomplete vis-à-vis spec.

**Alternativas para "Execution mode"**:
- (A) `settings.get_runtime_config().execution_mode` — **Recomendada**: usa la API existente, RuntimeConfig ya tiene el campo (añadido en Fase 2)
- (B) Hardcodear "dry_run" porque run command siempre dry_run — descartada: crea tech-debt, peor cuando BL-016 se fixee

## Documento Contrato

- **Archivos afectados**: 1 (`src/trady_ai/cli/main.py`)
- **Líneas afectadas**: dentro de `status()` (líneas 46-63), agregar 2 echo lines. Actualizar docstring línea 47.
- **Qué se cambia**:
  - Docstring: añadir "Note: capture state siempre 'stopped' en Fase 2 — EventCapture es efímero (vive dentro del comando capture, no singleton). Fase 3+ con daemon/service trackeará real state."
  - Línea después de "Active markets": `click.echo(f"  Execution mode: {settings.get_runtime_config().execution_mode}")`
  - Mismo lugar: `click.echo("  Capture: stopped")` (hardcodeado + limitación documentada)
- **Qué NO se toca**: rest del status command, secrets output (sigue sin leakar), otros comandos.
- **Verification gate**:
  - mypy: clean
  - ruff: clean
  - pytest: sin regresión (puede que `test_cli.py::test_status` necesite assert de las nuevas líneas — ver si ya existe)
- **Riesgo**: 🟡 aplica post-approval (UX ya decidida por usuario).

---

# Orden 6 — BL-015: raw_payload NOT NULL (schema fix)

## Assessment Report

**Hallazgo**: `init_event_store` en persistence.py línea 197-212 define schema con `raw_payload TEXT` (nullable). Design dice `raw_payload TEXT NOT NULL` (línea 579 del spec).

**Implementación actual**: `append_event` línea 241 usa `event.get("raw_payload")` → puede insertar NULL.

**Caller en EventCapture._capture_one** (línea 461): SIEMPRE populates con `json.dumps(raw_event)`. Por eso no hay lockeages activos. Pero el schema es inmune a un caller futuro que se olvide.

**Causa raíz**: el schema SQL no refleja el design. El caller correcto no lo afecta hoy.

**Impacto**: schema deviation documentada en verify como WARNING. No data risk hoy; si caller futuro olvidara, insertaría NULL.

**Alternativas**:
- (A) Cambiar schema a `NOT NULL` + validar callers populan → **Recomendada**: schema correcto + caller ya cumple
- (B) Dejar nullable + documento → descartada: warning persiste en verify

**SUBTLE BUG potential**: cambiar el schema de una tabla existente requiere DROP + recreate, o ALTER TABLE. SQLite NO soporta ALTER COLUMN. Sin embargo:
- `init_event_store` usa `CREATE TABLE IF NOT EXISTS` → si la tabla existe, NO se re-crea con el nuevo schema.
- usuários con DBs existentes (dev, capture histórica) NO obtendrán el constraint hasta reset.

**Checks adicionales**:
- Existing DBs en dev: ¿hay datos que perder? No — solo constraint, no data.
- ¿Tests crean la tabla y persist? Sí (test_persistence_event_store.py) — verificar que usan `init_event_store` y no schema hardcoded.

## Documento Contrato

- **Archivos afectados**: 1 (`src/trady_ai/core/persistence.py`)
- **Líneas afectadas**: línea 208 (`raw_payload TEXT,` → `raw_payload TEXT NOT NULL,`)
- **Qué se cambia**:
  - Schema: añadir `NOT NULL` a raw_payload
  - `append_event`: cambiar `event.get("raw_payload")` → `event["raw_payload"]` (required key ahora)
  - Documentar en docstring de `append_event` que raw_payload es requerido
  - Verificar todos los callers de `append_event` populan raw_payload (EventCapture ya lo hace en línea 461)
- **Qué NO se toca**: schema de otras columnas, dedup logic, funciones de lectura.
- **Verification gate**:
  - mypy: clean
  - ruff: clean
  - pytest: sin regresión (si algún test no popula raw_payload, va a romper y hay que arreglarlo)
- **Migración**: para DBs existentes (dev):
  - Opción implícita: `reset_event_store()` (dev only) recrea con el nuevo schema
  - Sin acción manual necessaria para DBs nuevos
- **Riesgo**: 🟡 toca schema + callers. Caller ya cumple, así que fix es autocompletado.

---

# Orden 7 — BL-016 + BL-017: suggestions

## Assessment Report

### BL-016 — `run` hardcodea dry_run=True

**Hallazgo**: cli/main.py línea 177: `engine = ExecutionEngine(config, db, dry_run=True)`. Hardcodea True sin mirar `config.execution_mode`. En live mode, el engine correrá como dry_run siempre.

**Caller**: `run` command línea 159-191. Después de BL-010 ya valida `config.execution_mode` pre-ejecución. Después de BL-016 debería respetarlo.

**Fix**: `dry_run=(config.execution_mode == "dry_run")`. Una línea.

### BL-017 — WS retry demasiado amplio

**Hallazgo**: polymarket.py línea 421: `except Exception as e:` captura todo. Design decía `(ConnectionError, httpx.RemoteProtocolError)` (línea 366 del spec).

**Riesgo actual**: silencia errores no-retry (`ValueError`, bugs internos, `KeyboardInterrupt`). Un `bug` en `_capture_one` dispararía reconnect infinito en vez de fallar.

**Fix**: cambiar `except Exception` → `except (ConnectionError, httpx.RemoteProtocolError, asyncio.TimeoutError)`. Añadir test de que errores no-retry propaguen.

## Documento Contrato

- **Archivos afectados**: 2
  1. `src/trady_ai/cli/main.py` (línea 177 — BL-016)
  2. `src/trady_ai/adapters/polymarket.py` (línea 421 — BL-017)
- **Líneas afectadas**:
  - cli/main.py línea 177: `dry_run=True` → `dry_run=(config.execution_mode == "dry_run")`
  - polymarket.py línea 421: `except Exception as e:` → `except (ConnectionError, httpx.RemoteProtocolError, asyncio.TimeoutError) as e:`
- **Qué se cambia**: 2 líneas exactamente.
- **Qué NO se toca**: comportamiento de run para dry_run (idéntico), lógica de reconnect.
- **Verification gate**:
  - mypy: clean
  - ruff: clean
  - pytest: sin regresión. (Opcional: 1 test nuevo que verify que un ValueError dentro del _run_loop se propague y no reintente — si se rompe algo, los tests van a gritar.)
- **Riesgo**: 🟢 trivial (1 línea c/u) + 🟡 requiere check que tests existentes no dependen de `except Exception` para perdonar bugs. A verificación post-edit.

---

# Resumen ejecutivo para aprobación

| Orden | BL | Tipo | Archivos | Riesgo | Lo esencial |
|-------|-----|------|----------|--------|--------------|
| 1 | BL-012 | doc edit | 1 | 🟢 | Editar apply-progress (corregir "mypy: 0 new" + agregar desvíos) |
| 2 | BL-010 + BL-011 | bug + tests | 3 (1 nuevo) | 🟡 | Mover validate a security/polymarket.py, invocar desde capture+run, +3 tests |
| 3 | BL-009 | deuda | 2 | 🟢 | Parametrizar dict/list/Queue en 19 lugares + cast int en persistence:305 |
| 4 | BL-014 | deuda + test | 1-2 + test | 🔴 | Investigar Polymarket API primero → implementar gap-fill o declarar limitación |
| 5 | BL-013 | deuda | 1 | 🟡 | Agregar 2 echo lines a status + docstring |
| 6 | BL-015 | deuda | 1 | 🟡 | Schema raw_payload NOT NULL + append_event required |
| 7 | BL-016 + BL-017 | deuda | 2 | 🟢 | 2 lines: dry_run desde config + except más granular |

**Decisión que necesito de vos para BL-014**: ¿avanzo con Paso 0 (investigar Polymarket API docs via webfetch/context7) antes de tocar código? Es el único BL donde la solución depende de información externa.

**Total archivos a tocar**: 7 únicos
- `openspec/changes/polymarket-integration/apply-progress.md` (BL-012)
- `src/trady_ai/security/polymarket.py` NUEVO (BL-010)
- `src/trady_ai/cli/main.py` (BL-010, BL-013, BL-016)
- `tests/unit/test_security_polymarket.py` NUEVO (BL-011)
- `src/trady_ai/adapters/polymarket.py` (BL-009, BL-014, BL-017)
- `src/trady_ai/core/persistence.py` (BL-009, BL-015)
- `tests/integration/test_polymarket_integration.py` (BL-014)

**Total.assertTrue**: archivos nuevos (security + 1 test) +Editar 5 existentes. Cero cambios arquitectural; todo preserva los contracts del spec.

---

## Checklist post-aprobación (mi plan de ejecución)

Una vez que apruebes, voy en orden estricto:

1. BL-012 (doc edit) → corregir apply-progress → amend WIP
2. BL-010+011 (move + invoke + tests) → amend WIP
3. BL-009 (annotations) → amend WIP
4. BL-014 (Paso 0: investigar Polymarket API) → documentar finding → implementar o declarar limitación → amend WIP
5. BL-013 (status lines) → amend WIP
6. BL-015 (schema NOT NULL + callers) → amend WIP
7. BL-016+017 (2 trivial edits) → amend WIP
8. Verify #2 (sub-agent fresh, contra nuevo hash WIP) — si verde, archive path
9. Enmamor最后的 pause — te presento verify-report #2 para aprobación pre-archive

En cada amend del WIP incluyo `assessment: trivial — <razón>` o referencia al Assessment aprobado, según protocolo.

---

**Esperando tu aprobación para iniciar BL-012 o feedback para ajustar.**