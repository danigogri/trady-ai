# Paper Trading Operational Readiness — Architect Review 1

Role: Challenger, not defender. Mi trabajo es probar que nuestras ideas están equivocadas. Si sobreviven, son más fuertes.

## 1. Executive Summary

El concepto de "Temporary Operational Governance Layer" es innecesario y arquitectónicamente riesgoso. Viola el Constitution A6 (Governance Minimalism) al introducir una capa de gobernanza duplicada sobre el governance que ya existe (RFC-007 + Paper Trading Spec). Peor aún: la hipótesis de que Hermes debe participar en market discovery o candidate generation es incorrecta. Cada paso del workflow pre-trading es una operación determinística — queries de API, filtros matemáticos, escritura de archivos. Hermes no agrega valor medible en ninguna de estas etapas.

Recomendación: reemplazar toda la "Operational Governance Layer" con 3 scripts determinísticos que el operador humano ejecuta bajo su autoridad. Zero AI. Zero governance nuevo. Cero complejidad innecesaria.

Estado: NEEDS GOVERNANCE DECISION

## 2. Overall Architectural Assessment

### 2.1 El problema del "temporary governance layer"

La propuesta de una "capa de gobernanza operativa temporal" choca con tres constraints congelados:

| Artifact | Qué dice | Conflicto |
| --- | --- | --- |
| Constitution A6 | "Governance growth is operational cost. Before adding any rule, process, or structure, ask: does this increase operational surface unnecessarily?" | Agregar una capa de gobernanza — aunque sea "temporal" — aumenta la superficie operativa. |
| RFC-007 §Authority Hierarchy | Governance > Deterministic Infrastructure > Reflection > Intelligence > External Platforms | ¿Dónde se ubica esta "temporary governance layer"? Si está al nivel de Governance, duplica RFC-007. Si está abajo, no es governance — es tooling. |
| RFC-007 §Human Sovereignty | "Humans own capital allocation, production authorization, freeze approval, risk exposure" | La capa propuesta introduce un intermediario (scripts/Hermes/governance layer) entre el humano y el pipeline. Esto difumina la línea de autoridad. |

Conclusión: El término "Operational Governance Layer" es un misnomer. Lo que realmente necesitamos no es governance nuevo — es tooling determinístico de pre-vuelo. Scripts. No governance. No capas. No Hermes.

### 2.2 La arquitectura YA cubre todo lo necesario

| Responsabilidad | ¿Quién la cubre hoy? | ¿Falta algo? |
| --- | --- | --- |
| Ejecutar sesiones | PaperTradingSession (REQ-PT-001) | No |
| Validar contratos | contracts.py (REQ-PT-002) | No |
| Aislar operaciones | REQ-PT-003 (import boundary) | No |
| Coordinar servicios | REQ-PT-004 (direct Python import) | No |
| Bundling de evidencia | REQ-PT-005 | No |
| CLI interface | REQ-PT-006 | No |
| Error handling | REQ-PT-007 | No |
| 30-day lifecycle | REQ-PT-008 | No |
| Seleccionar markets | ❌ Gap — ACTIVE_MARKETS es string vacío | SÍ — este es el ÚNICO gap real |
| Validar markets antes de captura | ❌ Gap — PRE_FLIGHT no valida market_ids no vacío | SÍ — detectado en Q5 del review anterior |

Conclusión: Hay exactamente DOS gaps operativos. Ambos se resuelven con scripts determinísticos. Ninguno requiere AI, governance nuevo, ni capas adicionales.

Estado: READY TO FREEZE (el assessment de que los gaps son mínimos)

## 3. Counterarguments — Destruyendo nuestras propias hipótesis

### 3.1 "Hermes debería descubrir markets"

Counter: ¿Qué hace "descubrir markets" exactamente?

