# Proposal: Deterministic Core (Fase 1)

**Roadmap Phase**: 1 | **Motivado por**: RFC-001, RFC-003

## Core Principles

1. **Deterministic Execution** — Identical inputs MUST produce identical outputs.
2. **Replayability** — Any execution MUST be fully reproducible from stored data.
3. **Auditability** — Every decision, signal, and state transition MUST be traceable.
4. **Fail Fast & Fail Loud** — Never silence errors. Surface them immediately, with enough context to reproduce.
5. **Low Coupling** — Engine depends on abstractions (SignalStrategy), never on concrete implementations.

## Intent

Construir el motor de ejecución determinístico de Trady.AI — el corazón del sistema. Sin APIs, sin inteligencia, sin async. Procesa CSVs de mercado paso a paso y genera señales vía Markov persistence.

## Deterministic Execution Contract

The engine MUST behave as a deterministic state machine. Given identical input market data, runtime configuration, strategy implementation, and engine version, the engine MUST always produce identical observable behaviour (market state transitions, signals, decisions, trades, positions, SQLite records, replay output, and summary stats). Every observable difference MUST be fully explained by a corresponding difference in inputs. No execution may depend on randomness, hidden state, execution timing, or external side effects.

## Scope

### ✅ In Scope
- Ingesta CSV (timestamp, market_id, price, volume)
- Normalización: UTC + Decimal
- MarketStateTracker con threshold configurable por mercado (UP/DOWN/NEUTRAL)
- SignalStrategy (ABC) + MarkovStrategy (matriz 3×3, señal con confianza)
- Cold start: 50 obs → WARMUP (aprende, no señaliza) → READY
- Position sizing fijo, transaction_cost_pct (default 0%)
- `RuntimeConfig` separado de `Settings`: threshold_pct, warmup_ticks, position_size, transaction_cost_pct
- RiskEnforcer (fail-fast), PositionTracker (SQLite)
- ExecutionEngine orquesta lifecycle completo — depende de `SignalStrategy` (ABC), nunca de `MarkovStrategy` directamente
- Deterministic replay + summary stats
- validate_secrets desactivado (sin adapters externos)

### ❌ Out of Scope
- Estrategias no-Markov (Fase 3+)
- Adapters / APIs / async / portfolio / UI

### 🚫 Non Goals (Phase 1 intentionally excludes)
- Profitability optimization
- Live trading
- Adaptive strategies
- AI / Machine Learning / prediction models
- Portfolio optimization
- Multi-strategy orchestration

## Capabilities

### New
- `deterministic-core`: Pipeline completo — ingesta, normalización, state, risk, persistence, replay, observabilidad
- `markov-strategy`: Implementación SignalStrategy con matriz 3×3, cold start, threshold por mercado

### Modified
- `001-python-bootstrap`: +numpy como dependencia, módulo `core/` reemplaza placeholder

## Approach

Pipeline por tick: `CSV → Validación → Normalización → MarketState → SignalStrategy.evaluate() → RiskEnforcer → ExecutionDecision → PositionManager → DB → Log`

**Separation of concerns**: `Settings` (infraestructura: environment, logging, db_path, dry_run) vs `RuntimeConfig` (ejecución: threshold_pct, warmup_ticks, position_size, transaction_cost_pct).

**Fail Fast**: toda validación que falle lanza excepción explícita con contexto suficiente para reproducir el error. No hay `try/except` que silencie errores sin justificación documentada.

```
Engine → SignalStrategy (abstract)
         └── MarkovStrategy (Fase 1)
         └── ... (futuro)
```

numpy para matriz de transición. Toda decisión se logga + persiste en SQLite.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/trady_ai/core/` | New | 11 archivos (models, engine, signal_strategy, state, risk, runtime_config, etc.) |
| `pyproject.toml` | Modified | +`numpy >= 1.26` |

## Risks

| Risk | Mitigation |
|------|------------|
| Matriz poco informativa en mercados con pocas transiciones | Cold start N=50 mínimo; threshold configurable por mercado |
| SQLite lock si se paraleliza en futuro | Fase 1 es estrictamente secuencial |

## Rollback

1. Eliminar `src/trady_ai/core/`
2. Revertir `pyproject.toml` (quitar numpy)
3. Restaurar `core/__init__.py` a placeholder
4. Verificar `trady-ai status` y `analyze` sigan funcionando

## Dependencies

- `numpy >= 1.26`
- Bootstrap 001 completado

## Success Criteria

- [ ] Mismo CSV → misma secuencia de señales en ejecuciones sucesivas
- [ ] Cold start: primeros 50 ticks → WARMUP, cero señales
- [ ] Tick #51+ → READY, señales emitidas
- [ ] Replay produce bitácora idéntica a ejecución original
- [ ] Umbrales, position_size y transaction_cost configurables sin tocar código
