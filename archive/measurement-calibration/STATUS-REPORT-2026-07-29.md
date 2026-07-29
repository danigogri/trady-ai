# PAPER TRADING — Estado del Proyecto y Barrera Técnica

> **Fecha**: 2026-07-29 16:48 UTC | **Día**: 2 del experimento | **Sesiones**: 55

---

## PARTE I — ESTADO ACTUAL DEL PROYECTO

### 1.1 Resumen ejecutivo

El experimento de Paper Trading V1 corre en un VPS AWS Lightsail en Singapur (52.220.172.112), capturando datos tick-by-tick de BTCUSDT y ETHUSDT desde Bybit testnet. El sistema opera de forma autónoma con sesiones cada 15 minutos, 0 errores, y pipeline completo (guard → capture → execute → reflect → bundle).

### 1.2 Métricas del experimento

| Métrica | Valor |
|---------|-------|
| Día calendario | **Day 2** (29 julio 2026) |
| Sesiones completadas | **55** |
| Eventos capturados | **1,319** |
| Errores | **0** |
| Trades ejecutados | **0** |
| Uptime VPS | 1 día 14 horas |
| Load average | 0.15 / 0.07 / 0.02 |

### 1.3 Distribución por mercado

| Market | Eventos | % |
|--------|---------|---|
| BTCUSDT | 672 | 50.9% |
| ETHUSDT | 647 | 49.1% |

### 1.4 Infraestructura

| Componente | Estado |
|-----------|--------|
| VPS | AWS Lightsail t3.micro, Singapur |
| RAM | 911 MB (46% usada) |
| Disco | 38 GB (9% usado, 35 GB libre) |
| DB SQLite | 5.9 MB (1,319 eventos + 55 reports + 36,810 exec_log) |
| Crontab | ✅ `*/15 * * * *` activo |
| Backup diario | ✅ 02:00 UTC |
| Log | 3.6 MB, 32K+ líneas |

### 1.5 Base de datos

```
event_store:        1,319 filas (datos crudos de Bybit testnet)
reflection_reports:    55 filas (1 por sesión, domain=BYBIT-SPOT)
execution_log:     36,810 filas (1 por tick procesado)
strategy_snapshots:     0 filas ⬅️ VACÍO — BARRERA TÉCNICA
trades:                 0 filas
calibration_adoptions:  0 filas
```

### 1.6 Historial de incidentes

| Fecha | Incidente | Resolución |
|-------|-----------|------------|
| 2026-07-28 | Session counter = day counter false positive | SDD cycle `fix-calendar-day-counter` (commit `52d0c71`) |
| 2026-07-29 | DB limpiada, Day 0 Restart | Forensic archive guardado |

### 1.7 Commits recientes

```
52d0c71 fix: calendar day counter — replace session COUNT with frozen DAY_ZERO date math
6ba3b08 fix: EventCapture._capture_one uses market_input fields for domain-agnostic dedup
0955fee feat: Bybit Spot Adapter — tick-by-tick trade stream for V1 Paper Trading
```

---

## PARTE II — LA BARRERA TÉCNICA

### 2.1 El problema en una frase

**El motor Markov procesa 1,319 eventos pero NUNCA persiste sus conteos de transición. Cada 15 minutos aprende y olvida. Sin datos persistidos, `calibrate review` no puede analizar nada y no podemos encontrar el threshold óptimo.**

### 2.2 Los tres sub-problemas

#### Problema 1: Threshold demasiado grande para crypto tick data

**Código actual** — `src/trady_ai/paper_trading/session.py:352`:

```python
strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=0.001)
```

`threshold_pct=0.001` significa 0.1%. A $87,000/BTC, necesita un movimiento de **$87.00** para registrar UP o DOWN. En una ventana de 60 segundos, BTC se mueve típicamente $2-$5 (0.002%-0.006%). Resultado: **el 99% de los ticks clasifican como NEUTRAL**.

| Threshold | $ equivalente (BTC ~$87K) | Ticks necesarios | ¿En 60 segundos? |
|-----------|--------------------------|-------------------|-------------------|
| **0.1%** (actual) | $87.00 | 870 | ❌ Casi nunca |
| 0.01% | $8.70 | 87 | ⚠️ Ocasional |
| 0.005% | $4.35 | 43 | ✅ Frecuente |
| 0.001% | $0.87 | 9 | ✅ Muy frecuente |

