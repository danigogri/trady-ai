# Architecture Discovery Report — Session-Centric vs Event-Centric

## 1. Executive Summary

"Session" no es un concepto de dominio. Es un artefacto operacional. Los RFCs fundacionales (000, 001, 002, 003, 004) nunca mencionan "Session" como entidad arquitectónica. Session aparece exclusivamente en el Paper Trading Spec (REQ-PT-001), que es un documento de implementación operativa, no un RFC fundacional.

Los verdaderos conceptos de dominio — Evidence, Decision, Reflection — ya están definidos como bounded contexts independientes en los RFCs. La arquitectura actual los implementó correctamente como módulos separados (EventCapture, ExecutionEngine, ReflectionEngine), pero luego los acopló dentro de PaperTradingSession en un pipeline secuencial monolítico.

Este acoplamiento es el root cause del bottleneck de reconstruction descubierto en el review anterior. No es un bug de implementación — es una consecuencia de tratar un artefacto operacional (Session) como unidad arquitectónica primaria.

Recomendación: Reconocer los tres clocks (Evidence, Decision, Reflection) como los verdaderos bounded contexts. Session se degrada a un thin orchestrator que coordina clocks sin acoplarlos. La evolución hacia independencia total de clocks pertenece a Fase 6+.

## 2. Domain Reconstruction

### 2.1 Entidades fundamentales del dominio

Analizando el dominio "financial intelligence infrastructure" desde primeros principios:

| Entidad | ¿Qué es? | ¿Es de dominio? | Evidencia |
| --- | --- | --- | --- |
| Market | Un activo financiero externo con precio, volumen, y estado. Tiene lifecycle: created → active → resolving → resolved. | ✅ Sí | RFC-006: "Domains represent operationally distinct financial realities." |
| Event / Observation | Un cambio de estado en un Market: tick de precio, trade, order book update. Llega del mundo externo. | ✅ Sí | RFC-002: "Adapters isolate external APIs, expose frozen internal contracts." |
| Decision / Signal | El output de una estrategia: LONG, SHORT, NEUTRAL. Generado a partir de Events procesados. | ✅ Sí | RFC-003: "Strategies generate signals. They do not own execution authority." |
| Execution / Trade | Actuar sobre una Decision: abrir/cerrar posición. | ✅ Sí | RFC-001: "The Deterministic Core executes. It does not improvise." |
| Reflection | Análisis post-ejecución de Decisions y sus outcomes. | ✅ Sí | RFC-004: "Reflection analyzes execution. It does not control execution." |
| Calibration | Evaluación meta de si el sistema produce señales estadísticamente confiables. | ✅ Sí | RFC-004 §Drift Detection: "detect statistical degradation, strategy instability." |
| Session | Agrupación operacional de capture → execute → reflect. | ❌ No | Solo aparece en REQ-PT-001. Ausente de todos los RFCs. |

### 2.2 ¿Por qué Session no es un concepto de dominio?
Evidencia 1 — Los RFCs no lo mencionan.
Busqué "Session" en los 9 RFCs. Resultado: cero ocurrencias. Los RFCs hablan de:
- "execution sequencing" (RFC-001)
- "signal generation" (RFC-003)
- "post-execution analysis" (RFC-004)
- "operational continuity" (RFC-009)
Ninguno define "Session" como unidad arquitectónica.
Evidencia 2 — Session es una construcción de implementación.
REQ-PT-001: "Single invocation of run_session(scope, domain, market_ids) → SessionReport traverses all states sequentially."
Esto es una decisión de API, no una verdad de dominio. Es como si un sistema de email definiera "SendButton" como concepto arquitectónico porque el CLI tiene un comando send.
Evidencia 3 — Los componentes subyacentes YA son independientes.
EventCapture, ExecutionEngine, y ReflectionEngine son módulos separados con imports directos (REQ-PT-004: "Direct Python import only"). No se necesitan entre sí para funcionar. Session es el que los encadena.
### 2.3 El acoplamiento que Session introduce

```text
PaperTradingSession.run_session():
    _do_capture(market_ids)     ← depende de adapter
    _do_execute(scope, domain)  ← depende de event_store (llenado por capture)
    _do_reflect(scope, domain)  ← depende de trades (generados por execute)
```