1. Llamar a GET /markets de Polymarket → operación HTTP determinística
2. Filtrar por active=true, closed=false → filtro booleano determinístico
3. Filtrar por categoría (football) → filtro de string determinístico
4. Filtrar por tipo de mercado (winner) → filtro de string determinístico
5. Ordenar por volumen → sort numérico determinístico
6. Tomar top N → slice determinístico

Cada uno de estos pasos es una operación determinística. Ninguno requiere reasoning, pattern matching, semantic understanding, o cualquier capacidad que justifique AI. Un script de 50 líneas en Python hace exactamente lo mismo, con:

- ✅ Misma salida para misma entrada (A1)
- ✅ Trazabilidad completa (RFC-000 §Auditability)
- ✅ Cero latencia de LLM
- ✅ Cero costo de tokens
- ✅ Cero riesgo de alucinación

Hermes en market discovery es arquitectónicamente indefendible. Viola RFC-005 §Proposal-Only Doctrine ("Intelligence outputs are proposals") porque estaría tomando una decisión operativa (qué markets tradear), no generando una propuesta para revisión humana.

### 3.2 "Hermes debería evaluar candidates"

Counter: ¿Evaluar contra qué? Si las políticas de evaluación son frozen (liquidez mínima, volumen mínimo, antigüedad del mercado), la "evaluación" es aplicar thresholds numéricos. Eso es código determinístico, no AI.

Si las políticas NO están definidas, el problema no es que falte Hermes — el problema es que falta definir las políticas. Hermes no debería inventar políticas de evaluación. Eso es governance authority (RFC-007: "Governance owns risk authorization").

### 3.3 "Una capa de gobernanza temporal es necesaria para generar evidencia"

Counter: La evidencia YA se genera. SessionReport, contracts.json, manifest.json, reflection_reports. El Paper Trading Spec (REQ-PT-005, REQ-PT-008) ya define exactamente qué evidencia se produce y dónde se persiste.

Agregar una "governance layer" no genera más evidencia — genera más artifacts que auditar. Viola A6: "Before adding any rule, process, or structure, ask: does this increase operational surface unnecessarily?"

### 3.4 "Es temporal, se remueve después"

Counter: Lo "temporal" en software rara vez lo es. Una capa de gobernanza, una vez integrada en el workflow operativo, crea dependencia. El operador se acostumbra. Los scripts asumen su existencia. Removerla después requiere migration.

Además, el Constitution B4 (Stabilization Progression) dice: "Mutation should become increasingly constrained after freezes, audits, production promotion." Introducir una capa que sabés que vas a remover es arquitectura desechable — anti-patrón.

Estado: NEEDS GOVERNANCE DECISION

## 4. Risks

| Riesgo | Severidad | Descripción |
| --- | --- | --- |
| Governance duplication | HIGH | Una "temporary governance layer" compite con RFC-007 por autoridad. Dos fuentes de verdad sobre quién gobierna qué → drift operativo. |
| AI authority creep | HIGH | Si Hermes participa en market discovery, el límite entre "assistance" y "decision" se desdibuja. El próximo paso natural será "Hermes ya selecciona markets, ¿por qué no ejecuta sesiones?" → Fase 8 prematura. |
| Complexity without evidence | MEDIUM | No hay evidencia de que el workflow actual (humano edita .env → session) haya fallado. Estamos diseñando una solución para un problema que no hemos observado. Viola A7. |
| Token cost sin ROI | LOW | Hermes consumiendo tokens para filtrar una API response es literalmente quemar plata para hacer lo que jq hace en 3 líneas. |
| Removal friction | MEDIUM | Si la capa se integra en tooling, CI, o documentación operativa, removerla después requiere migration effort. |

Estado: NEEDS GOVERNANCE DECISION

## 5. Simplification Opportunities

### 5.1 Eliminar "Operational Governance Layer" como concepto

No es governance. Es tooling. Llamémoslo lo que es: Pre-Flight Toolchain.

