# Archive: 002 — Deterministic Core (Fase 1)

## Fecha de cierre

2026-07-08

## Resumen ejecutivo

Fase 1 del roadmap de Trady.AI completada. Se construyó el motor de ejecución determinístico — el corazón del sistema — procesando CSVs de mercado paso a paso y generando señales vía Markov persistence. Sin APIs, sin async, sin inteligencia.

El cambio entrega 14 módulos nuevos + 3 modificados, orquestados en 4 PRs stacked-to-main con 117 tests, 97% coverage, y verificación final **PASS sin warnings**.

## Métricas finales

| Métrica | Valor |
|---------|-------|
| **Tests** | **117/117 passed (100%)** |
| **Coverage** | **97%** (554 stmts, 17 miss) |
| **Ruff** | 0 errores bloqueantes |
| **Mypy** | 0 errores nuevos (30 pre-existentes en PRs 1-3, reconocidos en spec) |
| **Acceptance Criteria** | **16/16** |
| **PRs** | 4 stacked-to-main (PR 1: ~380 lines → PR 2: ~450 → PR 3: ~500 → PR 4: ~540) |
| **Módulos implementados** | 14 nuevos + 3 modificados |
| **Tareas completadas** | **20/20** (100%) |
| **Estado verify final** | **PASS ✅** |

## Archivos archivados

Los siguientes archivos fueron movidos de `openspec/specs/` a `openspec/changes/archive/2026-07-08-002-deterministic-core/`:

| Archivo | Tamaño |
|---------|--------|
| `002-deterministic-core-proposal.md` | 105 líneas |
| `002-deterministic-core-spec.md` | 1,159 líneas |
| `002-deterministic-core-design.md` | 463 líneas |
| `002-deterministic-core-tasks.md` | 258 líneas |
| `002-deterministic-core-verify-report.md` | 117 líneas |

## Decisiones arquitectónicas

| Decisión | Opción | Alternativa | Rationale |
|----------|--------|-------------|-----------|
| **RuntimeConfig separado de Settings** | Pydantic `BaseModel` frozen | Dentro de `Settings` (BaseSettings) | Concerns distintos: Settings = infraestructura (env, db_path, dry_run), RuntimeConfig = ejecución (thresholds, sizing). RuntimeConfig no hereda de Settings. |
| **Engine depende de SignalStrategy ABC** | Abstract base class | Directamente de MarkovStrategy | Bajo acoplamiento. Futuras estrategias (Fase 3+) solo implementan la ABC. Engine nunca importa MarkovStrategy directamente. |
| **Matriz de transición** | numpy `int64` | Python `list[list[int]]` | Broadcasting para probs, tipado fijo sin overflow |
| **Moneda** | `Decimal` | `float` | Errores de redondeo en P&L inaceptables en finanzas |
| **UUIDs** | UUID5 | UUID4 | Determinístico: mismo input → mismo ID. Replay y verificación posible |
| **Pipeline** | Secuencial sync | Async | Sin I/O externo en Fase 1. Async = complejidad innecesaria |
| **PositionManager** | In-memory dict | Solo DB writes | O(1) lookups por tick. DB es commit final, no source of truth durante runtime |
| **CSV parsing** | `csv.DictReader` (stdlib) | pandas | Dependencia de 30MB+ innecesaria para CSVs planos |
| **Floating point en %** | `float` | `Decimal` | Thresholds y costos son razonables con float. `transaction_cost_pct=0.0` es exacto |
| **Stop loss** | Configurable (`stop_loss_pct`, default 5%) | Hardcodeado | Ahora configurable via CLI flag `--stop-loss` |

## Entregas por PR

### PR 1 → main: Foundation (~380 lines)
- `pyproject.toml` + numpy ≥ 1.26
- `RuntimeConfig` (config/runtime_config.py) — frozen, 5 campos con validaciones
- `models.py` — 6 modelos Pydantic con UUID5 determinísticos
- `SignalStrategy` ABC — 4 abstractmethods
- `conftest.py` — fixtures del core

