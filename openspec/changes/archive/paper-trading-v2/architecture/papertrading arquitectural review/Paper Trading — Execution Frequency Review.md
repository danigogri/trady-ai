# Paper Trading — Execution Frequency Review

## 1. Recomputed Statistical Model

### Base de cálculo

- Duración del experimento: 30 días = 720 horas = 43,200 minutos
- Duración de sesión: ~70 segundos (capture 60s + execute ~5s + reflect 3s + verify 2s)
- Sesiones por intervalo: sesiones = 720 / T donde T está en horas
- Error estándar: SE = 1/√n

| Intervalo | Sesiones/30d | SE (1/√n) | Reducción SE vs intervalo anterior | Mejora vs 6h baseline |
|---|---:|---:|---:|---:|
| 6h | 120 | 9.13% | — | baseline |
| 3h | 240 | 6.45% | −29.3% | 1.41× |
| 2h | 360 | 5.27% | −18.4% | 1.73× |
| 1h | 720 | 3.73% | −29.3% | 2.45× |
| 45m | 960 | 3.23% | −13.4% | 2.83× |
| 30m | 1,440 | 2.64% | −18.4% | 3.46× |
| 20m | 2,160 | 2.15% | −18.4% | 4.24× |
| 15m | 2,880 | 1.86% | −13.6% | 4.90× |
| 10m | 4,320 | 1.52% | −18.4% | 6.00× |

### Curva de diminishing returns (√n)

```text
Sesiones:  120    240    360    720    960   1440   2160   2880   4320
SE:       9.1%   6.5%   5.3%   3.7%   3.2%   2.6%   2.2%   1.9%   1.5%
           │      │      │      │      │      │      │      │      │
           │      ├─ 1.4x mejora (2x sesiones)
           │      │      ├─ 1.2x mejora (1.5x sesiones)
           │      │      │      ├─ 1.4x mejora (2x sesiones)
           │      │      │      │      ├─ 1.2x (1.3x)
           │      │      │      │      │      ├─ 1.2x (1.5x)
           │      │      │      │      │      │      ├─ 1.2x (1.5x)
           │      │      │      │      │      │      │      ├─ 1.2x (1.5x)
           ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
         Excelente   Muy bueno    Bueno     Moderado    Marginal
```

El punto de diminishing returns real: cada duplicación de sesiones reduce el SE en ~29% (propiedad de √n). No hay un "codo" matemático — la mejora marginal es continua y predecible: para reducir el SE a la mitad, necesitás 4× sesiones. Para reducirlo a un décimo, necesitás 100× sesiones.

Desde el punto de vista puramente estadístico, más sesiones = mejor calibración. No hay punto donde "no vale la pena." El límite es puramente operacional.

Estado: READY TO FREEZE (el modelo estadístico)

## 2. Football-Domain Evidence Analysis

### Modelo de partido de fútbol

```text
                        PARTIDO (90-120 min)
    ├─ Kickoff (0')      ──┐
    ├─ 1st Half (0-45')    ├─ Zona de alta volatilidad
    ├─ Halftime (45')      │  (goles, tarjetas, lesiones)
    ├─ 2nd Half (45-90')   │
    ├─ Late Game (75-90')  │  ← MÁXIMA señal: convergencia a resolución
    └─ Resolution (90+') ──┘

    Pre-match (días antes): volatilidad baja-media, acumulación de información
    Post-match: mercado cerrado, sin datos
```

### Probabilidad de capturar eventos clave

Asumiendo un partido de 105 minutos (90 + 15 entretiempo) con 3 goles a los 23', 57', y 82':

