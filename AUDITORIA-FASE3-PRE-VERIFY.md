# Auditoría Pre-Verify — Fase 3: Strategy Infrastructure

**Rol**: Auditor (chat orquestador, NO implementador)  
**Fecha**: 2026-07-11  
**Branch**: `feat/fase-3-strategy-infrastructure`  
**Base**: `main` @ `8ff82b4`

---

## Resumen Ejecutivo

La Fase 3 implementó 8 archivos nuevos y modificó 4 existentes. La calidad del código es alta — limpio, documentado, cumple RFC-003. **Pero no compila.** Hay 3 hallazgos que bloquean el verify, uno CRITICAL y dos WARNING.

---

## Hallazgos

### 🔴 CRITICAL — Circular Import bloquea toda la estrategia

**Archivo**: `src/trady_ai/core/__init__.py` línea 19  
**Causa**: El re-export `from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine as MarkovStrategy` crea un ciclo:

```
core/__init__.py (línea 19)
  → strategies/markov/persistence.py (línea 17)
    → strategies/base.py (línea 14)
      → core/__init__.py (vía from trady_ai.core.models ...)
        → 💥 ImportError: cannot import name 'StrategyBase' from partially initialized module
```

**Impacto**:  
- `from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine` → **FALLA**  
- `from trady_ai.strategies.base import StrategyBase` → **FALLA**  
- `from trady_ai.core import MarkovStrategy` → **FALLA** (usa el re-export de `__init__`)  
- **Ningún test de estrategia puede correr.** Los 199 tests de Fase 1-2 sí corren (no importan `strategies`).

**¿Por qué funciona `from trady_ai.core.markov_strategy import MarkovStrategy`?**  
Porque el stub `core/markov_strategy.py` no dispara `core/__init__.py`. El import carga `core/markov_strategy.py` → `strategies/markov/persistence.py` → `strategies/base.py` → `core.models` → Python ve que `core` ya está en `sys.modules` (cargado por el stub) y no re-ejecuta `__init__`. Sin ciclo.

**Ruta de fix recomendada**:
1. Remover línea 19 de `core/__init__.py` — el re-export crea el ciclo
2. Remover `"MarkovStrategy"` de `__all__` en `core/__init__.py`
3. Agregar comentario explicando que el re-export está en `core/markov_strategy.py` (el stub)
4. Actualizar `tests/unit/strategies/test_backward_compat.py` línea 8: cambiar `from trady_ai.core import MarkovStrategy` → `from trady_ai.core.markov_strategy import MarkovStrategy`
5. Actualizar spec delta `002-deterministic-core/delta.md`: el requisito "`core/__init__.py` SHALL exportar `MarkovStrategy`" es inviable por el circular import. Documentar que el re-export en `core/markov_strategy.py` (stub) es el mecanismo backward-compat definitivo.

**El backward-compat vía stub (`from trady_ai.core.markov_strategy import MarkovStrategy`) funciona perfectamente.** Solo falla `from trady_ai.core import MarkovStrategy` (vía `__init__`), que es el path que usa 1 solo test.

---

### 🟡 WARNING — Conflicto de nombre de archivo de test

**Archivos en conflicto**:  
- `tests/integration/test_persistence.py` (existente, Fase 1-2)  
- `tests/unit/strategies/markov/test_persistence.py` (nuevo, Fase 3)

**Causa**: Ambos archivos comparten el mismo basename `test_persistence`. Python/pytest trata el módulo como `test_persistence` y encuentra dos archivos con el mismo nombre. Resultado: `import file mismatch` durante collection.

**Impacto**: pytest no puede recolectar los tests de `strategies/markov/test_persistence.py`.

**Ruta de fix**: Renombrar el nuevo test a `test_markov_engine.py` o `test_markov_persistence.py` (nombre único en todo `tests/`).

---

### 🟡 WARNING — `__init__.py` vacíos en tests crean shadow package