| Concepto actual | Simplificación |
| --- | --- |
| Operational Governance Layer | → scripts/pre_flight/ (3 archivos Python) |
| Market Discovery Policy | → discover_markets.py — query API, filtrar, output CSV |
| Candidate Evaluation Policy | → evaluate_candidates.py — aplicar thresholds, output report |
| Source of Truth Update | → update_markets.py — escribir .env |
| "Governance contracts" | → Ya existen en contracts.py (REQ-PT-002) |

### 5.2 Colapsar los 7 contratos operativos en 2

De los 7 contratos propuestos (C1-C7), varios son redundantes con lo que ya existe:

| Contrato | ¿Ya existe? | Acción |
| --- | --- | --- |
| C1: Market Selection | Parcialmente — ACTIVE_MARKETS existe pero vacío | KEEP — pero como tooling, no governance |
| C2: Market Lifecycle | No | KEEP — responsabilidad del operador |
| C3: Domain Taxonomy | No | KEEP — necesario para no contaminar datos |
| C4: Pre-Flight Validation | Parcialmente — contracts.py ya existe | MERGE con REQ-PT-002 como nuevo contrato ACTIVE_MARKETS_CONFIGURED |
| C5: Operator Sovereignty | YA EXISTE — RFC-007 §Human Sovereignty | ELIMINAR — es redundante |
| C6: Infrastructure Portability | YA EXISTE — RFC-000 §Infrastructure Isolation | ELIMINAR — es redundante |
| C7: Empty Market Policy | YA EXISTE — A4 (Fail-Fast) + evidence guard | ELIMINAR — ya está implementado |

Resultado: 7 contratos → 3 necesarios (C1, C2, C3) + 1 merge a spec existente (C4). Los otros 3 ya están cubiertos por frozen artifacts.

Estado: READY TO FREEZE (la simplificación)

## 6. Component Elimination Opportunities

Componentes que deberían eliminarse del diseño actual

| Componente | Justificación para eliminar |
| --- | --- |
| Hermes en market discovery | Zero value. API query + filter es determinístico. Viola RFC-005: "Intelligence assists operations. It does not own operations." |
| Hermes en candidate evaluation | Zero value. Aplicar thresholds numéricos no requiere AI. Viola RFC-005: "Intelligence systems do NOT own execution authority." |
| "Temporary Operational Governance Layer" | No es governance. Es tooling. Viola A6. Duplica RFC-007. |
| Governance Contracts C5, C6, C7 | Redundantes con RFC-007, RFC-000, y Constitution A4 respectivamente. |
| Candidate Generation como paso separado | Es indistinguible de Market Discovery + Candidate Evaluation. Colapsar en un solo paso: "Market Selection". |

Lo que SOBREVIVE al challenge

| Componente | Por qué sobrevive |
| --- | --- |
| 3 scripts determinísticos | Resuelven los gaps reales sin introducir governance, AI, ni complejidad |
| Domain Taxonomy (C3) | Gap real — sin taxonomy, domain es string arbitrario. Pero debe ser un archivo de configuración, no un "contrato de gobernanza" |
| PRE_FLIGHT validation de markets (C4) | Gap real — el pipeline no debería llegar a CAPTURING con market_ids vacío |
| Operador humano como autoridad | Ya existe (RFC-007), solo se reafirma |
| Hermes en reflection/post-execution | Ya existe (RFC-005), no se toca |

Estado: READY TO FREEZE (eliminaciones)

## 7. Analysis of the Seven Operational Contracts

### Q1: Market Selection Policy

¿Quién descubre markets? Un script determinístico: GET /markets → filtrar → output.

¿Quién genera candidates? El mismo script o uno encadenado. La distinción "discovery vs generation" es artificial — es el mismo pipeline de filtrado.

¿Requiere AI? NO. Cada paso es una transformación determinística de datos.

¿Pueden scripts determinísticos reemplazar a Hermes completamente? SÍ. Y deben hacerlo.