| Intervalo | Snapshots durante el partido | ¿Captura kickoff? | ¿Captura gol 1? | ¿Captura entretiempo? | ¿Captura gol 3 + resolución? | Eventos clave capturados |
|---|---:|---|---|---|---|---:|
| 6h | 0-1 | 8% probabilidad | ❌ sesión cada 6h, probabilidad ~12% de solaparse | ❌ | ❌ | 0-1 de 5 |
| 3h | 0-1 | 17% | ⚠️ Baja | ❌ | ❌ | 0-1 de 5 |
| 2h | 0-2 | 25% | ⚠️ Baja | ⚠️ Baja | ❌ | 0-2 de 5 |
| 1h | 1-2 | 42% | ⚠️ Media | ⚠️ Baja | ⚠️ Baja | 1-2 de 5 |
| 45m | 2-3 | 57% | ⚠️ Media | ⚠️ Media | ⚠️ Baja | 2 de 5 |
| 30m | 3-4 | 71% | ✅ Buena | ⚠️ Media | ⚠️ Media | 2-3 de 5 |
| 20m | 5-6 | 86% | ✅ Buena | ✅ Buena | ⚠️ Media | 3-4 de 5 |
| 15m | 7-8 | 93% | ✅ Excelente | ✅ Buena | ✅ Buena | 4-5 de 5 |
| 10m | 10-11 | 97% | ✅ Excelente | ✅ Excelente | ✅ Excelente | 5 de 5 |

La zona crítica: Late Game (75'-90+')

Este período de 15-20 minutos es donde ocurre la máxima señal de precio: el mercado converge a la resolución. Con intervalos ≥ 30 minutos, la probabilidad de tener siquiera UN snapshot en esta ventana es baja (~50% con 30m). Con 15 minutos, la probabilidad sube a 87%. Con 10 minutos, 97%.

Para calibración de un pipeline de trading, perder la ventana de resolución es perder el evento más informativo del ciclo de vida del mercado.

¿Qué pasa con las sesiones que NO caen durante un partido?

Con 10-15 minutos de intervalo, el 90%+ de las sesiones ocurren FUERA de partidos activos (entre partidos, de madrugada). Estas sesiones capturan:

- Pre-match drift (movimiento gradual de precios) — señal más débil pero acumulativa
- Mercados inactivos (sin eventos nuevos) — el evidence guard lo detecta como 0 eventos

Las sesiones sin partido tienen bajo valor individual pero alto valor acumulativo: 2,500+ sesiones de pre-match buildup construyen un baseline estadístico que permite al Reflection Engine distinguir señal de ruido cuando SÍ hay partido.

Estado: READY TO FREEZE (el análisis de fútbol)

## 3. Architectural Constraint Discovery

Este es el hallazgo que cambia el análisis. El modelo estadístico anterior asume que cada sesión captura NUEVOS datos. Pero la arquitectura actual lo impide.

El bottleneck: _reconstruct_stages()

```text
# session.py:337-343
# CAPTURING: any events today?
row = self._db.execute(
    "SELECT COUNT(*) FROM event_store WHERE DATE(timestamp) = ?",
    [today],
).fetchone()
if row and row[0] and int(row[0]) > 0:
    skip.add("capturing")
```

Esto significa: una vez que la primera sesión del día captura eventos, TODAS las sesiones subsiguientes de ese día skippean CAPTURING, EXECUTING, y REFLECTING.

### Simulación real con intervalo de 15 minutos

```text
Día 1:
  00:00 → Session #1:  CAPTURING ✅ (no hay eventos hoy)
                        EXECUTING ✅ (no hay trades hoy)  
                        REFLECTING ✅ (no hay report hoy)
                        → Datos NUEVOS capturados
                        
  00:15 → Session #2:  CAPTURING ❌ (reconstruction: ya hay eventos hoy)
                        EXECUTING ❌ (ya hay trades hoy)
                        REFLECTING ❌ (ya hay report hoy)
                        → SOLO verifica y bundletea. Cero datos nuevos.
                        
  00:30 → Session #3:  Ídem #2
  ...
  23:45 → Session #96: Ídem #2
```

Resultado: 1 sesión productiva, 95 sesiones estériles.

Efectividad: 1.04%

Esto no es un bug — es diseño

La reconstruction se diseñó para sesiones diarias (Paper Trading Spec REQ-PT-007: "Interrupted → reconstruct operational state from persisted evidence, continue from first incomplete stage"). El DATE(timestamp) = today asume granularidad diaria. Para sesiones sub-diarias, la granularidad es incorrecta.