**Archivos**:  
- `tests/unit/strategies/__init__.py` (vacío)  
- `tests/unit/strategies/markov/__init__.py` (vacío)

**Causa**: Al tener `__init__.py`, pytest crea un package Python `strategies` a nivel top-level que sombrea `trady_ai.strategies`. Durante la collection, pytest intenta importar `strategies.markov` (el package de test) y falla porque no encuentra los submódulos correctos.

**Impacto**: pytest no puede recolectar tests bajo `tests/unit/strategies/`.

**Ruta de fix**: Eliminar ambos `__init__.py`. pytest **no necesita** `__init__.py` en directorios de test para recolectar. El `conftest.py` en `tests/unit/strategies/markov/` se descubre por filesystem, no por Python package.

---

## Calidad del Código (lo que está BIEN)

### `strategies/base.py` (130 líneas) — ⭐⭐⭐⭐⭐
- StrategyBase refina SignalStrategy con ABC, isolation, lifecycle hooks
- Fail-fast: TypeError, RuntimeError, NotImplementedError — sin catch-all
- Domain property con setter (registry-friendly)
- `evaluate()` con warmup guard que devuelve NEUTRAL/0.0
- Docstrings completos. Sin imports de adapters/governance/persistence.

### `strategies/registry.py` (86 líneas) — ⭐⭐⭐⭐⭐
- Dict + factory, singleton per (domain, name)
- Lazy instantiation en `get()`, domain seteado post-creación
- `list()` con filtro opcional por domain
- `reset()` para testing. Docstrings con ejemplos de uso.

### `strategies/markov/persistence.py` (317 líneas) — ⭐⭐⭐⭐⭐
- MarkovPersistenceEngine con constructor idéntico al legacy (`warmup_ticks=50, threshold_pct=0.001`)
- `on_update()`: clasifica por STATE_INDEX, incrementa contadores numpy.int64
- `on_evaluate()`: argmax con tie-break determinístico, zero-transition → NEUTRAL/0.0
- UUID5 ausente (spec R2 lo requiere) — pero Signal.id se genera en `evaluate()` y se pasa al constructor. Verificar si el modelo Signal ya asigna UUID en `__init__`.
- `snapshot()` y `restore()` con delegación a funciones de persistencia
- VolatilityPersistence: `_classify_volatility()` con fórmula concreta (range_pct), 3 bandas (HIGH/LOW/STABLE), edge cases cubiertos
- DirectionalPersistence: alias semántico limpio (override de `name`)
- Constantes globales (STATE_INDEX, VOLATILITY_INDEX) bien definidas como dict a nivel módulo

### `core/persistence.py` (nuevas funciones) — ⭐⭐⭐⭐⭐
- `init_strategy_tables()`: schema SQL correcto, IF NOT EXISTS, UNIQUE constraint
- `persist_strategy_snapshot()`: INSERT OR REPLACE, JSON.dumps para matrices
- `load_latest_snapshot()`: ORDER BY tick_number DESC LIMIT 1, retorna None si vacío
- Llamada desde `init_core_tables()` — integración limpia

### `core/markov_strategy.py` (stub) — ⭐⭐⭐⭐⭐
- Una línea de re-export con docstring explicativo
- Limpio, mínimo, correcto

### `strategies/__init__.py` y `strategies/markov/__init__.py` — ⭐⭐⭐⭐⭐
- Exports explícitos con `__all__`, docstrings descriptivos

---

## Verificación de Specs vs Implementación