→ RECOMENDACIÓN: 1 script discover_markets.py. Input: domain (FOOTBALL-WINNER). Output: CSV de Condition IDs con metadata (volumen, liquidez, fecha de creación).

Estado: READY TO FREEZE

### Q2: Condition Lifecycle Policy

¿Cómo monitorear Condition IDs? El script discover_markets.py se ejecuta bajo demanda (semanal o pre-sesión). Si un market desaparece de /markets (resuelto), no aparece en el output. El operador lo detecta al revisar el diff contra el .env actual.

¿Cómo reemplazar markets expirados? El operador revisa el output del script y actualiza .env. Esto es explícito, trazable, y reversible.

¿Es operational governance o future architecture? Es operational. No requiere nuevos contratos, solo tooling.

→ RECOMENDACIÓN: El operador ejecuta discover_markets.py → revisa output → actualiza .env → commitea el cambio. Cero magic.

Estado: READY TO FREEZE

### Q3: Discovery Scheduling Policy

¿Deberían estar separados discovery, capture, monitoring, y lifecycle?

SÍ. Y YA LO ESTÁN. La arquitectura actual los separa implícitamente:

| Actividad | Frecuencia | Dueño | Capa arquitectónica |
| --- | --- | --- | --- |
| Discovery | Bajo demanda | Script + humano | Tooling (no es capa arquitectónica) |
| Capture | Per-sesión | EventCapture | Adapters |
| Execution | Per-sesión | ExecutionEngine | Core |
| Reflection | Per-sesión | ReflectionEngine | Reflection |
| Monitoring (market health) | No implementado | — | No necesario en Fase 5 |

La separación es correcta. No requiere formalización adicional.

→ RECOMENDACIÓN: Mantener la separación implícita actual. No crear un "Discovery Scheduling Policy" — es over-engineering para 30 días.

Estado: READY TO FREEZE

### Q4: Experimental Domain Policy

¿Es FOOTBALL-WINNER el scope correcto?

SÍ. La evidencia del review anterior sigue siendo válida:

- Reduce variables (A5)
- Acelera calibración (A7)
- Mercados binarios con resolución en 90 minutos = ciclo de feedback rápido

¿Debería congelarse el domain taxonomy YA?

No como "taxonomy" completo. Basta con un valor concreto: FOOTBALL-WINNER para los 30 días. Si el experimento funciona, el taxonomy se diseña en Fase 6 (Multi-Domain) con datos reales, no con especulación.

→ RECOMENDACIÓN: FOOTBALL-WINNER como domain string único para los 30 días. No diseñar taxonomy ahora.

Estado: READY TO FREEZE

### Q5: Failure Policy

Revisión de cada gate operativo:

| Gate | ¿Funciona? | Hallazgo |
| --- | --- | --- |
| CLI --markets vacío → exit 0 | ❌ | Falso positivo. Debería ser exit 1. Detectado en review anterior. |
| EventCapture.start() con market_ids vacío | ✅ | ValueError → fail-fast |
| Evidence guard: 0 eventos post-capture | ✅ | CRITICAL ERROR → correcto |
| PRE_FLIGHT contracts | ✅ | DRY_RUN, NO_REAL_FUNDS, TEMPORAL_INTEGRITY |
| VERIFYING contracts | ✅ | EVIDENCE_COMPLETENESS, DETERMINISTIC_REPRODUCIBILITY |

Único gap: el CLI gate silencioso en main.py:247-249. Pero esto es un bug de implementación, no un problema de governance.

→ RECOMENDACIÓN: No crear nuevas políticas de failure. Arreglar el exit code en main.py (de 0 a 1 cuando no hay markets). El resto funciona.

Estado: NEEDS DISCOVERY (el bug específico en main.py necesita fix, no policy)

### Q6: Operational Authority Policy

¿Dónde reside la autoridad?

