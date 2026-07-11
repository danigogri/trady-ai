# Archive: 003 — Polymarket Integration (Fase 2)

## Fecha de cierre
2026-07-10

## Resumen ejecutivo

Integración completa de Polymarket CLOB API en Trady.AI: WebSocket capture de eventos de mercado en tiempo real, almacenamiento append-only en event_store (SQLite), replay determinístico vía `run_from_store()`, y CLI commands (`capture`/`run`/`status`). La integración respeta la arquitectura de 6 capas (Governance > Intelligence > Reflection > Core > Adapters > Platforms) y el principio de que el Core determinístico NO depende de adapters (RFC-002).

El cambio se implementó como 4 PRs encadenados (stacked-to-main) de ~290-390 líneas cada uno, total ~1,386 líneas. Verificación final: 199 tests, 91% coverage, 0 errores mypy + ruff.

## Artifacts archivados

| Artifact | Archivo en archive | Source original |
|----------|-------------------|----------------|
| **Proposal** | `proposal.md` | `openspec/specs/003-polymarket-integration-proposal.md` |
| **Spec** | `spec.md` | `openspec/specs/003-polymarket-integration-spec.md` |
| **Design** | `design.md` | `openspec/changes/polymarket-integration/design.md` |
| **Tasks** | `tasks.md` | `openspec/changes/polymarket-integration/tasks.md` |
| **Apply Progress** | `apply-progress.md` | `openspec/changes/polymarket-integration/apply-progress.md` |
| **Verify Report #1** | `verify-report.md` | `openspec/changes/polymarket-integration/verify-report.md` |
| **Verify Report #2** | `verify-report-2.md` | `openspec/changes/polymarket-integration/verify-report-2.md` |
| **Archive Report** | `archive-report.md` | *(current)* |

## Estado final de verificación

### Métricas (Verify #2 — 2026-07-10)

| Métrica | Resultado | Threshold |
|---------|-----------|-----------|
| Tests | 199/199 pass | ≥ 80% coverage |
| Coverage | 91% | ≥ 80% |
| ruff | 0 errores | 0 |
| mypy | 0 errores (29 source files) | 0 |
| Criterios de aceptación spec | 28/29 COMPLIANT, 1/29 PARTIAL | 29/29 |
| Verify #1 findings resueltos | 12/12 | 12/12 |
| Tasks completadas | 14/14 | 14/14 |

### Cobertura por módulo

| Módulo | Statements | Coverage |
|--------|-----------|----------|
| `adapters/polymarket.py` | 203 | 84% |
| `cli/main.py` | 138 | 81% |
| `core/engine.py` | 63 | 95% |
| `core/persistence.py` | 51 | 96% |
| `security/polymarket.py` | 16 | 100% |
| `security/secrets.py` | 18 | 100% |
| Otros (Fase 1 + placeholders) | — | ≥ 80% |
| **Total** | **892** | **91%** |

### Criterios de aceptación

| # | Criterio | Resultado |
|---|----------|-----------|
| 1 | Mismo evento → mismo registro en event_store (reproducible) | ✅ |
| 2 | Dedup: event_id duplicado → UNIQUE constraint, retorna None | ✅ |
| 3 | WS reconexión: REST gap fill desde último timestamp | ⚠️ PARTIAL (API limitation) |
| 4 | dry_run: pipeline corre sin firmar, secrets vacíos OK | ✅ |
| 5 | N mercados configurables sin tocar código | ✅ |
| 6-21 | Spec requirements (16 items) | 16/16 ✅ |
| 22-29 | Architectural invariants (8 items) | 8/8 ✅ |

### Verify #1 Resolution (12/12 findings)

| # | Finding | Severidad | BL | Resultado |
|---|---------|-----------|----|-----------|
| 1 | mypy: 19 errors en código nuevo | CRITICAL | BL-009 | ✅ RESUELTO — 0 errors |
| 2 | apply-progress.md claim falso de mypy | CRITICAL | BL-012 | ✅ RESUELTO |
| 3 | validate_polymarket_secrets() definida pero NO LLAMADA | CRITICAL | BL-010 | ✅ RESUELTO |
| 4 | Sin tests para validate_polymarket_secrets | CRITICAL | BL-011 | ✅ RESUELTO |
| 5 | Status command incompleto | WARNING | BL-013 | ✅ RESUELTO |
| 6 | Naming/placement de validate_secrets | WARNING | BL-010 | ✅ RESUELTO (Option C) |
| 7 | Integration test reconnect_gap_fill faltante | WARNING | BL-014 | ✅ RESUELTO |
| 8 | REST gap fill simplificado | WARNING | BL-014 | ✅ RESUELTO (API limitation) |
| 9 | raw_payload nullable vs NOT NULL | WARNING | BL-015 | ✅ RESUELTO |
| 10 | append_event usa raw SQL vs sqlite_utils | SUGGESTION | — | ✅ RESUELTO (intentional deviation) |
| 11 | run command hardcodes dry_run=True | SUGGESTION | BL-016 | ✅ RESUELTO |
| 12 | WS retry usa broad except Exception | SUGGESTION | BL-017 | ✅ RESUELTO |

## Archivos modificados/creados