Este es un pipeline secuencial con dependencias de datos. Si capture falla, execute no corre. Si execute no corre, reflect no corre. Las tres responsabilidades comparten el mismo destino.

Pero en el dominio real, estas responsabilidades NO comparten destino:

- Si un market no tiene eventos nuevos, capture debería seguir corriendo (otros markets pueden tener eventos)
- Si no hay eventos nuevos, execute no debería correr (no hay nada que procesar)
- Si no hay trades nuevos, reflect debería seguir corriendo (analiza datos históricos, no solo los nuevos)

## 3. Conceptual Model
### 3.1 Modelo actual (Session-Centric)

```text
                    ┌─────────────┐
                    │   SESSION   │
                    │  (monolith) │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │  CAPTURE   │  │  EXECUTE   │  │  REFLECT   │
    │  (60s)     │─▶│  (on same  │─▶│  (on same  │
    │            │  │   events)  │  │   trades)  │
    └────────────┘  └────────────┘  └────────────┘
```

Propiedades:

- Un solo clock para las tres responsabilidades
- Si una falla, todas fallan
- Si querés capturar más, ejecutás y reflejás más (innecesario)
- Reconstruction es per-session, no per-responsabilidad

### 3.2 Modelo propuesto (Clock-Centric)

```text
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │ EVIDENCE CLOCK  │     │ DECISION CLOCK   │     │ REFLECTION CLOCK│
    │                 │     │                  │     │                 │
    │ Frequency:      │     │ Frequency:       │     │ Frequency:      │
    │ every 15 min    │     │ every 1-3 hours  │     │ daily           │
    │                 │     │                  │     │                 │
    │ Reads: market   │     │ Reads: events    │     │ Reads: trades   │
    │ Writes: events  │     │ Writes: signals  │     │ Writes: reports │
    │                 │     │          trades   │     │         proposals│
    └────────┬────────┘     └────────┬─────────┘     └────────┬────────┘
             │                       │                        │
             │    event_store        │    trades              │
             ├──────────────────────▶├───────────────────────▶│
             │   (datos crudos)      │   (decisiones)         │   (análisis)
             │                       │                        │
             ▼                       ▼                        ▼
    ┌────────────────────────────────────────────────────────────────┐
    │                        EVIDENCE STORE                          │
    │  events → signals → trades → reflection_reports               │
    │  (cada clock escribe en su propia capa, lee de capas previas) │
    └────────────────────────────────────────────────────────────────┘
```

Propiedades:

- Tres clocks independientes con frecuencias propias
- Failure isolation: si capture falla, execute sigue con datos viejos
- Sin acoplamiento temporal: podés capturar cada 15min y reflejar una vez al día
- Reconstruction per-clock: cada clock trackea su propio progreso

## ## 4. Session-Centric vs Event-Centric Analysis

| Dimensión | Session-Centric | Event/Clock-Centric |
| --- | --- | --- |
| Acoplamiento temporal | Capture → Execute → Reflect en lockstep | Cada clock a su frecuencia natural |
| Failure isolation | Un fallo en capture bloquea todo el pipeline | Un fallo en Evidence no afecta Reflection |
| Reconstruction | Per-session, per-day granularity. No soporta sub-diario. | Per-clock, per-seq granularity. Soporta cualquier frecuencia. |
| Eficiencia de recursos | Si capture no produce eventos, execute y reflect corren igual sobre datos viejos | Si no hay eventos nuevos, Decision Clock no corre. Si no hay trades nuevos, Reflection Clock no corre. |
| Generalización entre dominios | Football: session cada 15min → execute y reflect también cada 15min (innecesario) | Football: evidence cada 15min, decision cada 3h, reflection diaria. Crypto: evidence cada 1min, decision cada 5min, reflection diaria. Misma arquitectura, distintas frecuencias. |
| Alineación con RFCs | Session no aparece en ningún RFC | Evidence → RFC-002 (Adapters), Decision → RFC-001/003 (Core/Strategies), Reflection → RFC-004. Cada clock mapea a un RFC existente. |
| Simplicidad (A5) | ✅ Más simple: un solo comando, un solo reporte | ⚠️ Más complejo: tres schedulers, tres tipos de reporte |
| Boundary Discipline (A3) | ❌ Colapsa tres bounded contexts en un pipeline | ✅ Cada bounded context es un clock independiente |