| Capa | Dueño | Autoridad |
| --- | --- | --- |
| Governance | RFC-007 + humano | Freeze, rollout, capital, riesgo, deployment |
| Deterministic Execution | PaperTradingSession + engine | Ejecutar sesiones, validar contratos, generar evidencia |
| AI Assistance | Hermes (RFC-005) | Reflection augmentation, summarization, anomaly detection |
| Operational Automation | Scripts determinísticos | Market discovery, candidate filtering (herramientas del operador) |

¿Hermes posee alguna autoridad durante Paper Trading?

NO. Y no debería. RFC-005 es explícito: "Hermes is an integration layer. Not system authority." Cualquier autoridad que se le otorgue a Hermes en el workflow operativo viola:

- RFC-005 §Initial Role: "NOT: unrestricted execution, autonomous governance, architectural ownership"
- RFC-007 §Human Sovereignty: "Humans own capital allocation, production authorization"
- RFC-000 §Intelligence Containment: "Intelligence systems must remain operationally sandboxed"

→ RECOMENDACIÓN: Hermes permanece en su rol RFC-005: reflection augmentation post-ejecución. Zero autoridad operativa. Zero participación en market selection.

Estado: READY TO FREEZE

### Q7: Infrastructure Policy

¿Es suficiente la portabilidad actual?

SÍ. El análisis del review anterior se mantiene. La arquitectura es provider-agnostic por diseño (Fase 0). No se requieren contratos adicionales.

→ RECOMENDACIÓN: No crear nuevos contratos de infraestructura. Los existentes (RFC-000 §Infrastructure Isolation, Constitution B2) son suficientes.

Estado: READY TO FREEZE

## 8. Does Hermes Provide Enough Value to Justify Its Existence During Paper Trading?

En el workflow pre-trading (market selection): NO.

Hermes no agrega valor en:

- Market discovery → API call + filtros
- Candidate evaluation → thresholds numéricos
- Source of Truth update → escritura de archivo

Cada una de estas operaciones es:

- Determinística: mismo input → mismo output
- Verificable: podés auditar el output contra los inputs
- Simple: <100 líneas de Python
- Gratis: cero tokens, cero latencia de LLM

Introducir Hermes aquí es arquitectónicamente dañino:

- Viola RFC-005 (Hermes no es execution authority)
- Viola A5 (Simplicity Doctrine)
- Viola A6 (Governance Minimalism)
- Viola A1 (agrega no-determinismo donde no hace falta)

En el workflow post-trading (reflection): SÍ.

Hermes YA agrega valor en su rol definido por RFC-005:

- Reflection augmentation → enriquece los reflection reports
- Operational summarization → comprime sesiones para el operador
- Anomaly interpretation → ayuda a detectar patrones anómalos
- Proposal generation → sugiere ajustes de parámetros

Este rol no se toca. Hermes sigue haciendo exactamente lo que RFC-005 define. La diferencia es que NO se expande su scope al workflow pre-trading.

Conclusión

Paper Trading sin Hermes en pre-trading: ✅ Mejor (más determinístico, más simple)

Paper Trading con Hermes en pre-trading: ❌ Peor (no-determinismo innecesario, viola RFC-005)

Paper Trading con Hermes en post-trading: ✅ Correcto (es su rol diseñado)

→ RECOMENDACIÓN: Remover a Hermes completamente del workflow pre-trading. Mantenerlo exclusivamente en reflection/post-ejecución.

Estado: NEEDS GOVERNANCE DECISION

## 9. Can the Entire Workflow Become Deterministic?

SÍ. Y ya lo es, excepto por los gaps de tooling.

Workflow determinístico completo para los 30 días:

DÍA N:

1. [SCRIPT] discover_markets.py --domain FOOTBALL-WINNER
   → output: candidates.csv (Condition IDs + metadata)
   → determinístico: mismo input → mismo output

2. [HUMANO] Revisa candidates.csv
   → decide cuáles incluir (governance authority)
   → edita .env: TRADY_AI_ACTIVE_MARKETS=0xabc,0xdef