### PR 2 → main: Strategy & State (~450 lines)
- `MarkovStrategy` — matriz 3×3 numpy, cold start 50 ticks
- `MarketStateTracker` — clasificación UP/DOWN/NEUTRAL por threshold
- `normalize()` — UTC conversion, idempotente
- `read_csv()` — validación + parsing con stdlib
- `core/__init__.py` — re-exports

### PR 3 → main: Pipeline & Engine (~500 lines)
- `RiskEnforcer` — 5 checks fail-fast (max positions, size limit, stop loss, duplicados)
- `PositionManager` — in-memory, P&L con cost, lifecycle completo
- `ExecutionEngine` — pipeline 9 pasos por tick, fail-fast, determinístico
- `persistence.py` — 5 tablas SQLite, Decimal como TEXT
- `observability.py` — summary stats (win_rate, total_pnl, max_drawdown)
- Tests de integración del pipeline completo

### PR 4 → main: Assembly & Verify (~540 lines)
- `replay.py` — replay + verify_replay desde execution_log
- `settings.py` — +5 defaults + `get_runtime_config()`
- CLI `backtest`, `analyze` (implementado), `run` (stub)
- Verify final: 117 tests, 97% coverage, 16/16 AC

## Acceptance Criteria verificados

| # | Criterio | Resultado |
|---|----------|-----------|
| 1 | Mismo CSV → misma secuencia de señales | ✅ `test_engine_determinism` |
| 2 | Cold start: 50 ticks → WARMUP, cero señales no-NEUTRAL | ✅ `test_engine_cold_start` |
| 3 | Tick 51+ → READY, señales emitidas | ✅ `test_engine_exits_warmup` |
| 4 | Replay produce bitácora idéntica | ✅ `test_replay` |
| 5 | Parámetros configurables sin tocar código | ✅ CLI flags + custom values test |
| 6 | RuntimeConfig independiente de Settings | ✅ BaseModel puro, no BaseSettings |
| 7 | Engine depende de SignalStrategy ABC | ✅ Importa ABC, nunca MarkovStrategy |
| 8 | UUID5 determinísticos | ✅ 3 tests de determinismo UUID |
| 9 | Precios como TEXT en SQLite | ✅ Decimal string preservado exacto |
| 10 | CSV mal formado → excepción explícita | ✅ ValueError con contexto |
| 11 | validate_secrets NO invocado en Fase 1 | ✅ grep vacío en cli/ |
| 12 | dry_run=True por defecto | ✅ Settings + Engine default True |
| 13 | numpy en pyproject.toml | ✅ `"numpy>=1.26"` presente |
| 14 | Pipeline completo 9 pasos | ✅ normalize→state→update→evaluate→risk→execute→persist→log |
| 15 | compute_summary retorna métricas | ✅ total_signals, total_pnl, max_drawdown |
| 16 | CLI backtest funciona | ✅ `test_backtest_command` → output con summary |

## Invariantes arquitectónicos preservados

- ✅ Sin async en ningún módulo core
- ✅ Sin APIs externas en ningún módulo core
- ✅ Sin inteligencia/AI en ningún módulo core
- ✅ Sin hidden retries ni silent corrections
- ✅ Sin probabilistic execution paths
- ✅ Sin runtime mutation de configuración
- ✅ Strategies generan señales — NO ejecutan trades
- ✅ Engine posee ejecución authority — strategies no
- ✅ Sin contaminación cross-domain (estados de mercados diferentes)

## Cobertura por módulo (final)

