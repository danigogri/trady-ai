# BACKLOG — TRADY.AI

> Generado desde BACKLOG-PROTOCOL v1
> Auditoría inicial: 2026-07-09
> Última actualización: 2026-07-22 (BL-027, BL-028, BL-029 — Portable OS compliance hallazgos; BL-029 cerrado con 29 tests; BL-030 — bundle path duplicado post-dry-run; BL-031 — 8 tests de integración preexistentes rotos)

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

## Roadmap / Operational Sequencing

> Fuente: Análisis arquitectónico post-Fase 3 — secuencia Fase 4 vs. Paper Trading.
> Decisión tomada: 2026-07-11. Fundamento: RFC-000, RFC-002, RFC-004, MASTER-ROADMAP-001.

[BL-019] | decisión | alta | roadmap, RFC-004, Fase 2 dry_run | **Paper Trading Validation Period debe ocurrir DESPUÉS de completar Fase 4 (Reflection Systems).** La iteración `dry_run` de Fase 2 (capture real + pipeline sin firmar) existe, pero sin Fase 4 la evaluación de decisiones vs. outcomes reales sería manual, no reproducible, y no auditable — violando RFC-000 Auditability Doctrine (línea 363-381) y RFC-004 Proposal Doctrine (línea 161-170). Secuencia correcta: Fase 4 SDD completo → Paper Trading con Reflection desde día uno → Governance Review basado en evidencia determinística → autorización (o no) de `execution_mode=live`. Evitar tooling temporal que se descarte. | cerrado

[BL-020] | deuda | baja | paper-trading, contracts | **`dry_run_enforced("dry_run")` no llama a `validate_execution_secrets()`.** La implementación actual usa string comparison directo en `contracts.py:37` en vez de delegar a `security/polymarket.py:16`. Son funcionalmente equivalentes porque `validate_execution_secrets()` con `execution_mode="dry_run"` es un no-op (`return` inmediato en línea 29-30). El safety net real está en `ExecutionEngine(dry_run=True)` hardcodeado en `session.py:352`. La spec (REQ-PT-002, línea 37) referencia `validate_execution_secrets()` como mecanismo de validación, creando una discrepancia documental. Sin impacto operacional — corregir solo si cambia el contrato de seguridad o si se reutiliza `dry_run_enforced()` en modo live. | abierto

[BL-021] | deuda | baja | paper-trading, session | **`_compute_day()` usa `COUNT(*)` en vez de `COUNT(DISTINCT DATE())`.** La query en `session.py:380` cuenta filas totales de `reflection_reports` en vez de días distintos. `temporal_integrity()` (`contracts.py:88`) previene sesiones duplicadas por día usando `datetime.now(UTC)`, así que en operación normal ambas queries son equivalentes. Impacto cosmético: si existieran múltiples reports el mismo día (por inserción manual o scope distinto), los directorios de bundle saltarían números (`dia-007/`, `dia-009/`). No afecta evidencia, replayabilidad, calibración, ni governance. Corregir si `temporal_integrity()` se relaja en el futuro. | abierto

[BL-022] | deuda | baja | paper-trading, bundler | **`_count_today_events(day)` y `_count_today_trades(day)` ignoran el parámetro `day`.** `bundler.py:142-157` cuenta todos los eventos/trades sin filtrar por día. Limitación del schema actual: `event_store` no tiene columna `session_day`. El `session.py` `_count_events()` tiene el mismo comportamiento (cuenta total), así que el bundle regenerado es consistente con el original. Impacto: solo cosmético en `session_report.json` regenerado. No afecta Reflection, Calibration, ni Governance. Revisar post-Paper Trading cuando se agregue columna `session_day` al schema. | abierto

[BL-023] | deuda | media | core, persistence | **`get_events()` límite por defecto aumentado a 2000 pero sin paginación real.** `persistence.py:391` tenía `limit=100` — insuficiente para mercados activos (>100 eventos/día). Aumentado a 2000 como mejora operacional para Paper Trading. El docstring de `engine.py:153` documentaba esto como limitación de Fase 2 con plan de resolver en Fase 6+ (cursor-based streaming con batch_size configurable). Revisar post-Paper Trading si 2000 es suficiente o si se necesita paginación real. | abierto

[BL-024] | deuda | media | paper-trading, contracts, session | **`last_processed_seq` usa `execution_log.tick_number` como proxy en vez de una columna dedicada.** `contracts.py:100-104` y `session.py:257-260` consultan `MAX(tick_number)` de `execution_log` para trackear el progreso del Decision Clock. `tick_number` es monotónicamente creciente y se correlaciona con eventos procesados — funcional para los 30 días de Paper Trading. Para Phase 6+, agregar columna `last_processed_seq` dedicada en la tabla `trades` o una tabla `clock_state` separada. | abierto

