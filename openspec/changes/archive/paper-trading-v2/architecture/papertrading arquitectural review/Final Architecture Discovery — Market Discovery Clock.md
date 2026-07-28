# Final Architecture Discovery — Market Discovery Clock

## 1. Executive Summary

Market Discovery es un bounded context independiente. Merece su propio clock operacional. No por su frecuencia de ejecución distinta (que también), sino porque:

1. Modela un tipo de dato fundamentalmente distinto: metadata de mercados (reference data) vs time-series de precios (market data). En infraestructura financiera real, estos se manejan en sistemas completamente separados.
2. Tiene su propio lifecycle: discover → qualify → activate → monitor → retire. Este lifecycle es independiente del ciclo capture→execute→reflect de Evidence/Decision/Reflection.
3. La dependencia es unidireccional: Evidence depende de Discovery (necesita market_ids). Discovery NO depende de Evidence (puede verificar estado de mercado vía REST). Esta es la marca de un boundary válido.
4. Escala en una dimensión distinta: Discovery escala con el NÚMERO de dominios y plataformas. Evidence escala con el VOLUMEN de datos. Son dimensiones ortogonales.

La arquitectura final tiene 4 clocks: Discovery → Evidence → Decision → Reflection, con dependencias estrictamente unidireccionales.

Estado: READY TO FREEZE

## 2. Conceptual Definition of Market Discovery

### 2.1 ¿Qué es Market Discovery en el dominio?

Market Discovery no es "buscar mercados para tradear." Eso es Strategic Selection, que ya establecimos que pertenece a Governance.

Market Discovery es reference data management para mercados financieros. En infraestructura financiera profesional, reference data es el conjunto de datos que describe QUÉ instrumentos existen, independientemente de CÓMO se está tradeando cada uno:

| Reference Data (Discovery) | Market Data (Evidence) |
| --- | --- |
| ¿Qué mercados existen? | ¿A qué precio está este mercado? |
| ¿Están activos o cerrados? | ¿Cuánto volumen se tradeó? |
| ¿A qué categoría pertenecen? | ¿Cómo cambió el precio en el último tick? |
| ¿Cuándo expiran/resuelven? | ¿Cuál es el spread bid-ask? |
| Datos CUASI-ESTÁTICOS (cambian en días) | Datos en TIEMPO REAL (cambian en segundos) |

Esta distinción no es un invento nuestro. Es estándar en la industria financiera: los Instrument Masters y Security Masters son sistemas separados de los Market Data Platforms. Bloomberg tiene terminales diferentes para reference data (DES, SECF) y market data (ALLQ, MOST). Las exchanges exponen endpoints distintos para instrument definitions y para market data feeds.

### 2.2 ¿Qué NO es Market Discovery?

- ❌ NO es "elegir el mejor mercado" → eso es Strategic Selection (Governance)
- ❌ NO es "capturar precios" → eso es Evidence Clock
- ❌ NO es "generar señales" → eso es Decision Clock
- ❌ NO es "analizar outcomes" → eso es Reflection Clock

Market Discovery es: mantener el conjunto de mercados que el sistema está observando. Nada más. Nada menos.

## 3. Lifecycle Analysis

### 3.1 El lifecycle completo de un mercado observado

```text
                    ┌─────────────┐
                    │  DISCOVER   │  ← Scan platform APIs for available markets
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  QUALIFY    │  ← Apply frozen eligibility rules
                    └──────┬──────┘     (domain, type, active, not closed)
                           │
                           ▼
                    ┌─────────────┐
                    │  ACTIVATE   │  ← Add to active_markets config
                    └──────┬──────┘     → Evidence Clock starts capturing
                           │
                           ▼
                    ┌─────────────┐
                    │  MONITOR    │  ← Periodic health check:
                    └──────┬──────┘     still active? still producing events?
                           │            expired? resolved?
                           ▼
                    ┌─────────────┐
                    │  RETIRE     │  ← Remove from active_markets
                    └─────────────┘     → Evidence Clock stops capturing
                           │
                           ▼
                      (goto DISCOVER)
```

### 3.2 Comparación con el lifecycle de Evidence

| Fase | Discovery Lifecycle | Evidence Lifecycle |
| --- | --- | --- |
| Inicio | Market es creado en la plataforma | Market es activado por Discovery |
| Operación | Mantiene el catálogo de mercados observables | Captura eventos del mercado activo |
| Fin | Market expira/resuelve → se retira del catálogo | Market se retira → se deja de capturar |
| Duración típica | Días a semanas (vida del market) | Segundos a minutos (sesión de capture) |
| Gatillo | Eventos externos (nuevo market, market resuelto) | Schedule interno (cron cada 15 min) |

Conclusión: Son lifecycles distintos con triggers, duraciones y estados diferentes. No deberían compartir el mismo clock.

