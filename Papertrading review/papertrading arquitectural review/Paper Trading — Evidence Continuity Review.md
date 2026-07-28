# Paper Trading — Evidence Continuity Review

## 1. Did the Previous Review Conflate Governance with Evidence Continuity?

SÍ. Cometí ese error. Y la distinción del usuario es arquitectónicamente correcta.

**Lo que yo analicé (incorrectamente)**

Traté "market rotation" como un solo concepto monolítico: seleccionar un Condition ID → governance → prohibido. Pero market rotation tiene DOS variantes arquitectónicamente distintas que colapsé en una:

| Variante | Qué hace | Dónde reside |
| --- | --- | --- |
| Strategic Selection | Elige el "mejor" mercado (mayor liquidez, mejor volatilidad, más profit potencial) | Governance — RFC-007 §Human Sovereignty |
| Evidence Continuity | Detecta que el mercado actual expiró y busca CUALQUIER mercado válido para que el experimento no se detenga | Operaciones — RFC-000 §Operational Survivability |

Son arquitectónicamente distintas. La primera requiere juicio. La segunda requiere solo ejecutar reglas frozen.

**Evidencia de la conflation**

Mi análisis anterior dijo:

> "Seleccionar qué Condition IDs entran al pipeline de trading — incluso en dry_run — es capital allocation. Estás decidiendo a qué mercados asignar el paper capital del sistema."

Esto asume que seleccionar = elegir el mejor. Pero si las reglas son frozen ("cualquier football winner market activo"), seleccionar es solo aplicar un filtro. No hay juicio. No hay preferencia. No hay optimización. Solo continuidad.

La distinción es análoga a:

- Strategic: "Contrato a Messi porque es mejor que los otros delanteros" → governance
- Continuity: "Necesito 11 jugadores en la cancha. El que estaba se lesionó. Que entre el próximo disponible de la lista pre-aprobada." → operaciones

**Corrección**

El pipeline NO debería elegir qué mercado es mejor. Pero SÍ debería poder garantizar que siempre hay al menos un mercado activo para seguir recolectando datos. La primera es governance. La segunda es operational continuity — y los RFCs no solo la permiten, la EXIGEN.

**Estado:** NEEDS GOVERNANCE DECISION (reconocer la corrección)

## 2. Strategic Selection vs Continuous Evidence Acquisition

**Tabla comparativa**

| Dimensión | Strategic Market Selection | Continuous Evidence Acquisition |
| --- | --- | --- |
| Objetivo | Maximizar profit / calidad de señal | No detener la recolección de datos |
| Pregunta que responde | "¿Cuál es el MEJOR mercado?" | "¿Hay ALGÚN mercado válido disponible?" |
| Requiere ranking? | Sí — comparar mercados entre sí | No — basta con encontrar el primero que cumpla reglas frozen |
| Requiere optimización? | Sí | No |
| Requiere AI? | Podría (pero no en esta fase) | No — es un filtro determinístico |
| Si falla | Se tradea un mercado subóptimo | Se pierden sesiones de datos |
| Severidad del fallo | Baja (en dry_run paper trading) | Alta — compromete la calibración del experimento |
| Dueño arquitectónico | Governance (RFC-007) | Operational Continuity (RFC-000, RFC-009) |
| ¿Debe ser automático? | No en Fase 5 | Sí — su ausencia es un riesgo operativo para el experimento |

**¿Por qué son responsabilidades distintas?**

**RFC-000 §Operational Survivability:**

> "Long-term survivability has higher priority than growth speed, autonomy expansion, orchestration sophistication. The architecture prioritizes sustainable evolution, operational containment, bounded complexity, recoverability, auditability."

Un pipeline que se detiene porque expiró un Condition ID NO es "operationally survivable." Es frágil. La continuidad de evidencia ES survivability — el experimento de 30 días sobrevive solo si sigue recolectando datos.

**RFC-009 §Operational Continuity:**

> "The infrastructure exists to preserve operational continuity, preserve bounded intelligence integration, support multi-platform execution."

Preservar continuidad operativa es una responsabilidad EXPLÍCITA de la infraestructura. No es governance — es runtime.

**Estado:** READY TO FREEZE (la distinción es arquitectónicamente sólida)