**Fuente**: Bybit API confirma `tickSize: 0.1` para BTCUSDT. Cada tick = $0.10 = 0.000115% del precio. El threshold actual es **870x más grande** que un tick individual.

#### Problema 2: Sin calibración adoptada

`calibration_adoptions` = 0. El sistema está usando el default `DirectionalStateGenerator(3)` con threshold 0.1%. El Calibration Framework (AIC, BIC, Markov χ², persistencia, entropía) está implementado pero nunca se usó para BYBIT-SPOT. No hay un state space adoptado que el motor pueda usar.

#### Problema 3: Strategy snapshots no se persisten (BL-018)

El motor Markov procesa todos los eventos cada sesión, acumula conteos de transición en memoria (`self._transition_counts`), genera decisiones... y al terminar la sesión, **todo se descarta**. La tabla `strategy_snapshots` está en **0 filas**.

El método `persist_strategy_snapshot()` existe en `core/persistence.py` (línea 291) pero **nunca se invoca** desde el engine. La función está completa — acepta `transition_counts`, `state_counts`, `warmup_ticks`, `threshold_pct`, `state_space_size`, `state_generator` — pero nadie la llama.

### 2.3 BL-018 — Referencia completa del backlog

```
[BL-018] | deuda | baja | strategies/markov/persistence.py, core/persistence.py |
`_last_state` no se persiste en `strategy_snapshots` — la primera transición 
post-restore no se registra (1 data point perdido por ciclo). `restore()` 
explícitamente setea `_last_state = None`. `evaluate()` no se ve afectado 
(solo usa `_transition_counts`). El contrato arquitectónico ideal del snapshot 
exige resumability total (estado indistinguible del pre-snapshot), lo cual 
requiere `_last_state`. Fix diferido: requiere agregar columna `last_state TEXT` 
al schema + tests de roundtrip con transiciones. | abierto
```

**Nota**: BL-018 se enfoca en `_last_state`, pero el problema más urgente es que **ningún dato** se persiste — ni `transition_counts`, ni `state_counts`, ni nada. La tabla está completamente vacía.

### 2.4 El cuello de botella

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  event_store ──→ Motor Markov ──→ decisiones (HOLD)             │
│  (1,319 eventos)   (aprende)      (olvida todo)                 │
│                                                                 │
│                         ✗ NO guarda en strategy_snapshots       │
│                                                                 │
│  calibrate review ──→ strategy_snapshots ──→ "no data available"│
│  (no puede analizar)   (0 filas)                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## PARTE III — TRES OPCIONES PARA ROMPER LA BARRERA

### Opción A: Fix BL-018 + pausar experimento

**Qué hace**: Agregar `persist_strategy_snapshot()` al final del `run()` del engine. Requiere reiniciar el experimento porque el código cambia.

**Código a modificar** — `src/trady_ai/core/engine.py`, después del loop de ticks (línea ~165):

```python
# engine.py — al final del método run(), después del loop y antes del return

from trady_ai.core.persistence import persist_strategy_snapshot

# Guardar snapshot de transiciones aprendidas
domain = "BYBIT-SPOT"  # o pasar como parámetro
persist_strategy_snapshot(
    db=self._db,
    domain=domain,
    strategy_name=strategy.name,
    tick_number=len(inputs),
    transition_counts=strategy._transition_counts.tolist(),
    state_counts=strategy._state_counts.tolist(),
    warmup_ticks=strategy._warmup_ticks,
    threshold_pct=strategy._threshold_pct,
    state_space_size=strategy._generator.state_count,
    state_generator=strategy._generator.__class__.__name__,
)
```

**Proceso**:
1. Modificar `engine.py` (1 método, ~10 líneas)
2. El `domain` actualmente no llega al engine — hay que pasarlo como parámetro o inferirlo
3. Pushear aGitHub, sync a VPS, `pip install -e .`
4. Como el código cambió, el experimento en curso se ve afectado (siguiente sesión usa nuevo engine)
5. Esperar 15-30 min → 1-2 sesiones graban snapshots
6. `calibrate review --domain BYBIT-SPOT` → ya funciona
7. Probar diferentes thresholds manualmente (cambiando `session.py:352` entre sesiones)

| Pro | Contra |
|-----|--------|
| Solución definitiva a BL-018 | Requiere deploy de código |
| Snapshots disponibles para siempre | `domain` no está disponible en `run()` — hay que pasarlo |
| Calibración futura automática | El threshold sigue hardcodeado en `session.py` |

---

### Opción B: Shadow calibration — SIN tocar el experimento