## 4. Responsibility Ownership Analysis

### 4.1 ¿Qué responsabilidades son EXCLUSIVAS de Discovery?

| Responsabilidad | ¿Puede hacerlo Evidence? | ¿Por qué no? |
| --- | --- | --- |
| Market scanning | ❌ No | Evidence consume market_ids, no los descubre. Si Evidence incluyera scanning, estaría decidiendo QUÉ capturar además de CÓMO capturar. Viola RFC-002: "Adapters isolate external APIs; adapters do not own strategy logic." |
| Opportunity identification | ❌ No | Esto es Governance (qué dominios nos interesan). Discovery ejecuta reglas frozen del humano, no identifica oportunidades. |
| Market eligibility | ⚠️ Parcialmente | Evidence YA aplica algunas reglas (DRY_RUN_ENFORCED). Pero eligibility de mercado (¿es football winner? ¿está activo?) no es responsabilidad de quien captura eventos. |
| Activation criteria | ❌ No | Activar un mercado es una decisión de configuración. Evidence es un consumidor de configuración, no un productor. |
| Market retirement | ⚠️ Parcialmente | Evidence ya detecta "0 eventos" (evidence guard). Pero retirar el mercado del catálogo no debería ser responsabilidad de quien captura. |
| Watchlist maintenance | ❌ No | Mantener una lista de candidatos pre-qualificados es state management. Evidence es stateless en cuanto a catálogo de mercados. |

### 4.2 ¿Qué pasaría si Discovery se queda dentro de Evidence?

Actualmente, ensure_active_market.py hace Discovery ANTES de cada sesión. Esto funciona, pero:

1. Cada 15 minutos, EvidenceClock ejecuta Discovery aunque no haya cambiado nada (96 veces/día)
2. Responsabilidades entreveradas: el guardián de continuidad hace scanning + qualification + activation + monitoring + retirement — todo en un script "pre-sesión"
3. Sin estado propio: no hay watchlist, no hay historial de mercados observados, no hay tracking de cuántos mercados pasaron por el sistema
4. Difícil de testear: Discovery está acoplado al ciclo de Evidence

Si Discovery es su propio clock, corre 1-2 veces por día (o cuando se detecta que un mercado expiró). Evidence corre 96 veces por día sin preocuparse de nada que no sea capturar eventos.

## 5. Temporal Analysis

### 5.1 Frecuencias naturales

| Clock | Frecuencia natural | Justificación |
| --- | --- | --- |
| Discovery | 1-2 veces/día o event-driven | Mercados nuevos aparecen cada horas/días. Mercados expiran en el timeframe de un partido (90 min) o días. No tiene sentido escanear cada 15 minutos. |
| Evidence | Cada 15 minutos | Los ticks de precio llegan cada segundos. 15 minutos acumulan cientos de ticks por mercado activo. |
| Decision | Cada 1-3 horas | Procesar eventos acumulados requiere un volumen mínimo para generar señales con confianza estadística. |
| Reflection | Diaria | Analizar outcomes requiere un día completo de trades para tener significancia estadística. |

### 5.2 ¿Diferente frecuencia justifica diferente clock?

El evaluation criteria dice:

"Different execution frequency alone is NOT sufficient justification."

Correcto. Pero la frecuencia distinta es un SÍNTOMA de responsabilidades distintas, no la causa. La causa es: Discovery gestiona metadata cuasi-estática; Evidence gestiona time-series en tiempo real. La diferencia de frecuencia es una consecuencia de modelar datos fundamentalmente distintos.

Es como preguntar: "¿Un sistema de nómina (mensual) y un sistema de point-of-sale (cada segundo) deberían ser el mismo sistema?" La respuesta no es "tienen frecuencias distintas." La respuesta es "modelan dominios distintos." La frecuencia es un indicador, no la razón.

## 6. Dependency Analysis

### 6.1 Grafo de dependencias

```text
                    ┌──────────────┐
                    │  GOVERNANCE  │  (externo — define reglas frozen)
                    └──────┬───────┘
                           │ reglas de eligibility
                           ▼
                    ┌──────────────┐
                    │  DISCOVERY   │  ← 1-2x/día
                    │  CLOCK       │
                    └──────┬───────┘
                           │ market_ids
                           ▼
                    ┌──────────────┐
                    │  EVIDENCE    │  ← cada 15 min
                    │  CLOCK       │
                    └──────┬───────┘
                           │ events
                           ▼
                    ┌──────────────┐
                    │  DECISION    │  ← cada 1-3 horas
                    │  CLOCK       │
                    └──────┬───────┘
                           │ trades
                           ▼
                    ┌──────────────┐
                    │  REFLECTION  │  ← diaria
                    │  CLOCK       │
                    └──────────────┘
```