## 3. Does Automatic Evidence Continuity Violate Any Frozen RFC?

Voy a auditar cada constraint relevante:

### RFC-000 — Operational Safety

| Doctrina | ¿Violación? | Evidencia |
| --- | --- | --- |
| Least Privilege | No | El pipeline solo modifica .env (configuración, no capital, no wallets, no secrets). |
| Runtime Hardening | No | La rotación es un script explícito, pre-sesión, con salida a stderr. No es hidden, no es daemon, no es background. |
| Deterministic Safety | No | Reglas frozen → output determinístico. Mismo .env + mismo estado de Polymarket → mismo mercado seleccionado. |
| Blast Radius Minimization | No | Si falla → no se selecciona mercado → siguiente sesión reintenta. No afecta DB, no afecta capital, no afecta secrets. |
| Fail-Fast | Lo refuerza | Si no hay mercados disponibles → error explícito → log → el operador lo ve. Mejor que "silencio por 3 días hasta que el humano revisa." |

### RFC-002 — Platform Integration

| Doctrina | ¿Violación? | Evidencia |
| --- | --- | --- |
| Adapter Doctrine | No | Usa PolymarketAdapter.get_markets() — método EXISTENTE del adapter. No nuevo endpoint, no nueva integración. |
| Platform Isolation | No | El adapter ya está isolado. La rotación no crea nuevo acoplamiento. |

### RFC-007 — Governance Hardening

| Doctrina | ¿Violación? | Evidencia |
| --- | --- | --- |
| Human Sovereignty | No — si se interpreta correctamente | El humano retiene: (1) definición de reglas frozen, (2) domain scope (FOOTBALL-WINNER), (3) override authority. La rotación es ejecución de reglas humanas, no creación de reglas nuevas. |
| Approval Doctrine | No | La activación de un nuevo mercado bajo reglas PRE-APROBADAS no es una "operationally meaningful mutation" nueva — es la misma decisión ya aprobada, aplicada a una nueva instancia. |
| Bounded Autonomy | Cumple | "Limited autonomy may exist only inside explicitly approved boundaries." Las reglas frozen SON el explicitly approved boundary. |
| Capital Allocation | No aplica | No hay decisión de cuánto capital asignar. El position size es fijo (default_position_size: "10.00"). El pipeline no decide "más a este mercado, menos a aquel." |

### RFC-008 — Autonomous Coordination

| Doctrina | ¿Violación? | Evidencia |
| --- | --- | --- |
| Fase 8 | No | Esto NO es autonomous coordination. Es operational continuity. RFC-008 gobierna sistemas que schedulan, coordinan, y secuencian workflows. Un script que chequea "¿sigue activo este market?" y rota si no es un healthcheck, no un coordinator. |
| Bounded Coordination | No aplica | No hay coordinación de múltiples sistemas — es un solo pipeline con un solo mercado. |

### Constitution

| Principio | ¿Violación? | Evidencia |
| --- | --- | --- |
| A1 (Deterministic-First) | No | Reglas frozen + API determinística → output determinístico. |
| A3 (Boundary Discipline) | No | Discovery (Adapter), Filter (Policy), Select (Pipeline), Update (Config). Cada paso tiene dueño claro. |
| A5 (Simplicity) | Cumple | ~30 líneas de Python vs perder 12-24 sesiones de datos porque el humano no revisó a tiempo. |
| A7 (Validate Uncertainty) | Lo refuerza | Más datos = mejor validación. Si el pipeline se detiene, la validación es más débil. |
| A8 (Evidence Before Complexity) | Lo refuerza | La rotación automática GENERA más evidencia. No la reemplaza. |

**Conclusión del audit**

Cero violaciones. Cero conflictos. La evidencia continuity automática no solo es compatible con los RFCs — es una consecuencia natural de RFC-000 §Operational Survivability y RFC-009 §Operational Continuity.

Lo que SÍ violaría los RFCs: un pipeline que se detiene silenciosamente durante días porque un Condition ID expiró, perdiendo datos que el experimento necesita para calibrarse. ESO es riesgo operativo.

**Estado:** READY TO FREEZE

## 4. Three-Hour vs Six-Hour Execution Rhythm