## ## 5. Independent Clock Analysis

### 5.1 Los tres clocks fundamentales

#### Evidence Clock

| Propiedad | Valor |
| --- | --- |
| Responsabilidad | Ingerir eventos de mercado y persistirlos en event_store |
| Dueño arquitectónico | RFC-002 (Platform Integration) — Adapters layer |
| Input | Polymarket WebSocket + REST |
| Output | Filas en event_store (seq, market_id, price, volume, timestamp) |
| Frecuencia natural | 15 minutos (football) a 1 minuto (crypto) |
| Dependencias | PolymarketAdapter, EventCapture |
| ¿Puede correr solo? | ✅ Sí — solo necesita adapter + DB |
| Reconstruction | Trackea max_seq alcanzado. Resume desde max_seq + 1. |

#### Decision Clock

| Propiedad | Valor |
| --- | --- |
| Responsabilidad | Procesar eventos acumulados → generar signals → ejecutar trades |
| Dueño arquitectónico | RFC-001 (Core) + RFC-003 (Strategies) |
| Input | Eventos en event_store desde last_processed_seq |
| Output | Filas en signals y trades |
| Frecuencia natural | 1-6 horas (cuando suficientes eventos nuevos se acumularon) |
| Dependencias | ExecutionEngine, strategy (ej: MarkovStrategy) |
| ¿Puede correr solo? | ✅ Sí — solo necesita DB + strategy |
| Reconstruction | Trackea last_processed_seq. Procesa eventos seq > last_processed_seq. |

#### Reflection Clock

| Propiedad | Valor |
| --- | --- |
| Responsabilidad | Analizar trades → evaluar outcomes, detectar drift, generar propuestas |
| Dueño arquitectónico | RFC-004 (Reflection Systems) |
| Input | Trades + signals + outcomes en DB |
| Output | reflection_reports, proposals |
| Frecuencia natural | Diaria o semanal (análisis sobre datos acumulados) |
| Dependencias | ReflectionEngine, analyzers |
| ¿Puede correr solo? | ✅ Sí — solo necesita DB + analyzers |
| Reconstruction | Trackea last_report_date. Analiza desde esa fecha. |

### 5.2 ¿Son necesarios más clocks?

| Clock candidato | ¿Es un clock independiente? | Justificación |
| --- | --- | --- |
| Calibration Clock | ❌ No — es un modo de Reflection | Calibration es "reflection sobre suficientes datos para declarar readiness." Misma frecuencia, mismo dueño. Diferente threshold, no diferente clock. |
| Governance Clock | ❌ No — es externo al sistema | Governance es el operador humano. No es un proceso automatizado. No necesita clock. |
| Market Discovery Clock | ⚠️ Híbrido | Discovery es parte de Evidence Clock (el guardián de continuidad antes de capturar). Pero tiene frecuencia distinta (días, no minutos). Podría ser un sub-clock de Evidence. |
| Portfolio Clock | ❌ No — Fase 6+ | No aplica en Fase 5. En Fase 6, portfolio management es parte de Decision Clock (asignación de capital entre dominios). |
| Risk Clock | ❌ No — es una constraint de Decision | Risk no es un proceso separado. Es un constraint que Decision Clock aplica al ejecutar. "Risk enforcement" ya está en RFC-001 §Primary Responsibilities. |
| Lifecycle Clock | ❌ No — es meta | Lifecycle (30-day experiment) es el marco que contiene a los clocks. No es un clock en sí mismo. |

Conclusión: Tres clocks son suficientes. Agregar más es governance inflation (Constitution A6).

## 6. Scalability Assessment
6.1 ¿La arquitectura propuesta escala a otros dominios?
Dominio	Evidence Clock	Decision Clock	Reflection Clock	¿Requiere cambios?
Football Winner	15 min (eventos cada ~segundos durante partido)	1-3 horas	 	 