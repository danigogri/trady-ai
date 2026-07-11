## Resumen

Implementación completa de Fase 2 — Polymarket Integration para Trady.AI.

Adapter stateless + EventCapture + event_store append-only + CLI commands. El core pipeline determinístico NO cambia (boundary RFC-002 preservada). `run_from_store()` delega a `run()` sin modificar el pipeline existente.

## SDD Cycle completo

| Fase | Veredicto | Detalle |
|------|-----------|---------|
| Spec | ✅ Aprobado | 9 módulos, 46 escenarios BDD, 37 tests planificados |
| Design | ✅ Aprobado | 12 decisiones arquitectónicas (Option C: validate_secrets preservado) |
| Tasks | ✅ Aprobado | 14 tareas en 4 work units (stacked-to-main) |
| Apply | ✅ Implementado | 199 tests passing |
| Verify #1 | ❌ FAIL | 4 CRITICAL, 5 WARNING, 3 SUGGESTION |
| Triage | ✅ 9 BLs fixeados | BL-009..017 + 1 bug preexistente (SQLite threading) |
| Verify #2 | ✅ PASS | 12/12 resolved, 0 new findings |
| Archive | ✅ Archivado | `openspec/changes/archive/2026-07-10-polymarket-integration/` |

## Módulos implementados

| Módulo | Archivo | Descripción |
|--------|---------|-------------|
| PolymarketAdapter | `adapters/polymarket.py` | Stateless: 6 REST methods, 1 WS generator, 2 pure mappers |
| EventCapture | `adapters/polymarket.py` | Stateful: thread lifecycle, dedup, reconnect, error property |
| Event Store | `core/persistence.py` | Append-only: 6 funciones, seq-based ordering, INSERT OR IGNORE |
| Engine | `core/engine.py` | `run_from_store(since_seq)` → delegates to `run()` |
| Config | `config/settings.py`, `config/runtime_config.py` | 6 Polymarket fields, execution_mode, default_order_type |
| CLI | `cli/main.py` | `capture` (WS), `run` (from store), `status` (event store stats) |
| Security | `security/polymarket.py` | `validate_execution_secrets` (Option C, existing `validate_secrets` unchanged) |

## Verification gates

| Gate | Resultado |
|------|-----------|
| `mypy src/` | `Success: no issues found in 29 source files` |
| `ruff check src/ tests/` | `All checks passed!` |
| `pytest` | `199 passed` |
| Coverage | `91%` |

## Do-not-change respetado

- [x] No se modificó `security/secrets.py` `validate_secrets()` (Phase 1 contract, Option C)
- [x] No se modificó `openspec/specs/003-polymarket-integration-spec.md` (modificación preexistente excluida)
- [x] No se modificaron tests existentes de Fase 1
- [x] No se cambió `pyproject.toml` config (solo +websockets>=13.0 dependency)
- [x] No se renombraron funciones, clases o módulos existentes

## Limitaciones conocidas

1. **Polymarket CLOB API no tiene endpoint histórico de eventos individuales.** Reconnect usa snapshot actual (`get_market_data`), no gap-fill real. Fase 3+ investigará indexing on-chain (OrderFilled events en Polygon).
2. **Capture state siempre "stopped" desde CLI.** EventCapture es efímero (vive dentro del comando `capture`, no es singleton). Fase 3+ con daemon/service trackeará real state.

## Triage post Verify #1

9 items de backlog (BL-009..017) + 1 bug preexistente resueltos:

| BL | Fix |
|----|-----|
| BL-009 | 19 annotations mypy (dict→dict[str,Any], Queue→Queue[...], cast en returns) |
| BL-010 | validate_execution_secrets movida a security/polymarket.py, invocada en capture+run |
| BL-011 | 3 tests para validate_execution_secrets |
| BL-012 | apply-progress corregido (mypy "0 new"→"19 errors", deviations documentados) |
| BL-013 | status command: execution mode + capture state |
| BL-014 | _handle_reconnect docstring limitación + test_reconnect_snapshot_fill |
| BL-015 | raw_payload NOT NULL en schema + callers actualizados |
| BL-016 | dry_run desde config.execution_mode |
| BL-017 | except granular en _run_loop |
| Extra | SQLite check_same_thread=False (bug preexistente para EventCapture threaded) |

## Artifacts archivados

`openspec/changes/archive/2026-07-10-polymarket-integration/` — 8 archivos:
proposal.md, spec.md, design.md, tasks.md, apply-progress.md, verify-report.md, verify-report-2.md, archive-report.md