El contexto cambió. La pregunta anterior era "¿cuál balancea costo y cobertura?" La pregunta ahora es "¿cuál maximiza evidencia para calibración?"

**Evidencia cuantitativa**

| Métrica | Cada 3 horas | Cada 6 horas | Diferencia |
| --- | --- | --- | --- |
| Sesiones/día | 8 | 4 | 2× |
| Sesiones/30 días | 240 | 120 | 2× |
| Tamaño de muestra | 240 data points | 120 data points | 2× |
| Intervalo de confianza | ~6.3% (1/√240) | ~9.1% (1/√120) | 1.44× más ajustado |
| Cobertura durante partido (2h) | 1-2 snapshots | 0-1 snapshots | Crítico para capturar resolución |
| Runtime diario | 560s (9 min) | 280s (5 min) | Diferencia insignificante |
| API calls (WS connects) | 8/día | 4/día | Diferencia trivial |
| DB growth | ~800-8000 filas/día | ~400-4000 filas/día | SQLite maneja ambos sin problemas |
| Infraestructura | Mismo VPS | Mismo VPS | Cero diferencia |

**Análisis**

No hay razón arquitectónica para preferir 6 horas sobre 3. La única razón anterior era "operational cost" — que el usuario explícitamente descarta como preocupación.

El factor crítico es la cobertura durante la ventana del partido. Un mercado de fútbol winner market resuelve en ~90 minutos. Con 6 horas, es posible que una sesión caiga 1 hora antes del partido y la siguiente 5 horas después (cuando ya resolvió). Te perdiste TODO el movimiento de precio durante el partido. Con 3 horas, la ventana máxima entre sesiones es 3 horas → al menos 1 snapshot cae DENTRO del partido o muy cerca del silbatazo final.

Para calibración, los datos DURANTE el partido son los más valiosos: es donde el precio converge de probabilidad a certeza (0 o 1). Perder esa ventana es perder la señal más fuerte.

**Veredicto**

3 horas. El doble de datos para calibración. Cero costo arquitectónico adicional. La diferencia en cobertura de resolución de mercados es material para la calidad del experimento.

`cron: 0 */3 * * *`

**Estado:** READY TO FREEZE

## 5. Architectural Recommendation

**Diseño: Pre-Session Continuity Guard**

No es un "coordinator." No es un "rotation engine." Es un guardián de continuidad — un script que corre ANTES de cada sesión y garantiza que hay al menos un market activo.

`cron cada 3 horas:`

1. `python scripts/ensure_active_market.py --domain FOOTBALL-WINNER`
   - Lee ACTIVE_MARKETS de .env
   - Para cada market: chequea si expiró (REST: GET /market/{id} → closed?)
   - Si TODOS expiraron:
     - GET /markets → filtrar por FOOTBALL-WINNER
     - Aplicar reglas frozen: active=true, closed=false, football winner
     - Tomar el primero disponible (no ranking, no optimización)
     - Escribir .env: TRADY_AI_ACTIVE_MARKETS=<nuevo_id>
     - Log: "rotated market: 0xOLD → 0xNEW"
   - Si al menos 1 sigue activo → no hace nada

2. `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive`
   - Lee .env (fresco, recién actualizado si hubo rotación)
   - Ejecuta sesión normalmente

**¿Por qué PRE-sesión y no DENTRO de la sesión?**

1. Settings frozen: get_settings() es @lru_cache. Si la rotación ocurriera dentro de run_session(), el proceso ya tendría los Settings viejos en memoria. Modificar .env no los actualizaría sin cache_clear() — runtime mutation.
2. Separación de concerns: El guardián de continuidad es operational infrastructure. La sesión es execution pipeline. Juntarlos viola A3.
3. Failure isolation: Si el guardián falla (API down, no hay markets), la sesión ni siquiera arranca. Si la sesión falla (WS disconnect), el guardián ya hizo su trabajo.
4. Testeabilidad: El guardián se prueba independientemente. La sesión no necesita saber que existe.

**Reglas frozen para el guardián**

```python
# Reglas congeladas ANTES de Day 0 por el operador humano:

ELIGIBILITY_RULES = {
    "domain": "FOOTBALL-WINNER",
    "active": True,
    "closed": False,
    "tags": ["football", "winner"],  # de la respuesta de Polymarket
}

# El guardián NO rankea, NO compara, NO optimiza.
# Simplemente toma el primer mercado que cumple TODAS las reglas.
```