**Qué hace**: Crear un script que corre en paralelo, lee la DB del experimento (read-only), ejecuta el motor Markov con diferentes thresholds, guarda snapshots temporales, y compara resultados.

**Script conceptual** — `scripts/shadow_calibrate.py`:

```python
"""Shadow calibration — corre en paralelo al experimento, no modifica el motor."""
from trady_ai.config import get_settings
from trady_ai.db.database import get_db
from trady_ai.core.engine import ExecutionEngine
from trady_ai.core.markov_strategy import MarkovStrategy
from trady_ai.core.persistence import (
    get_events,
    persist_strategy_snapshot,
)
from trady_ai.reflection.calibration.analyzer import CalibrationAnalyzer

THRESHOLDS = [0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01]
DOMAIN = "BYBIT-SPOT"

settings = get_settings()
db = get_db(settings)

events = get_events(db, since_seq=0)
print(f"Eventos disponibles: {len(events)}")

for threshold in THRESHOLDS:
    engine = ExecutionEngine(db, dry_run=True)
    strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=threshold)
    result = engine.run(events, strategy)
    
    # Guardar snapshot temporal (se sobreescribe en cada iteración)
    persist_strategy_snapshot(
        db=db,
        domain=DOMAIN,
        strategy_name="markov_persistence",
        tick_number=len(events),
        transition_counts=strategy._transition_counts.tolist(),
        state_counts=strategy._state_counts.tolist(),
        warmup_ticks=50,
        threshold_pct=threshold,
    )
    
    # Analizar
    analyzer = CalibrationAnalyzer()
    report = analyzer.analyze(db, DOMAIN)
    
    print(f"Threshold {threshold*100:.4f}%: "
          f"AIC={report.aic:.2f}, BIC={report.bic:.2f}, "
          f"χ² p={report.markov_test.get('p_value', 'N/A')}, "
          f"persistence={report.state_persistence}")
```

**Proceso**:
1. Crear `scripts/shadow_calibrate.py` (no modifica código del motor)
2. Ejecutar en el VPS (puede ser en otra sesión SSH, no interfiere)
3. El script lee `event_store` (read-only), corre el motor con cada threshold
4. Guarda snapshots temporales (sobrescribe el mismo `tick_number`)
5. `CalibrationAnalyzer` computa AIC, BIC, χ², persistencia, entropía
6. Output: tabla comparativa — "el threshold 0.003% es el mejor"
7. Una vez elegido, modificar `session.py:352` con el threshold óptimo

| Pro | Contra |
|-----|--------|
| Experimento NO se toca | Script ad-hoc, no reutilizable |
| Resultados inmediatos | Snapshots se pisan entre iteraciones |
| Sin deploy de código | Hay que correrlo manualmente en el VPS |
| Comparación side-by-side | Los snapshots no quedan para futuro |

---

### Opción C: Mini-SDD — persistencia mínima + threshold configurable (RECOMENDADA)

**Qué hace**: Dos cambios quirúrgicos que no requieren pausar el experimento:

1. Agregar `persist_strategy_snapshot()` al `_do_execute()` de `session.py` (ya tiene acceso a `domain`)
2. Hacer el threshold configurable desde `session.py` para poder probar valores sin recompilar

**Cambio 1** — `src/trady_ai/paper_trading/session.py:346-353`:

```python
# ANTES
def _do_execute(self, scope: str, domain: str) -> None:
    """Run the execution engine on captured events."""
    from trady_ai.core.markov_strategy import MarkovStrategy

    engine = self._ensure_execution_engine()
    strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=0.001)
    engine.run_from_store(strategy, since_seq=0)

# DESPUÉS
def _do_execute(self, scope: str, domain: str) -> None:
    """Run the execution engine on captured events."""
    from trady_ai.core.markov_strategy import MarkovStrategy
    from trady_ai.core.persistence import persist_strategy_snapshot

    engine = self._ensure_execution_engine()
    strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=0.001)
    result = engine.run_from_store(strategy, since_seq=0)

    # Persistir transition counts para calibración (BL-018 parcial)
    if strategy.is_ready():
        snapshot_data = strategy.get_state_summary()
        persist_strategy_snapshot(
            db=self._db,
            domain=domain,
            strategy_name=strategy.name,
            tick_number=len(result.decisions),
            transition_counts=snapshot_data["transition_counts"],
            state_counts=snapshot_data["state_counts"],
            warmup_ticks=strategy._warmup_ticks,
            threshold_pct=strategy._threshold_pct,
            state_space_size=snapshot_data.get("state_space_size", 3),
            state_generator=snapshot_data.get("state_generator", "directional"),
        )
```