| Archivo | Acción | Líneas |
|---------|--------|--------|
| `src/trady_ai/adapters/polymarket.py` | Crear | ~346 (PolymarketAdapter + EventCapture) |
| `src/trady_ai/adapters/__init__.py` | Crear | — |
| `src/trady_ai/core/persistence.py` | Modificar | +51 (event_store + 6 funciones) |
| `src/trady_ai/core/engine.py` | Modificar | +run_from_store() |
| `src/trady_ai/config/settings.py` | Modificar | +6 campos Polymarket |
| `src/trady_ai/config/runtime_config.py` | Modificar | +execution_mode, default_order_type |
| `src/trady_ai/security/polymarket.py` | Crear | +16 (validate_execution_secrets) |
| `src/trady_ai/cli/main.py` | Modificar | +capture command, run/status extendidos |
| `pyproject.toml` | Modificar | +websockets>=13.0 |
| `tests/unit/test_adapter.py` | Crear | Tests PolymarketAdapter |
| `tests/unit/test_capture.py` | Crear | Tests EventCapture |
| `tests/unit/test_persistence_event_store.py` | Crear | Tests event_store persistence |
| `tests/unit/test_config_polymarket.py` | Crear | Tests config |
| `tests/unit/test_engine.py` | Modificar | +run_from_store tests |
| `tests/unit/test_security_polymarket.py` | Crear | Tests validate_execution_secrets |
| `tests/integration/test_polymarket_integration.py` | Crear | Pipeline + dedup + determinism |

## Decisiones arquitectónicas clave

| Decisión | Opciones | Elegida | Rationale |
|----------|----------|---------|-----------|
| WS library | websockets / websocket-client / raw asyncio | `websockets` | Pure async, bien tipado, mismo patrón que httpx |
| HTTPX mode | AsyncClient / Sync + asyncio.run | **Sync REST + async WS** | REST desde core sync. WS en thread propio con asyncio.run |
| WS thread model | threading.Thread / asyncio loop puro | **threading.Thread** | Core 100% sync. Async aislado en thread boundary |
| Dedup strategy | INSERT OR IGNORE / ON CONFLICT DO NOTHING | **INSERT OR IGNORE** | sqlite_utils idiom, mismo SQL semantics |
| raw_payload | TEXT (nullable) / TEXT NOT NULL | **TEXT NOT NULL** (BL-015) | Preserva payload original. Forward-compatible |
| Reconnect cursor | MAX(seq) / MAX(timestamp) | **MAX(seq) → timestamp** | seq es monotónico, determinístico. timestamp depende de clock externo |
| validate_secrets | Modificar security/secrets.py / Nueva función en nuevo módulo | **Option C: security/polymarket.py** | Phase 1 contract preservado (Option C) |

## Decisiones de implementación (deviations justificadas)

| Desviación | Especificación | Implementación | Justificación |
|------------|---------------|----------------|---------------|
| REST gap fill | Fetch histórico desde timestamp | Current snapshot `get_market_data()` | Polymarket CLOB API no tiene endpoint histórico de eventos. Documentado en docstring de `_handle_reconnect` |
| append_event vía raw SQL | Design muestra `db["event_store"].insert(...)` | `cursor.execute("INSERT OR IGNORE ...")` | Ambas aproximaciones funcionan idénticamente. Raw SQL da control explícito sobre UNIQUE constraint |

## Estado deuda técnica

| Ítem | Prioridad | Esfuerzo | Notas |
|------|-----------|----------|-------|
| Gap fill histórico | Baja | Alto | Polymarket API no ofrece endpoint histórico. Limitation documentada |
| CI pipeline | Alta | Medio | Sin CI, la verificación depende de ejecución local |
| Lock file | Media | Bajo | Generar con `uv lock` o `pip freeze` |
| Coverage threshold en CI | Media | Bajo | Configurar `--cov-fail-under=80` |

## Lecciones aprendidas

1. **BL-009..017 como workflow**: El ciclo Verify #1 → triage → BLs → Verify #2 demostró que el proceso de backlog items para hallazgos post-verificación es efectivo. 12/12 findings resueltos en una iteración.

2. **Option C para preservar contratos de Fase 1**: Decidir no modificar `security/secrets.py` (Phase 1 contract) y crear `security/polymarket.py` para la nueva funcionalidad evitó regresiones y mantuvo la isolation entre fases.

3. **Delta specs ausentes en change folder**: Los artifacts de spec y proposal se colocaron directamente en `openspec/specs/` en lugar de `openspec/changes/polymarket-integration/specs/`. Para cambios futuros, seguir la convención openspec: delta specs en `openspec/changes/{change-name}/specs/{domain}/spec.md`.

4. **API limitations documentadas**: La falta de endpoint histórico en Polymarket CLOB API es una limitación real, no un bug. Documentada en reconnect docstring y en verify report como PARTIAL aceptado.

## Próximos pasos (orquestador)

1. **Squash WIP commit** (`478c84f`) en un commit limpio con mensaje convencional (`feat:`)
2. **Push desde PowerShell** (gh auth limitation en WSL)
3. **Crear PR** en GitHub con el diff completo
4. **Cerrar BL-009..017** en BACKLOG.md como resueltos

## Veredicto

**APROBADO — ARCHIVADO** ✅

El cambio "003 — Polymarket Integration (Fase 2)" está completo, verificado y archivado:

- 14/14 tareas implementadas ✅
- 199/199 tests pasan (199 > 195 baseline) ✅
- 91% coverage (≥ 80% threshold) ✅
- 0 errores mypy + ruff ✅
- 28/29 criterios de aceptación COMPLIANT, 1/29 PARTIAL (API limitation documentada) ✅
- 12/12 Verify #1 findings resueltos ✅
- Option C contract preservado (validate_secrets unchanged) ✅
- Sin regresiones en Fase 1 ✅

La integración con Polymarket está lista para operación dry_run. Para live execution, solo se necesita configurar secrets y cambiar `execution_mode` a `"live"`. Stack listo para Fase 3+ (Multi-Platform).