[BL-025] | deuda | baja | tests | **Ruff N806 — `MockCapture` naming convention (10 instancias en 4 archivos).** `with patch(...) as MockCapture` usa PascalCase en vez de `mock_capture` (snake_case). Archivos: `test_paper_trading_session.py`, `test_reconstruction.py`, `test_subdaily_execution.py`. No bloquea — naming convention lint. | abierto

[BL-026] | deuda | baja | tests, scripts | **Ruff import hygiene — unsorted imports (I001), unused imports (F401), unused variable (F841). 13 instancias, 12 auto-fixable.** Archivos: `ensure_active_market.py`, `test_guard.py`, `test_reconstruction.py`, `test_subdaily_execution.py`, `test_cli.py`, `test_paper_trading_session.py`. `ruff check --fix` resuelve 12/13. | abierto

---

## Fase 5 — Paper Trading Deployment (Compliance hallazgos)

> Fuente: Portable OS compliance review del `scripts/ensure_active_market.py` modificado el 2026-07-22 (deployed durante Phase 1 de deployment a AWS Lightsail). Veredicto: script técnicamente sólido, pero violó proceso del framework (BACKLOG-PROTOCOL §3/§7/§10, Architecture Contract §27, Operations Manual §6 Discovery Protocol). Ver detalle en `paper_trading/SESSION-2026-07-22.md` y `paper_trading/MARKET-DISCOVERY-FIX.md`.

### Orden 1: BL-027 (deuda P0 — deviation del contract)

[BL-027] | deuda | alta | scripts/ensure_active_market.py | **Deviation from frozen Architecture Contract OC-2.** Implementado 2026-07-22 como hotfix: el discovery mechanism usa HTML scraping (`polymarket.com/sports/{league}/games`) + `gamma-api/events?slug={slug}` + `clob.polymarket.com/markets/{conditionId}` en vez del flow documentado en OC-2 (single `clob/markets` con filter de tags). Eligibility rules cambiaron de "tags contains `football` AND `winner`" a regex sobre question field (`^Will .+ win on YYYY-MM-DD?$`). Documentado en 3 lugares (docstring del script, `paper_trading/SESSION-2026-07-22.md`, `paper_trading/MARKET-DISCOVERY-FIX.md`) pero NO siguió el proceso: sin contract amendment, sin SDD cycle, sin verify-report (mypy/ruff/pytest), sin governance review (Operations Manual §6 Discovery Protocol truncado en Authorize y Close). Sin tests del script. | abierto

### Orden 2: BL-028 (mejora P0 — formalizar)

[BL-028] | mejora | alta | Papertrading review/PAPER-TRADING-ARCHITECTURE-CONTRACT.md | **Amend Architecture Contract to v2.0:** formalizar el 3-endpoint discovery mechanism, documentar las regex de elegibilidad como frozen rules (en formato legible para operator review, no código embebido), agregar sección "Documented Deviations / Errata" con referencia a BL-027, realizar impact assessment contra RFC-000..009 (Auditability, Determinism, Integration Hostility, etc.). Coordinar con BL-029 (externalized config) y BL-018..BL-026 (open items del paper trading). Mini-SDD cycle recomendado: proposal → spec → design → tasks → apply → verify → archive. | abierto

### Orden 3: BL-029 (mejora P0 — externalize config, multi-league configurable)

[BL-029] | mejora | media | scripts/ensure_active_market.py, .env.example | **Externalize hardcoded discovery config to .env (resuelve pedido de multi-league).** Mover `_CANDIDATE_LEAGUES` y los regex (`_WIN_QUESTION_PATTERN`, `_REJECT_PATTERNS`) a variables de entorno: `TRADY_AI_FOOTBALL_LEAGUES` (comma-separated), `TRADY_AI_WINNER_PATTERN` (regex string), `TRADY_AI_REJECT_PATTERNS` (comma-separated substrings). Cumplir con AD-5 del Architecture Contract: "operator may adjust frozen rules at review windows" sin deploy de código. Mantener defaults hardcoded como fallback si las variables no están presentes (backward compat). Multi-league configurable es pedido explícito del operador (sesión 2026-07-22): "el sistema pueda mantenerse solo y funcionar solo". | cerrado (implementado 2026-07-22 con 29 tests, verify-report)

### Orden 4: BL-031 (tests de integración preexistentes — no bloqueantes)