| Spec | Requisito | Estado | Nota |
|---|---|---|---|
| StrategyInfra R1 | StrategyBase con fail-fast, isolation | ✅ | Implementado en `base.py` |
| StrategyInfra R2 | StrategyRegistry singleton per key | ✅ | Implementado en `registry.py` |
| StrategyInfra R3 | Signal como output determinístico | ✅ | `evaluate()` devuelve Signal, engine decide ejecución |
| StrategyInfra R4 | Isolation enforcement | ✅ | No imports de adapters/governance en el código |
| StrategyInfra R5 | Fail-fast behavior | ✅ | TypeError, RuntimeError, ValueError definidos |
| StrategyInfra R6 | Lifecycle hooks | ✅ | on_init/on_update/on_evaluate/on_snapshot |
| Markov R1 | V1 variants (Directional, Volatility) | ✅ | Ambas definidas con state spaces independientes |
| Markov R2 | Signal generation contract | ⚠️ | UUID5 no visible en el código — verificar si Signal.__init__ lo asigna |
| Markov R3 | Internal contracts only | ✅ | Solo MarketState como input, sin imports de adapters |
| Markov R4 | Statistical traceability | ✅ | strategy_snapshots con schema completo |
| Markov R5 | Snapshot restore | ✅ | `restore()` classmethod con reconstruct |
| Markov R6 | Fail-fast on corruption | ✅ | JSONDecodeError → ValueError |
| Delta 002 | Backward-compat re-export | ⚠️ | `core/__init__` re-export roto por circular import. `core/markov_strategy.py` stub funciona. |
| Delta 002 | Engine pipeline unchanged | ⚠️ | No se auditó el engine — el código de `engine.py` no fue modificado en esta fase (solo se agregó la capacidad de registry loading) |
| Delta 002 | warmup_ticks/is_ready preserved | ✅ | Código idéntico al legacy |

---

## Tests

Los tests NO se pudieron ejecutar por los 3 hallazgos. Una vez resueltos:

| Grupo | Archivo | Líneas aprox |
|---|---|---|
| Unit: StrategyBase | `test_base.py` | ~195 |
| Unit: StrategyRegistry | `test_registry.py` | ~? |
| Unit: Markov Engine | `test_persistence.py` (→ `test_markov_engine.py`) | ~553 |
| Unit: Persistence Schema | `test_persistence_schema.py` | ~? |
| Unit: Backward Compat | `test_backward_compat.py` | ~41 |
| Integration: Registry+Engine | `tests/integration/strategies/` | ~? |

---

## Plan de Acción para el Chat Implementador

### Orden de fixes (dependencia: 1 → 2 → 3 → verify)

1. **Fix CRITICAL — Circular import**  
   - `core/__init__.py`: remover línea 19 (`from trady_ai.strategies.markov.persistence import ...`)  
   - `core/__init__.py`: remover `"MarkovStrategy"` de `__all__`  
   - `core/__init__.py`: agregar comentario `# MarkovStrategy re-export: use from trady_ai.core.markov_strategy import MarkovStrategy`  
   - `test_backward_compat.py` línea 8: cambiar a `from trady_ai.core.markov_strategy import MarkovStrategy`  
   - `specs/002-deterministic-core/delta.md`: actualizar requisito — el re-export está en el stub, no en `__init__`

2. **Fix WARNING — Conflicto de nombre**  
   - Renombrar `tests/unit/strategies/markov/test_persistence.py` → `test_markov_engine.py`  
   - Limpiar `__pycache__/` en ambos directorios de test

3. **Fix WARNING — Shadow package**  
   - Eliminar `tests/unit/strategies/__init__.py`  
   - Eliminar `tests/unit/strategies/markov/__init__.py`

4. **Verificar**  
   - `pytest tests/` — deben pasar todos (199 existentes + nuevos)  
   - `mypy src/` — 0 errores  
   - `ruff check .` — 0 errores  
   - Coverage ≥ 90% en nuevo código

---

## Nota sobre Daño Colateral

Durante la auditoría, `core/__init__.py` fue restaurado accidentalmente a la versión de Fase 2 (`git checkout --`). Fue re-restaurado manualmente a la versión de Fase 3. **Verificar que el archivo está correcto** — debe contener `from trady_ai.strategies.markov.persistence import MarkovPersistenceEngine as MarkovStrategy` en las imports.