El humano define las reglas UNA vez antes de Day 0. El guardián las aplica determinísticamente durante 30 días. Si las reglas necesitan ajuste, el humano las modifica en su ventana de revisión.

**¿Qué pasa si no hay mercados disponibles?**

- `ensure_active_market.py → exit 1`
- cron detecta exit ≠ 0 → loguea failure
- próxima ejecución (3h después) → reintenta
- operador ve el log en su ventana de revisión

Fail-fast, observable, recoverable. Exactamente lo que RFC-000 exige.

**Estado:** READY TO FREEZE

## 6. Final Verdict

**Corrección del análisis anterior**

| Claim anterior | Corrección |
| --- | --- |
| "Market rotation es capital allocation" | Strategic selection es capital allocation. Evidence continuity es operational survivability. Son distintas. |
| "Rotación automática viola RFC-007" | No viola RFC-007 si las reglas son frozen por el humano. La rotación es ejecución, no decisión. |
| "Rotación automática debe esperar a Fase 8" | No es autonomous coordination (Fase 8). Es operational continuity (aplica a cualquier fase). |

**Lo que SÍ se mantiene del análisis anterior**

| Claim | Estado |
| --- | --- |
| Hermes fuera del critical path | ✅ Correcto |
| Sin governance nuevo | ✅ Correcto |
| Sin AI en decisiones de selección | ✅ Correcto |
| Sin optimización de profit | ✅ Correcto |
| Pipeline determinístico | ✅ Correcto |
| Operador humano como governance authority | ✅ Correcto |

**Arquitectura operativa final**

```text
┌────────────────────────────────────────────────────────────┐
│               VPS — cron cada 3 horas                       │
│                                                            │
│  1. ensure_active_market.py (GUARDIÁN DE CONTINUIDAD)       │
│     ├─ ¿Markets actuales expiraron?                         │
│     ├─ Sí → Descubrir, filtrar con reglas frozen,           │
│     │        tomar el primero, actualizar .env              │
│     └─ No → continuar                                      │
│                                                            │
│  2. trady-ai paper-trade session                            │
│     --domain FOOTBALL-WINNER --non-interactive              │
│     → PRE_FLIGHT → CAPTURING → ... → BUNDLING              │
│                                                            │
│  Output: paper_trading/dia-NNN/session_report.json          │
│          + contracts.json + manifest.json                   │
└────────────────────────────────────────────────────────────┘
                         │
                         │ (cada ~7 días)
                         ▼
┌────────────────────────────────────────────────────────────┐
│                   OPERADOR HUMANO                           │
│                                                            │
│  • Revisa bundles acumulados                                │
│  • Ajusta reglas frozen si es necesario                     │
│  • Verifica rotaciones del guardián (logs)                  │
│  • Toma decisiones de governance:                           │
│    - ¿Seguir con FOOTBALL-WINNER?                           │
│    - ¿Ajustar position size?                                │
│    - ¿Cambiar threshold_pct?                                │
│  • NO necesita estar presente para cada sesión              │
│  • NO necesita rotar markets manualmente                    │
└────────────────────────────────────────────────────────────┘
```

**Contratos operativos finales (revisados)**

- **OC-1:** Execution Rhythm → cron: 0 */3 * * * (cada 3 horas, 8 sesiones/día, 240 data points en 30 días)
- **OC-2:** Evidence Continuity → ensure_active_market.py ejecuta PRE-sesión. Reglas frozen por el humano. Sin ranking. Sin optimización. Toma el primer mercado que cumple las reglas.
- **OC-3:** Governance Boundary → El humano define las reglas frozen. El guardián las ejecuta. El humano retiene override authority (editar .env manualmente en cualquier momento).

**Lo que NO cambia**

- ❌ Sin Hermes en critical path
- ❌ Sin governance nuevo
- ❌ Sin AI en selección de mercados
- ❌ Sin optimización de profit
- ❌ Sin ranking de mercados
- ❌ Sin adaptive heuristics

El guardián de continuidad no elige el mejor mercado. Elige el próximo disponible. La diferencia es toda la arquitectura.