[BL-031] | bug | media | tests/integration/test_paper_trading_session.py, tests/paper_trading/test_guard.py, tests/paper_trading/test_reconstruction.py | **8 tests de integración fallan consistentemente (preexistentes a Phase A del Calibration Framework).** Detectados durante verify de `calibration-framework` Phase A (2026-07-22). Los 8 tests requieren fixtures específicos (DB con estado, WebSocket mock, `.env` poblado) que no están presentes en el entorno de test actual. No son regresiones — ya fallaban antes del refactor del engine. No bloquean Phase B ni el resto del desarrollo. Scope: integración y guard script. | abierto

### Orden 5: BL-030 (cosmético — post-dry-run)

[BL-030] | bug | baja | src/trady_ai/paper_trading/bundler.py | **Bundle path `paper_trading/paper_trading/dia-001/` shows doubled prefix.** El bundler concatena `config.bundle_base_dir` (que el operador setea como `paper_trading/` relativo al CWD) con el path relativo del día, resultando en `paper_trading/paper_trading/` porque el CWD ya está dentro de `paper_trading/`. No blocker: el bundle se genera correctamente, los checksums son válidos, y la regeneración reproduce el mismo path. Arreglar: usar path absoluto desde `config.repo_root` en vez de path relativo al CWD, o normalizar `/` redundantes en la concatenación. | abierto

---

## 🧠 NOTAS

- **Estado Fase 1**: ✅ Limpia. mypy: 0 errores. pytest: 117 pass. Coverage: 97%.
- **Estado Fase 2**: ✅ Archive completo. 199 tests. 91% coverage. Mergeado a main.
- **Estado Fase 3**: ✅ Archive completo. 284 tests. 92.40% coverage. Mergeado a main.
- **Próximo paso**: Fase 5 — Paper Trading (Operational Sequencer). BL-019 ahora cerrado (Fase 4 completada, Paper Trading arranca).
- **Lecciones aprendidas**:
  - Cambios con riesgo de impacto colateral requieren Assessment Report + Documento Contrato antes de aplicar.
  - Cambios triviales (renombres locales, annotations) pueden aplicarse directo con nota en commit.
  - Verify es fresh-context adversarial review: no confiar en claims del apply-progress sin re-verificar.
  - apply-progress puede afirmar "green" algo que está rojo — verify atrapa esto como CRITICAL.
  - Commit local WIP (no pusheado) + squash en archive: snapshot reproducible para verify + backup del trabajo + history remoto limpio (cf. PORTABLE OS/SDD-CYCLE-GOVERNANCE.md).
  - BL-015 (schema NOT NULL) puede romper tests que no populan el campo requerido — verificar todos los callers de append_event.
  - SQLite + threads: `check_same_thread=False` necesario cuando EventCapture (daemon thread) accede la DB creada en thread principal.
  - BL-014: Polymarket CLOB API no tiene endpoint histórico de eventos individuales — `/prices-history` devuelve datos agregados (OHLC-like), no eventos. WS no tiene resumption protocol. Limitación documentada.
  - **2026-07-22**: La regla "do not touch backlog" se malinterpretó ayer. BACKLOG-PROTOCOL §1: "Todo hallazgo se registra" — registration es **mandatory**, no opcional. La regla de scope (§2) se refiere a no *trabajar* en hallazgos sin autorización, no a no *registrarlos*. BL-027/028/029 hubieran debido crearse ANTES del fix del script.
  - **2026-07-22**: Polymarket discovery: API REST no expone sports via tags. Working path: `polymarket.com/sports/{league}/games` (HTML) → `gamma-api/events?slug={slug}` → `clob.polymarket.com/markets/{conditionId}`. Lecciones: User-Agent `Python-urllib/3.12` → 403; usar browser UA. Cuando API no expone datos, la web sí los tiene (HTML + Next.js + Schema.org JSON-LD).
- **Decisiones del usuario**:
  - BL-013: capture state siempre "stopped" en Fase 2 (EventCapture efímero, no overengineering con pidfile). Documentar como limitación.
  - Orden de ejecución ajustado: BL-010+011 antes que BL-009 (destraba validación antes de meterse en mypy denso).
  - BL-014: investigar Polymarket API antes de implementar (Option A). Resultado: no existe endpoint histórico → declarar limitación.
  - 2026-07-22: Paper Trading discovery es autonomous-first (Approach A). El sistema descubre markets solo via guard script, sin intervención del operador. Operator ajusta reglas frozen via `.env` (no deploy de código) — BL-029.
  - 2026-07-22: Remediación de P0+P1 del Portable OS compliance review se hace ANTES del dry-run session. Test rigor importa más que velocidad.