3. [PIPELINE] trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive
   → PRE_FLIGHT → CAPTURING → EXECUTING → REFLECTING → VERIFYING → BUNDLING → COMPLETE
   → 100% determinístico (REQ-PT-001 a REQ-PT-008)

4. [HERMES] Reflection engine (post-ejecución)
   → analyze outcomes, detect anomalies, generate proposals
   → rol RFC-005 — sin cambios

5. [EVIDENCIA] paper_trading/dia-NNN/
   → session_report.json + contracts.json + manifest.json

Cada paso es determinístico. El ÚNICO punto donde entra juicio humano es el paso 2 (selección final de markets) — y eso es correcto según RFC-007 (Human Sovereignty).

Zero AI en el critical path pre-trading. Zero governance nuevo. Zero capas adicionales.

→ RECOMENDACIÓN: Adoptar este workflow como el estándar operativo para los 30 días.

Estado: READY TO FREEZE

## 10. Recommended Operational Governance Layer for the 30-Day Campaign

Corrección: no es un "Governance Layer". Es un "Pre-Flight Toolchain".

```text
scripts/pre_flight/
├── discover_markets.py    # GET /markets → filtrar → candidates.csv
├── evaluate_candidates.py # aplicar thresholds → report
└── README.md              # operador: cómo usar estas herramientas
```

Contratos operativos MÍNIMOS (3, no 7):

### OC-1: Market Source of Truth

- TRADY_AI_ACTIVE_MARKETS en .env como única fuente
- Formato: CSV de Condition IDs
- Actualización: manual por el operador, asistido por discover_markets.py

### OC-2: Domain Scope

- Primer experimento: FOOTBALL-WINNER
- Markets: exclusivamente "Winner (Full Time)" en Polymarket
- Duración: 30 días calendario

### OC-3: Pre-Flight Validation

- PRE_FLIGHT debe validar market_ids no vacío
- Fallback: ERROR explícito (no exit 0)
- Esto es un merge a REQ-PT-002 (spec change, no governance nuevo)

Lo que NO se crea:

- ❌ "Operational Governance Layer" como concepto
- ❌ Hermes en market discovery/evaluación
- ❌ Contratos C5, C6, C7 (redundantes con RFCs existentes)
- ❌ Domain taxonomy completo (esperar a Fase 6)
- ❌ Discovery scheduling policy (over-engineering)

Lo que SÍ se hace:

- ✅ 3 scripts determinísticos en scripts/pre_flight/
- ✅ 3 contratos operativos mínimos (no governance, solo documentación)
- ✅ 1 merge a spec existente (OC-3 → REQ-PT-002)
- ✅ 1 bug fix (main.py exit code)

### Final Verdict

| Componente | Decisión |
| --- | --- |
| "Temporary Operational Governance Layer" | ELIMINAR — no es governance, es tooling |
| Hermes en pre-trading | ELIMINAR — zero value, viola RFC-005 |
| 7 contratos operativos | COLAPSAR a 3 — el resto son redundantes |
| Workflow determinístico | ADOPTAR — 100% determinístico, zero AI en critical path |
| Pre-Flight Toolchain | CREAR — 3 scripts, sin governance nuevo |
| Domain: FOOTBALL-WINNER | CONFIRMAR — scope correcto para 30 días |
| Hermes en post-trading | MANTENER — sin cambios, rol RFC-005 |

El pipeline de Paper Trading es determinístico. Mantenelo determinístico. No le pongas AI donde no hace falta.

Deterministic-First no es un eslogan.

Es un constraint arquitectónico.

Cada vez que ponés AI en un critical path determinístico,
estás violando el constraint más fundamental del proyecto.

Estado general: NEEDS GOVERNANCE DECISION (el equipo debe decidir si adopta este enfoque minimalista o insiste en la capa de gobernanza temporal)