### 6.2 Dirección de dependencias

| Dependencia | Dirección | Tipo |
| --- | --- | --- |
| Evidence → Discovery | Evidence necesita market_ids | Data dependency — unidireccional |
| Discovery → Evidence | Discovery NO necesita eventos | Independiente — Discovery verifica estado vía REST |
| Decision → Evidence | Decision necesita events | Data dependency — unidireccional |
| Reflection → Decision | Reflection necesita trades | Data dependency — unidireccional |

Todas las dependencias son unidireccionales y fluyen en una sola dirección: Governance → Discovery → Evidence → Decision → Reflection.

No hay ciclos. No hay dependencias bidireccionales. Esto es el ideal arquitectónico: un DAG (directed acyclic graph) de bounded contexts.

### 6.3 ¿Qué pasa si Discovery falla?

Discovery Clock cae (API de Polymarket /markets down)

→ No se actualiza el catálogo de mercados
→ Evidence Clock sigue capturando con los market_ids actuales
→ Los mercados actuales eventualmente expiran
→ Evidence Clock produce 0 eventos → evidence guard → ERROR
→ El operador detecta el ERROR en su ventana de revisión
→ Mientras tanto, NO se perdieron datos de los mercados que SÍ estaban activos

Failure isolation: un fallo en Discovery no afecta a Evidence, Decision, ni Reflection hasta que TODOS los mercados activos expiren. Y aun así, el sistema falla explícitamente (fail-fast), no silenciosamente.

## 7. Scalability Assessment

### 7.1 ¿Discovery se vuelve más importante con más dominios?

Sí — y esa es precisamente la razón para separarlo.

Con 1 dominio (FOOTBALL-WINNER):

Discovery: 1 platform (Polymarket) × 1 domain filter × ~5-10 active markets

Complejidad: trivial. Discovery "dentro de Evidence" funciona.

Con 5 dominios:

Discovery: 1 platform × 5 domain filters × ~20-50 active markets
+ eligibility rules diferentes por dominio
+ watchlist separada por dominio

Complejidad: media. Discovery dentro de Evidence empieza a ser problemático.

Con 20 dominios multi-plataforma (Fase 9):

Discovery: N platforms × M domain filters × ~100+ active markets
+ cross-platform market correlation
+ domain-specific retirement policies
+ market lifecycle coordination

Complejidad: alta. Discovery DEBE ser independiente.

### 7.2 ¿Football-specific assumptions?

Evaluemos si el diseño de Discovery tiene supuestos que solo aplican a football:

| Supuesto | ¿Football-specific? | Generalización |
| --- | --- | --- |
| "Markets tienen estado active/closed" | No — todo mercado financiero tiene esto | ✅ Universal |
| "Markets pertenecen a categorías (winner, corners)" | No — es solo un sistema de tags | ✅ Universal (sector, asset class, market type) |
| "Markets expiran en ~90 minutos" | ⚠️ Parcialmente | Para crypto/equities, los mercados NO expiran (son continuos). El concepto de "retirement" cambia: en vez de expirar, un mercado se retira por baja liquidez o cambio de estrategia. |
| "Nuevos mercados aparecen cada días" | ⚠️ Parcialmente | Crypto: mercados nuevos aparecen cada minutos/horas (nuevos pares, nuevos tokens). Equities: IPOs son raros. |

Hallazgo: El concepto de "retirement" necesita ser flexible. En football es expiry, en crypto es delisting, en equities nunca expira. El Discovery Clock debe soportar políticas de retirement por dominio, no asumir que todos los mercados expiran.

Esto REFUERZA la necesidad de un clock separado: tener retirement policies por dominio dentro de Evidence Clock sería una violación grave de A3.

## 8. Bounded Context Evaluation

Aplicando los criterios de Constitution A3 (Boundary Discipline):

| Criterio | Discovery Clock |
| --- | --- |
| MUST: ¿qué debe hacer? | Mantener el catálogo de mercados observables: discover, qualify, activate, monitor, retire |
| MUST NOT: ¿qué NO debe hacer? | Capturar eventos, generar señales, ejecutar trades, analizar outcomes |
| MAY: ¿qué puede hacer? | Mantener watchlist, persistir historial de mercados, exponer market_ids a Evidence |
| Ownership: ¿posee algo? | Market catalog state, eligibility rules (aplicación, no definición), retirement policies |
| Persistence: ¿tiene storage propio? | .env (active_markets) + watchlist state + market history |
| Contracts: ¿contratos explícitos? | Eligibility rules frozen, activation criteria, retirement triggers |
| Failure isolation: ¿fallos contenidos? | Si Discovery falla, Evidence, Decision y Reflection siguen funcionando |
| Observability: ¿trazable? | Cada activación/retirement genera log + evidencia |