**Cambio 2** — Hacer el threshold configurable (opcional, para iteración rápida):

```python
# En session.py, leer threshold desde variable de entorno
import os

THRESHOLD_PCT = float(os.environ.get("TRADY_AI_THRESHOLD_PCT", "0.001"))

def _do_execute(self, scope: str, domain: str) -> None:
    # ...
    strategy = MarkovStrategy(warmup_ticks=50, threshold_pct=THRESHOLD_PCT)
    # ...
```

**Proceso**:
1. Modificar `session.py` — `_do_execute()` (1 método, ~15 líneas nuevas)
2. Opcional: agregar `TRADY_AI_THRESHOLD_PCT` al `.env`
3. Commit, push, sync a VPS, `pip install -e .`
4. **El experimento NO se pausa** — la siguiente sesión (15 min) ya graba snapshots
5. En 1-2 sesiones, `strategy_snapshots` tiene datos
6. Para probar thresholds: cambiar `.env` → `TRADY_AI_THRESHOLD_PCT=0.0001` → siguiente sesión usa nuevo threshold → graba snapshot → `calibrate review` compara
7. Iterar: 0.0005, 0.001, 0.005, etc. Una sesión por threshold.
8. Al encontrar el óptimo, adoptar con `calibrate adopt`

| Pro | Contra |
|-----|--------|
| Experimento NO se pausa | Requiere deploy de código (mínimo) |
| `strategy_snapshots` se puebla automáticamente | BL-018 parcial — `_last_state` sigue sin persistir |
| Threshold configurable sin recompilar | El threshold config es manual (`.env`), no automático |
| `calibrate review` funciona en ~15 min | |
| Camino más corto al objetivo | |

---

## PARTE IV — COMPARATIVA

| Criterio | Opción A | Opción B | Opción C |
|----------|----------|----------|----------|
| ¿Pausa el experimento? | ⚠️ Deploy code | ✅ No | ✅ No |
| ¿Puebla strategy_snapshots? | ✅ | ⚠️ Temporal | ✅ Permanente |
| ¿Threshold configurable? | ❌ Hardcodeado | ✅ En script | ✅ En .env |
| ¿Funciona calibrate review? | ✅ En ~15 min | ✅ Inmediato | ✅ En ~15 min |
| ¿Resuelve BL-018? | ✅ Completo | ❌ No toca | ⚠️ Parcial |
| ¿Código a modificar? | `engine.py` (~10 líneas) | Script nuevo (~30 líneas) | `session.py` (~15 líneas) |
| ¿Deploy necesario? | ✅ Sí | ❌ No | ✅ Sí |
| ¿Reutilizable? | ✅ Sí | ❌ Ad-hoc | ✅ Sí |
| Tiempo hasta resultado | ~30 min | ~5 min | ~30 min |

---

## PARTE V — RECOMENDACIÓN

**Opción C** es el camino más corto con el mayor retorno:

1. **15 líneas de código** en un solo archivo (`session.py`)
2. El experimento **no se detiene** — siguiente sesión ya graba snapshots
3. En **30 minutos** tenés `calibrate review` funcionando con datos reales
4. El threshold configurable permite **iterar rápido**: probás 5 thresholds en 5 sesiones (75 minutos)
5. BL-018 queda **parcialmente resuelto** — los conteos de transición se persisten, solo falta `_last_state`

El mayor riesgo es mínimo: `persist_strategy_snapshot()` ya existe, está testeada, y es una operación INSERT OR REPLACE — idempotente, no rompe nada.

---

**Archivos relacionados**:
- `paper_trading/archive/bug-session-counter-2026-07-28/INCIDENT-REPORT.md` — incidente del session counter
- `openspec/changes/archive/2026-07-28-fix-calendar-day-counter/` — SDD archive del fix
- `BACKLOG.md` — BL-018 (línea 88), BL-021, BL-033
- `src/trady_ai/core/engine.py` — `run()` método, línea 46-170
- `src/trady_ai/core/persistence.py` — `persist_strategy_snapshot()`, línea 291
- `src/trady_ai/paper_trading/session.py` — `_do_execute()`, línea 346
- `src/trady_ai/strategies/markov/persistence.py` — `MarkovPersistenceEngine`, línea 41