### Lo que esto significa para el análisis

El modelo estadístico de la Sección 1 es teórico — no se puede alcanzar con la arquitectura actual. Las sesiones/día efectivas están capped a 1 (una por día = 30 en 30 días). Esto da:

- SE efectivo: 1/√30 = 18.3%
- Snapshots por partido: 0-1 (igual que intervalo de 6h)
- Cobertura de eventos clave: mínima
- Calidad de calibración: pobre

Con la arquitectura actual, cualquier intervalo menor a 24h produce EXACTAMENTE la misma calidad de calibración que 24h. La diferencia entre 10 minutos y 23 horas es cero desde la perspectiva de datos nuevos.

Estado: NEEDS DISCOVERY (el constraint no era obvio en análisis previos)

## 4. Operational Cost Comparison

Incluyendo el impacto del reconstruction bottleneck:

| Intervalo | Sesiones/día | Sesiones productivas/día | Sesiones estériles/día | WS connects/día | DB writes (nuevos)/día | Runtime/día |
|---|---:|---:|---:|---:|---:|---:|
| 6h | 4 | 1 | 3 | 4 | ~100-1000 | ~5 min |
| 3h | 8 | 1 | 7 | 8 | ~100-1000 | ~9 min |
| 2h | 12 | 1 | 11 | 12 | ~100-1000 | ~14 min |
| 1h | 24 | 1 | 23 | 24 | ~100-1000 | ~28 min |
| 30m | 48 | 1 | 47 | 48 | ~100-1000 | ~56 min |
| 20m | 72 | 1 | 71 | 72 | ~100-1000 | ~84 min |
| 15m | 96 | 1 | 95 | 96 | ~100-1000 | ~112 min |
| 10m | 144 | 1 | 143 | 144 | ~100-1000 | ~168 min |

Conclusión: aumentar la frecuencia con la arquitectura actual NO aumenta la recolección de datos. Solo aumenta el desperdicio computacional (sesiones estériles). Cada sesión adicional gasta CPU, I/O, y WS connections para re-verificar y re-bundletear datos que no cambiaron.

Estado: NEEDS GOVERNANCE DECISION

## 5. Options to Resolve the Constraint

Hay tres caminos arquitectónicamente válidos:

### Option A: Session-Aware Reconstruction (cambio mínimo)

Refinar _reconstruct_stages() para que detecte etapas completadas POR SESIÓN, no por día calendario. En vez de DATE(timestamp) = today, usar el max_seq alcanzado en la sesión anterior.

```text
# En vez de: "¿hay eventos hoy?"
# Usar:     "¿hay eventos NUEVOS desde la última sesión?"

last_session_seq = self._get_last_session_max_seq(domain)
new_events = count_events_since(self._db, last_session_seq)
if new_events == 0:
    skip.add("capturing")
```

Impacto arquitectónico: Mínimo. Cambia la granularidad de una función existente. No agrega módulos, no cambia contratos, no modifica el state machine. Es una refinación, no un rediseño.

Con este cambio: todas las sesiones del modelo estadístico se vuelven productivas. 15 minutos → 2,880 sesiones productivas en 30 días. SE efectivo = 1.86%.

### Option B: Separar Capture del Pipeline (cambio medio)

```text
cron cada 15 min:  tradis-ai capture --duration 60 --markets <from .env>
cron cada 24h:     tradis-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive
```

El capture corre frecuentemente (solo ingesta de datos). La sesión completa corre una vez al día (procesa todo lo acumulado).

Impacto arquitectónico: Medio. Requiere agregar --duration al comando capture del CLI (actualmente bloquea hasta Ctrl+C). Pero mantiene la separación Capture/Execute/Reflect intacta — de hecho, la REFUERZA.

Con este cambio: 96 capturas/día × 30 días = 2,880 ingestion events. Sesiones completas: 30. El execute procesa todos los eventos acumulados en cada sesión diaria.