Conclusión: Discovery satisface TODOS los criterios de un bounded context independiente.

## 9. RFC Impact Assessment

### RFC-002 — Platform Integration

Impacto: Ninguno. Discovery usa los MISMOS adapters que Evidence (get_markets(), get_market_data()). La capa de adapters ya está diseñada para ser usada por múltiples consumidores. RFC-002 §Adapter Doctrine: "All external platforms must be isolated through bounded adapters." No especifica que solo un consumidor pueda usar un adapter.

### RFC-006 — Multi-Domain Execution

Impacto: Discovery se convierte en el componente domain-aware. Evidence se vuelve domain-agnostic (solo captura lo que recibe). Esto es MEJOR que el diseño actual donde domain es un string arbitrario sin validación.

RFC-006 §Domain Isolation: "Domains must remain isolated across strategies, memory, reflection cycles, observability." Un Discovery Clock por dominio (o un Discovery Clock con políticas por dominio) preserva este aislamiento.

### RFC-008 — Autonomous Coordination

Impacto: Discovery es el candidato NATURAL para ser el primer clock automatizado en Fase 8. Su ciclo es determinístico (reglas frozen), frecuente (diario), y de bajo riesgo (no ejecuta trades).

RFC-008 §Primary Responsibilities: "schedule approved workflows, coordinate bounded execution sequences." Discovery → Evidence → Decision → Reflection es exactamente una secuencia de workflows boundeados.

### RFC-009 — Universal Financial Infrastructure

Impacto: El modelo de 4 clocks con dependencias unidireccionales es inherentemente escalable a múltiples plataformas. Cada plataforma puede tener su propio Discovery+Evidence clock pair, compartiendo Decision y Reflection.

RFC-009 §Universal Infrastructure Doctrine: "coordinate deterministic financial systems, preserve bounded intelligence integration, support multi-platform execution." Los clocks son la unidad de coordinación.

## 10. Final Recommendation

Option B: Market Discovery es un clock independiente.

Los 4 clocks de la arquitectura:

**DISCOVERY CLOCK** → "¿Qué mercados deberíamos estar observando?"

- Frecuencia: 1-2x/día o event-driven
- Input: Platform APIs, frozen eligibility rules
- Output: active_markets config

**EVIDENCE CLOCK** → "¿Qué está pasando en estos mercados?"

- Frecuencia: cada 15 min
- Input: active_markets, Platform WebSocket/REST
- Output: event_store rows

**DECISION CLOCK** → "¿Deberíamos tradear basados en esta evidencia?"

- Frecuencia: cada 1-3 horas
- Input: event_store, strategy
- Output: signals, trades

**REFLECTION CLOCK** → "¿Qué aprendimos de nuestras decisiones?"

- Frecuencia: diaria
- Input: trades, signals
- Output: reflection_reports, proposals

¿Por qué 4 clocks no violan A6 (Governance Minimalism)?

A6 dice: "Before adding any rule, process, or structure, ask: does this increase operational surface unnecessarily?"

La respuesta: separar Discovery REDUCE la superficie operativa de Evidence. Actualmente, Evidence Clock carga con 5 responsabilidades (scan, qualify, activate, monitor, retire) que no le pertenecen. Separarlas en un clock dedicado hace que:

- Evidence Clock sea MÁS simple (solo captura eventos)
- Discovery Clock sea MÁS cohesivo (todas las responsabilidades de catálogo en un solo lugar)
- El sistema total tenga MENOS acoplamiento (dependencias unidireccionales)

Esto NO es "agregar un proceso." Es reconocer un bounded context que ya existe pero está enterrado dentro de otro. La complejidad YA ESTÁ en el sistema — solo está mal ubicada.

## 11. Freeze Recommendation

La arquitectura de 4 clocks está lista para freeze conceptual.

### RESUMEN DE DECISIONES ARQUITECTÓNICAS:

1. Session NO es un concepto de dominio → es un artefacto operacional
2. Arquitectura Event-Centric con 4 clocks independientes
3. Clocks: Discovery → Evidence → Decision → Reflection
4. Dependencias estrictamente unidireccionales (DAG)
5. Cada clock trackea su propio progreso (reconstruction per-clock)
6. Discovery gestiona reference data (metadata de mercados)
7. Evidence gestiona market data (time-series de precios)
8. Decision aplica estrategias sobre eventos
9. Reflection analiza decisiones sobre trades
10. Governance permanece externo (humano define reglas frozen)

Estado: READY TO FREEZE — Arquitectura Conceptual

Estado: BACKLOG — Implementación de clocks independientes (Fase 6+)

Estado: READY TO FREEZE — Para Phase 5: Session como thin orchestrator que invoca los 4 clocks en secuencia, con reconstruction refinado a granularidad sub-diaria