| Módulo | Coverage | Cambio vs 1er verify |
|--------|----------|----------------------|
| `runtime_config.py` | 100% | — |
| `models.py` | 100% | — |
| `signal_strategy.py` | 100% | — |
| `markov_strategy.py` | 100% | — |
| `state.py` | 100% | — |
| `normalization.py` | 100% | — |
| `ingestion.py` | 100% | — |
| `risk.py` | 96% | ⬆️ +15pp |
| `position_manager.py` | 100% | ⬆️ +35pp |
| `engine.py` | 91% | — |
| `persistence.py` | 96% | — |
| `replay.py` | 100% | — |
| `observability.py` | 100% | ⬆️ +32pp |
| `settings.py` | 100% | ⬆️ +13pp |
| `cli/main.py` | 94% | — |

## Lecciones aprendidas

1. **Determinismo se paga en diseño, no se agrega después**: Cada decisión (UUID5, Decimal para moneda, frozen RuntimeConfig, secuencial sync) fue deliberada desde la spec. No hay "hacerlo determinístico después" — se diseña desde el día 0.

2. **ABC temprano paga dividends**: `SignalStrategy` como abstract base class desde PR 1 forzó al engine a depender de la abstracción desde el inicio. PR 3 no tuvo que refactorizar nada.

3. **Configuración como concerns separados**: Separar `Settings` (infraestructura) de `RuntimeConfig` (ejecución) evitó el acoplamiento a variables de entorno para parámetros que cambian por ejecución.

4. **18 tests nuevos en verify post-warning**: La verify report de primera vuelta encontró 4 módulos con cobertura indirecta. Se escribieron 18 tests directos que elevaron coverage de 93% a 97%. El verify ácido de segunda vuelta fue PASS sin warnings.

5. **Stacked PRs funcionaron**: PR 1 → main, PR 2 → main (post PR 1), etc. Cada PR mantenía diff reviewable (~400-540 lines). El costo fue la espera secuencial, pero el beneficio fue revisabilidad y merges limpios.

6. **Stop loss ahora es configurable**: Originalmente hardcodeado al 5%. Se parametrizó como `stop_loss_pct` en `RuntimeConfig` con default 0.05. Ahora es configurable via CLI `--stop-loss` y env var.

## Riesgos encontrados y mitigados

| Riesgo | Estado | Mitigación |
|--------|--------|------------|
| `np.argmax` cambia comportamiento en numpy >2.x | ✅ Mitigado | Pin `numpy>=1.26,<3`. argmax first-occurrence está documentado |
| `Decimal.quantize` con cost_pct causa `Inexact` | ✅ Mitigado | `quantize(..., rounding=ROUND_HALF_EVEN)` explícito |
| SQLite execution_log con millones de filas | ✅ Aceptado | Fase 1 local-first, CSVs acotados. Índice por tick_number |
| `fromisoformat` pre-3.11 | ✅ No aplica | Python 3.12 requerido |

## Próximos pasos (Fase 2: Polymarket Integration)

La Fase 2 conecta el motor determinístico con el mundo real vía Polymarket (CTF CLOB API). Temas clave:

- **Adapters HTTP**: Cliente CLOB API con rate limiting, retry con backoff exponential, y error classification
- **Market sync engine**: Sincronización de mercados desde Polymarket a SQLite local
- **Order management**: Postear órdenes (LIMIT, GTC), trackear fills, cancelar
- **Live balance**: Sync de USDC balance + allowance
- **Deterministic wrapper**: Capa que adapta I/O no-determinístico al contrato determinístico del engine
- **Market types**: Distinguir entre mercados binarios (Sí/No) y multicategóricos
- **validate_secrets**: Validación de credenciales al startup (desactivado en Fase 1)

**RFCs a consultar**: RFC-002 (Platform Integration), RFC-006 (Multi-Domain Execution)

## Veredicto

✅ **APROBADO — Fase 1 completada**

El Deterministic Core de Trady.AI cumple con todos los criterios de aceptación del spec, todos los tests unitarios especificados existen y pasan, los 4 PRs stacked-to-main están mergeados, y la verificación final fue PASS sin warnings. 117 tests, 97% coverage, 16/16 acceptance criteria.

Ready para Fase 2: Polymarket Integration.
