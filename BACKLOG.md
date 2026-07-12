# BACKLOG — TRADY.AI

> Generado desde BACKLOG-PROTOCOL v1
> Auditoría inicial: 2026-07-09
> Última actualización: 2026-07-11 (BL-018 agregado post Verify Fase 3)

---

## Fase 1 — Deterministic Core (RESUELTO)

[BL-001] | deuda | media | models.py | `__init__` en Signal, Position, Trade sin type annotations (3 ocurrencias) | ✅ resuelto
[BL-002] | deuda | media | engine.py, observability.py, risk.py | Tipos genéricos sin argumentos: `list`, `dict` sin parámetros de tipo (7 ocurrencias) | ✅ resuelto
[BL-003] | deuda | media | markov_strategy.py, position_manager.py, engine.py | Llamadas a constructores no tipados (Signal, Position, Trade, PositionManager) que mypy no puede verificar (7 ocurrencias) | ✅ resuelto (desbloqueado por BL-001)
[BL-004] | deuda | alta | persistence.py | `sqlite_utils.Database.__getitem__` retorna `Table | View`, mypy no reconoce `.insert()` en tipos unión (5 ocurrencias) | ✅ resuelto (# type: ignore[union-attr])
[BL-005] | bug | alta | state.py, risk.py | Argumento `str` pasado donde se espera `Literal['UP','DOWN','NEUTRAL']` (state.py:50) y `Literal['OPEN_LONG','OPEN_SHORT','CLOSE','HOLD','REJECT']` (risk.py:109) | ✅ resuelto (cast explícito)
[BL-006] | deuda | alta | observability.py | Operaciones no seguras con `Decimal | None`: suma, comparación, conversión a `float` sin manejar el caso `None` (4 errores) | ✅ resuelto (filtro + type narrowing)
[BL-007] | deuda | baja | position_manager.py | `__init__` sin return type annotation (línea 16) | ✅ resuelto
[BL-008] | deuda | baja | replay.py | Errores colaterales de BL-002: variables de loop `a/b` reusadas entre tipos incompatibles (6 ocurrencias) | ✅ resuelto (renombrado a dec_a/dec_b, sig_a/sig_b, trd_a/trd_b)

---

## Fase 2 — Polymarket Integration (Verify #1 hallazgos)

> Fuente: `openspec/changes/polymarket-integration/verify-report.md` (commit `eee2999`)
> Veredicto verify #1: FAIL — 4 CRITICAL, 5 WARNING, 3 SUGGESTION
> Triage completado: BL-009..017 fixeados y validados (commit `73990ea`)

### Orden 1: BL-012 (corregir apply-progress — nunca más green falso)

[BL-012] | deuda | alta | openspec/changes/polymarket-integration/apply-progress.md | apply-progress línea 6 afirma "mypy: 0 new" — FALSO (hay 19). "Deviations from Design: None" — FALSO (raw_payload nullable + gap-fill simplificado). | ✅ resuelto (corregido a 19 errors + 2 desvíos documentados)

### Orden 2: BL-010 + BL-011 (validate + tests — unidad conectada)

[BL-010] | bug | alta | cli/main.py, security/polymarket.py (nuevo) | `validate_polymarket_secrets()` definida cli/main.py línea 9 pero NUNCA INVOCADA desde `capture` ni `run`. Spec Module 9 requiere validación pre-ejecución. | ✅ resuelto (movida a security/polymarket.py, renombrada validate_execution_secrets, invocada en capture+run)

[BL-011] | deuda | alta | tests/unit/test_security_polymarket.py (nuevo) | `validate_execution_secrets` sin tests. Cero coverage. | ✅ resuelto (3 tests: dry_run no-op, live missing raises, live complete pasa)

### Orden 3: BL-009 (mypy 19 errors — el denso)

[BL-009] | deuda | alta | adapters/polymarket.py, core/persistence.py | mypy: 19 errores `type-arg`/`no-any-return` en código nuevo (17 en polymarket + 2 en persistence). | ✅ resuelto (19 annotations: dict→dict[str,Any], Queue→Queue[...], cast en returns)

### Orden 4: BL-014 (gap-fill real + integration test)

[BL-014] | deuda | media | adapters/polymarket.py (`_handle_reconnect`), tests/integration/test_polymarket_integration.py | `_handle_reconnect` simplificado: fetch current, no gap-fill histórico. Test missing. | ✅ resuelto (investigación Polymarket API: no existe endpoint histórico. Limitación documentada en docstring. test_reconnect_snapshot_fill agregado)

### Orden 5: BL-013 (status command)

[BL-013] | deuda | media | cli/main.py (status command) | `status` falta "Capture: running/stopped" y "Execution mode: dry_run/live" (spec Module 7). | ✅ resuelto (agregadas 2 echo lines + docstring con limitación "always stopped" Fase 2)

### Orden 6: BL-015 (raw_payload NOT NULL)

[BL-015] | deuda | media | core/persistence.py (schema) | `raw_payload TEXT` (nullable) vs design `TEXT NOT NULL`. | ✅ resuelto (schema NOT NULL + append_event event["raw_payload"] required + callers actualizados)

### Orden 7: BL-016 + BL-017 (suggestions cleanup)

[BL-016] | deuda | baja | cli/main.py (run command) | `run` hardcodea `dry_run=True` ignorando `config.execution_mode`. | ✅ resuelto (dry_run=(config.execution_mode == "dry_run"))

[BL-017] | deuda | baja | adapters/polymarket.py (`_run_loop`) | WS retry usa broad `except Exception` — silencia errores no-retry. | ✅ resuelto (except granular: ConnectionError, httpx.RemoteProtocolError, TimeoutError)

---

## Hallazgo adicional (no BL — bug preexistente)

Se detectó un bug preexistente durante el triage: `init_db` en `db/database.py` creaba la conexión SQLite sin `check_same_thread=False`, pero EventCapture (que corre en un daemon thread) usa esa misma DB. Esto causaba `RuntimeError: SQLite objects created in a thread can only be used in that same thread`. Fix aplicado: `sqlite3.connect(path, check_same_thread=False)` envuelto en `sqlite_utils.Database(conn)`. Tests de EventCapture que fallaban por esto ahora pasan.

---

## Resumen Fase 2

| Métrica | Verify #1 (pre-fix) | Post-triage (commit `73990ea`) |
|---------|---------------------|-------------------------------|
| mypy | 19 errores | 0 errores (29 source files) |
| ruff | clean | clean |
| pytest | 195 passed | 199 passed |
| coverage | 89% | 91% |
| BLs resueltos | 0/9 | 9/9 (BL-009..017) |
| Hallazgos adicionales | — | 1 (SQLite threading, fixeado) |
| Veredicto | FAIL | Pendiente Verify #2 |

---

## Fase 3 — Strategy Infrastructure (Verify hallazgo)

> Fuente: `openspec/changes/fase-3-strategy-infrastructure/verify-report.md`
> Veredicto verify: PASS — 0 CRITICAL, 0 WARNING, 1 SUGGESTION
> La SUGGESTION no constituye incumplimiento de los criterios de aceptación de la Fase 3, pero sí una deuda arquitectónica respecto al contrato ideal de un Strategy Snapshot. Dado su impacto funcional prácticamente nulo y el costo de evolucionar el schema, se difiere deliberadamente para una futura evolución del persistence layer.

[BL-018] | deuda | baja | strategies/markov/persistence.py, core/persistence.py | `_last_state` no se persiste en `strategy_snapshots` — la primera transición post-restore no se registra (1 data point perdido por ciclo). `restore()` explícitamente setea `_last_state = None`. `evaluate()` no se ve afectado (solo usa `_transition_counts`). El contrato arquitectónico ideal del snapshot exige resumability total (estado indistinguible del pre-snapshot), lo cual requiere `_last_state`. Fix diferido: requiere agregar columna `last_state TEXT` al schema + tests de roundtrip con transiciones. | abierto

---

## 🧠 NOTAS

- **Estado Fase 1**: ✅ Limpia. mypy: 0 errores. pytest: 117 pass. Coverage: 97%.
- **Estado Fase 2**: Todas las fixes aplicadas y validadas localmente. Pendiente Verify #2 contra commit `73990ea`.
- **Próximo paso**: Verify #2 (sub-agent fresh) contra HEAD `73990ea`. Si verde → archive → squash → push.
- **Lecciones aprendidas**:
  - Cambios con riesgo de impacto colateral requieren Assessment Report + Documento Contrato antes de aplicar.
  - Cambios triviales (renombres locales, annotations) pueden aplicarse directo con nota en commit.
  - Verify es fresh-context adversarial review: no confiar en claims del apply-progress sin re-verificar.
  - apply-progress puede afirmar "green" algo que está rojo — verify atrapa esto como CRITICAL.
  - Commit local WIP (no pusheado) + squash en archive: snapshot reproducible para verify + backup del trabajo + history remoto limpio (cf. PORTABLE OS/SDD-CYCLE-GOVERNANCE.md).
  - BL-015 (schema NOT NULL) puede romper tests que no populan el campo requerido — verificar todos los callers de append_event.
  - SQLite + threads: `check_same_thread=False` necesario cuando EventCapture (daemon thread) accede la DB creada en thread principal.
  - BL-014: Polymarket CLOB API no tiene endpoint histórico de eventos individuales — `/prices-history` devuelve datos agregados (OHLC-like), no eventos. WS no tiene resumption protocol. Limitación documentada.
- **Decisiones del usuario**:
  - BL-013: capture state siempre "stopped" en Fase 2 (EventCapture efímero, no overengineering con pidfile). Documentar como limitación.
  - Orden de ejecución ajustado: BL-010+011 antes que BL-009 (destraba validación antes de meterse en mypy denso).
  - BL-014: investigar Polymarket API antes de implementar (Option A). Resultado: no existe endpoint histórico → declarar limitación.