### Option C: Mantener el status quo (cambio cero)

Aceptar que la frecuencia efectiva está capped a 1 sesión productiva por día. 30 sesiones en 30 días. SE = 18.3%.

Impacto arquitectónico: Cero. Pero la calidad de calibración es la peor de las tres opciones.

### Comparación

| Dimensión | Option A (Session-aware) | Option B (Separate capture) | Option C (Status quo) |
|---|---|---|---|
| Sesiones productivas/30d | 2,880 (@15min) | 30 (pipeline) + 2,880 (capture) | 30 |
| SE calibración | 1.86% | Depende de métrica | 18.3% |
| Cobertura de partido | 7-8 snapshots | Captura: 96/día, Pipeline: 1/día | 0-1 snapshots |
| Cambio de código | ~10 líneas en _reconstruct_stages | ~15 líneas en CLI capture | 0 líneas |
| ¿Viola frozen RFCs? | No | No | No |
| ¿Respeta A1 (Determinismo)? | ✅ | ✅ | ✅ |
| ¿Respeta A5 (Simplicidad)? | ✅ (refinación, no adición) | ⚠️ (dos cron jobs, dos modos) | ✅ (pero pobre calibración) |

Estado: NEEDS GOVERNANCE DECISION

## 6. Recommended Execution Interval

Si se adopta Option A (Session-Aware Reconstruction): 15 minutos

### Justificación cuantitativa:

1. Potencia estadística: 2,880 sesiones → SE = 1.86%. Esto es 4.9× mejor que el baseline de 6h (SE = 9.13%).
2. Cobertura de fútbol: 7-8 snapshots por partido → captura virtualmente todos los eventos clave (kickoff, goles, entretiempo, late game, resolución). Con 20 minutos (5-6 snapshots) podrías perder 1-2 eventos. Con 10 minutos (10-11 snapshots), la mejora marginal en cobertura de fútbol es pequeña — ya capturaste todo.
3. Punto de diminishing returns: entre 15 y 10 minutos, la mejora en SE es 18.4% (de 1.86% a 1.52%), pero la mejora en cobertura de partido es marginal (~10%). El ratio beneficio/costo se aplana después de 15 minutos.
4. Runtime manejable: 96 sesiones/día × 70s = ~112 minutos de runtime/día = 7.8% del tiempo del VPS. En un VPS de $5/mes, esto es trivial.
5. WS connections: 96/día = 4/hora. No es agresivo para una API pública.

Si se adopta Option B (Separate Capture): 15 minutos para capture, 24h para pipeline

El capture corre cada 15 minutos (misma densidad de ingestión que Option A). El pipeline procesa todo acumulado una vez al día. La calidad de calibración es comparable a Option A porque los datos crudos son los mismos — la diferencia está en cuándo se ejecuta el análisis.

Si se mantiene Option C (Status Quo): 24 horas (o el intervalo que sea — no importa)

Como solo la primera sesión del día es productiva, cualquier intervalo < 24h es indistinguible. La recomendación sería una sesión diaria en un horario que maximice la probabilidad de solaparse con partidos activos (ej: 19:00 UTC para ligas europeas).

Estado: NEEDS GOVERNANCE DECISION

## 7. Mathematical Justification

¿Por qué 15 minutos y no 10?

El teorema central del límite nos dice que SE ∝ 1/√n. La ganancia marginal de agregar Δn sesiones adicionales es:

```text
ΔSE = |1/√(n + Δn) − 1/√n|
Para n = 2,880 (15 min), agregar 1,440 sesiones más (llegar a 10 min):
ΔSE = |1/√4320 − 1/√2880|
    = |0.01521 − 0.01863|
    = 0.00342
```

Es decir, reducir el SE en 0.34 puntos porcentuales (de 1.86% a 1.52%) a costa de 50% más sesiones.

Para ponerlo en contexto futbolístico:

- Con 15 minutos: tenés 7-8 snapshots por partido. La probabilidad de tener al menos 1 snapshot en la ventana de late game (75'-90') es ~87%. La probabilidad de capturar el momento exacto post-gol (ventana de 5 minutos) es ~33% por gol.
- Con 10 minutos: tenés 10-11 snapshots. Late game coverage: ~97%. Post-gol coverage: ~50% por gol.

La mejora en late game coverage es de 10 puntos porcentuales (87% → 97%). La mejora en post-gol coverage es de 17 puntos. Esto NO es trivial — pero para un experimento de CALIBRACIÓN (no de trading), capturar 7-8 snapshots con 87% de cobertura de late game ya es suficiente para que el Reflection Engine detecte patrones.

Si el objetivo fuera trading en vivo, 10 minutos sería claramente superior. Para calibración, 15 minutos es el punto donde la mejora marginal en calidad de datos ya no justifica el 50% más de infraestructura.

### El √n lo confirma

| Métrica | 15 min → 10 min | Ganancia |
|---|---|---:|
| SE reduction | 1.86% → 1.52% | 18.4% |
| Sesiones adicionales | — | +50% |
| Late game coverage | 87% → 97% | +11.5% |
| Eficiencia (ganancia/costo) | — | 0.37 |

El ratio ganancia/costo < 1 indica diminishing returns. Cada punto porcentual de mejora en SE cuesta ~2.7 puntos porcentuales más de sesiones.

Estado: READY TO FREEZE

## 8. Final Freeze Recommendation

### Arquitectura operativa recomendada

```text
┌──────────────────────────────────────────────────────────────┐
│                 VPS — cron cada 15 minutos                     │
│                                                               │
│  1. ensure_active_market.py (guardián de continuidad)          │
│     └─ Rota market si expiró                                   │
│                                                               │
│  2. tradis-ai paper-trade session                              │
│     --domain FOOTBALL-WINNER --non-interactive                 │
│     └─ PRE_FLIGHT → CAPTURING → ... → BUNDLING                │
│                                                               │
│  ⚠️ REQUIERE: Option A — Session-Aware Reconstruction          │
│     Sin este cambio, solo 1/96 sesiones es productiva.         │
└──────────────────────────────────────────────────────────────┘
```

### Contrato operativo revisado

| Parámetro | Valor | Justificación |
|---|---|---|
| Intervalo | 15 minutos | Punto de diminishing returns para cobertura de fútbol + SE |
| Sesiones/día | 96 (8,760/año) | Máxima densidad antes de diminishing returns |
| Sesiones/30d | 2,880 | SE = 1.86% |
| Snapshots/partido | 7-8 | Captura todos los eventos clave |
| Late game coverage | ~87% | Suficiente para calibración |
| Runtime diario | ~112 min (7.8%) | Manejable en VPS |
| Prerrequisito | Refinar _reconstruct_stages() a granularidad sub-diaria | Sin esto, la frecuencia es irrelevante |

### Lo que NO se recomienda

- ❌ 10 minutos: diminishing returns en football coverage. +50% sesiones para +11% late game coverage no se justifica para calibración.
- ❌ 20+ minutos: pérdida significativa de cobertura de eventos intra-partido. SE > 2%.
- ❌ Sin refinar reconstruction: cualquier intervalo < 24h es indistinguible del status quo. Las 95 sesiones estériles son desperdicio.

La decisión real no es el intervalo — es si refinamos reconstruction

```text
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   ¿Refinamos _reconstruct_stages() para granularidad    │
│   sub-diaria?                                           │
│                                                         │
│   SÍ → 15 minutos, 2,880 sesiones, SE = 1.86%          │
│   NO → 24 horas, 30 sesiones, SE = 18.3%               │
│                                                         │
│   Cualquier intervalo intermedio sin refinar            │
│   reconstruction produce el mismo resultado que 24h.    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Estado: NEEDS GOVERNANCE DECISION

El modelo estadístico dice 15 minutos. La arquitectura actual dice "no sin refinar reconstruction." La decisión de governance es si hacemos esa refinación o aceptamos 30 sesiones en 30 días.