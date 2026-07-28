# Paper Trading Operational Readiness Review

Análisis arquitectónico y operativo basado en evidencia del repositorio. No se propone implementación, no se modifica ningún artifact.

---

## Q1: Market Discovery — Source of Truth

### Repository Evidence

| Fuente | Evidencia |
|---|---|
| `settings.py:39` | `active_markets: str = ""` — string vacío como default, parse CSV |
| `.env.example:29` | `TRADY_AI_ACTIVE_MARKETS=` documentado como "REQUIRED for Paper Trading" |
| `main.py:198,246` | Tanto `capture` como `paper_trade session` resuelven markets de `settings.get_active_market_ids()` con fallback al flag `--markets` |
| `RFC-000 §Infrastructure Isolation` | "infrastructure lock-in" rechazado explícitamente; "operational sovereignty must remain internal" |
| `RFC-006 §Domain Isolation` | PM-5M definido como dominio inicial de predicción; dominios son "operationally isolated" |
| `polymarket.py:380-399` | `EventCapture.start()` requiere `market_ids` no vacío; si está vacío, lanza `ValueError` |
| `session.py:145-165` | Evidence guard: si capture produce 0 eventos → CRITICAL ERROR |

### Análisis

**Manual (`TRADY_AI_ACTIVE_MARKETS`):**
- ✅ **Determinismo máximo**: la lista de markets es explícita, versionable, y reproducible. Alineado con A1 (Deterministic-First Execution) y A4 (Fail-Fast).
- ✅ **Simplicidad operativa**: un string en `.env`, sin lógica de descubrimiento, sin dependencias adicionales. Alineado con A5 (Simplicity Doctrine) y B2 (Integration Hostility).
- ✅ **Auditabilidad**: cada sesión sabe exactamente qué markets usó. Alineado con RFC-000 §Auditability.
- ❌ **Mantenibilidad**: requiere intervención humana cada vez que un Condition ID expira. El operador debe conocer los IDs — no hay abstracción.

**Automático (discovery vía `get_markets()` de Polymarket):**
- ✅ **Cero intervención humana** para rotación.
- ❌ **No determinístico**: `get_markets()` devuelve el estado actual de Polymarket, que cambia minuto a minuto. Dos sesiones en días distintos pueden capturar markets diferentes sin que el operador lo sepa. Viola A1.
- ❌ **Superficie operativa nueva**: el discovery se vuelve runtime behavior acoplado a la API de Polymarket. Viola B2.
- ❌ **Complejidad innecesaria en Fase 5**: el roadmap dice que Fase 5 es Intelligence Integration, no market discovery. Adelantaría complejidad de Fase 6 (Multi-Domain) o Fase 8 (Autonomous Coordination).

**Híbrido:**
- Podría mitigar algunos riesgos si el discovery es explícito, determinístico y traceable (ej: un script offline que genera la lista y el operador la revisa). Pero introduce una capa de tooling adicional sin justificación en este momento. Viola A6 (Governance Minimalism).

### Riesgos operativos

- **Manual**: el operador se olvida de rotar un market expirado → capture produce 0 eventos → session entra en ERROR (evidence guard). Pero esto **es el comportamiento correcto** según A4 (Fail-Fast): es mejor un ERROR explícito que datos silenciosamente vacíos.
- **Automático**: si el discovery selecciona un market con baja liquidez, los datos son ruido estadístico. El pipeline no tiene forma de distinguir ruido de señal sin varias sesiones de calibración. Viola A7 (Validate Uncertainty Before Scaling Complexity).

### Recomendación

**Manual `TRADY_AI_ACTIVE_MARKETS` como Source of Truth para Day 0.** Es la opción de menor superficie operativa, máxima determinismo, y alineada con la filosofía del proyecto. El costo de mantenibilidad (rotación manual de Condition IDs) es aceptable para los 30 días iniciales y fuerza al operador a entender qué está tradeando — alineado con A7.

La evolución hacia descubrimiento automático pertenece a Fase 8 (Autonomous Coordination) o Fase 6 (Multi-Domain), donde el roadmap ya prevé bounded autonomy para scheduling. No debería adelantarse.

---

## Q2: Market Lifecycle — Condition ID Expiration

### Repository Evidence

| Fuente | Evidencia |
|---|---|
| `.env.example:26-29` | `ACTIVE_MARKETS` es un string en `.env` — no hay mecanismo de rotación |
| `session.py:145-165` | Evidence guard: 0 eventos → CRITICAL ERROR |
| `RFC-000 §Least Privilege` | "No component receives unrestricted authority by default" |
| `RFC-007 §Freeze Governance` | "Frozen systems must not mutate implicitly, must not drift operationally" |
| `RFC-008 §Bounded Coordination` | "Autonomous systems may coordinate ONLY inside explicitly approved operational surfaces" |
| `Constitution A4` | "Failures must surface explicitly" |
| `Roadmap Fase 8` | Autonomous Coordination aún no implementada |

### Análisis

La vida de un Condition ID en Polymarket es finita: los mercados se resuelven y dejan de emitir eventos. El pipeline actual no tiene forma de distinguir "market sin actividad temporal" de "market expirado". Ambos producen 0 eventos y disparan el evidence guard.

**¿Quién gestiona el lifecycle?**
- **El pipeline NO**: no es su responsabilidad. El pipeline ejecuta, no selecciona. RFC-004: "Reflection analyzes execution. It does not control execution."
- **El operador humano SÍ**: hoy es quien edita `.env`. Es explícito, traceable y reversible.
- **Hermes en Fase 8**: RFC-008 permite scheduling y coordination bounded, pero Fase 8 no está implementada. Adelantar esta capacidad ahora viola el roadmap.

**¿Cómo reemplazar markets expirados sin violar determinismo?**
- El determinismo aplica al pipeline de ejecución, no a la selección de mercados. Cambiar `ACTIVE_MARKETS` entre sesiones no rompe el determinismo porque cada sesión es autocontenida con su `SessionReport` + `contracts.json` + `manifest.json`.
- Lo que SÍ violaría determinismo: cambiar `ACTIVE_MARKETS` **durante** una sesión (mid-capture). Pero el modelo actual lo impide porque `get_settings()` es singleton inmutable (`frozen=True`).

### Riesgos operativos

- **Market expirado no detectado**: el operador no se entera hasta que la sesión diaria falla. Esto es aceptable según A4 (Fail-Fast) pero genera fricción operativa.
- **Rotación no documentada**: si el operador cambia `ACTIVE_MARKETS` sin registrar qué cambió y por qué, se pierde traceabilidad. Viola RFC-000 §Auditability.

### Recomendación

**El operador humano gestiona el lifecycle durante los 30 días.** Cada rotación debe registrarse como parte del `SessionReport` (el campo `market_ids` ya se pasa a `run_session` — podría persistirse). Esto es consistente con RFC-007 §Human Sovereignty: "Humans own capital allocation, production authorization."

La automatización del lifecycle pertenece a Fase 8 (Autonomous Coordination), donde RFC-008 ya define que autonomy puede "schedule approved workflows" y "coordinate bounded execution sequences" pero nunca "redefine governance" ni "mutate deterministic logic."

---

## Q3: Discovery Frequency vs Capture Frequency

### Repository Evidence

| Fuente | Evidencia |
|---|---|
| `session.py:55-62` | State machine: `PRE_FLIGHT → CAPTURING → EXECUTING → REFLECTING → VERIFYING → BUNDLING → COMPLETE` |
| `session.py:280-311` | `_do_capture()` ejecuta EventCapture por sesión — captura es per-sesión, no continua |
| `RFC-004 §Reflection Scheduling` | "Reflection systems operate across bounded evaluation windows: session, daily, weekly, monthly" |
| `Constitution A3` | "Every boundary must declare: MUST, MUST NOT, MAY. Parsing is not classification. Classification is not analysis." |
| `RFC-008 §Scheduling Philosophy` | "Scheduling exists to preserve operational continuity, coordinate deterministic execution, enforce bounded timing behavior" |

### Análisis

**NO, el discovery no debe ejecutarse con la misma frecuencia que el capture.**

Razones:

1. **Son responsabilidades distintas**: capture es runtime data ingestion (Adapters layer). Market discovery es una decisión de configuración operativa (Governance layer). Mezclarlas viola A3 (Boundary Discipline): "No layer should collapse responsibilities."

2. **Frecuencias naturales distintas**: los Condition IDs de Polymarket viven días o semanas. Los ticks de precio llegan cada milisegundo. Ejecutar discovery en cada captura es desperdicio operativo — viola A5 (Simplicity Doctrine) y B2 (Integration Hostility).

3. **El modelo actual ya separa correctamente**: `ACTIVE_MARKETS` se lee UNA vez al construir `Settings` (singleton inmutable). El capture usa esa lista durante toda la sesión. Esto es correcto.

### Recomendación

**Separación explícita de responsabilidades:**

| Responsabilidad | Frecuencia | Dueño |
|---|---|---|
| Market Discovery (seleccionar qué tradear) | Semanal o bajo demanda | Operador humano (hoy) / Autonomous Coordination (Fase 8) |
| Event Capture (ingerir ticks) | Per-sesión (diario) | `EventCapture` vía `PaperTradingSession` |
| Market Validation (¿sigue activo este market?) | Pre-sesión (PRE_FLIGHT) | Podría agregarse como contrato operativo en `contracts.py` |

Esta separación es consistente con el state machine actual y no requiere cambios arquitectónicos.

---

## Q4: Initial Trading Domain — Football vs Single Market Family

### Repository Evidence

| Fuente | Evidencia |
|---|---|
| `RFC-006 §Initial Domains` | PM-5M definido como "Prediction microtrading" — único dominio inicial documentado |
| `session.py:81` | `domain: str` — el domain es un string libre, no validado contra un registry |
| `main.py:233` | `--domain` required en CLI, default "PM-5M" en `bundle` |
| `Roadmap §Fase 6` | Multi-Domain Expansion es Fase 6 — aún no implementada |
| `Constitution A7` | "Validate uncertainty before scaling complexity. Identify the true risk center early." |
| `Constitution A5` | "Version 1 exists to prove correctness, stability, and operational viability — not to impress." |
| Paper Trading Spec REQ-PT-008 | 30-day lifecycle, calibration readiness al día 30 |

### Análisis

**Football es demasiado amplio para un primer experimento.** Football en Polymarket abarca múltiples tipos de mercado:
- Winner markets (quién gana el partido)
- Over/Under markets (goles totales)
- Correct score markets
- Player props (goleador, asistencias)
- Tournament futures (quién gana el mundial)

Cada familia tiene dinámicas de precio distintas, liquidez diferente, y volatilidad con patrones propios. Mezclarlas en la misma ventana de calibración de 30 días diluye la señal estadística.

**Restringir a una sola familia (Winner Markets):**
- ✅ Reduce variables: mismo tipo de contrato, misma estructura binaria (gana/no gana), misma dinámica de resolución.
- ✅ Acelera calibración: con 30 días y una sola familia, cada sesión contribuye a un baseline coherente. Con 5 familias, necesitás 150 días para el mismo poder estadístico.
- ✅ Alineado con A7: identificar el risk center (¿funciona el pipeline con datos reales?) antes de escalar complejidad (¿funciona con múltiples tipos de mercado?).
- ❌ El paper trading spec no restringe `domain` — `PM-5M` es el default, pero `Football` o `FOOTBALL-WINNER` son strings válidos. Esto es un gap: el spec no define un domain taxonomy.

### Riesgos operativos

- Sin taxonomy de dominios, `domain` es un string arbitrario. Dos sesiones con `PM-5M` y `pm-5m` serían dominios distintos para el reconstruction engine. Viola A3 (Boundary Discipline) — falta validación.
- Football Winner Markets tienen resolución binaria y plazos cortos (90 minutos + injury time). Esto es bueno para calibración rápida pero introduce el riesgo de que los markets se resuelvan antes de que el pipeline capture suficientes ticks.

### Recomendación

**Primer experimento: una sola familia de mercado, explícitamente documentada.** Sugiero `FOOTBALL-WINNER` como domain, con markets de fútbol que sean exclusivamente "Winner (Full Time)" — contratos binarios con resolución en 90 minutos. Esto:

1. Maximiza calidad de evidencia estadística (A7, A8)
2. Minimiza variables (A5)
3. Permite que el reflection engine detecte si el pipeline funciona antes de expandir a otras familias

El domain taxonomy (qué strings son válidos, qué tipos de mercado agrupan) debería ser un contrato operativo congelado antes de Day 0.

---

## Q5: Empty Market Policy

### Repository Evidence

| Fuente | Evidencia |
|---|---|
| `session.py:145-165` | Evidence guard: `event_count == 0` → CRITICAL ERROR, session aborta |
| `polymarket.py:390-391` | `EventCapture.start()`: si `market_ids` vacío → `ValueError` |
| `main.py:199-201` | `capture` command: si no hay markets → imprime mensaje y retorna (no lanza error) |
| `main.py:247-249` | `paper_trade session`: misma lógica — mensaje y retorno |
| `Constitution A4` | "Failures must surface explicitly. Silent corruption is worse than explicit failure." |
| `RFC-000 §Failure Philosophy` | "Fail-fast operational behavior is mandatory" |

### Análisis

La arquitectura actual ya tiene DOS gates donde se puede manifestar el problema:

1. **CLI gate** (`main.py:247-249`): si `market_ids` está vacío al iniciar `paper_trade session`, el comando imprime un mensaje y retorna con exit 0. Esto es un **comportamiento inconsistente**: ni falla ni tiene éxito, simplemente hace nada y se va. Viola A4 — un error operativo (no hay markets configurados) no debería ser un exit 0 silencioso.

2. **Evidence guard** (`session.py:145-165`): si capture corrió pero produjo 0 eventos, la sesión entra en ERROR state con `EVIDENCE_COMPLETENESS` CRITICAL. Esto es correcto según A4.

El gap está en el CLI gate: retornar con éxito cuando `market_ids` está vacío es un falso positivo operativo.

### Comparación de políticas

| Política | Alineación con A4 | Alineación con REQ-PT-007 |
|---|---|---|
| **Wait** (bloquear hasta que haya markets) | ❌ Bloqueo silencioso — no hay señal de qué esperar | ❌ No hay timeout definido |
| **Finish successfully** (exit 0 sin datos) | ❌ Falso positivo — viola A4 | ❌ Oculta el problema |
| **Fail** (exit 1, error explícito) | ✅ Fail-fast explícito | ✅ Consistente con ERROR state |
| **Discover another market** | ❌ El discovery no es responsabilidad del session | ❌ Fuera de scope |
| **Pre-flight validation** (nuevo contrato) | ✅ Validación temprana antes de tocar la red | ✅ Extiende PRE_FLIGHT sin romper nada |

### Recomendación

**Fail explícito en PRE_FLIGHT.** Agregar un contrato operativo `ACTIVE_MARKETS_CONFIGURED` que valide que `get_active_market_ids()` retorna una lista no vacía **antes** de entrar a CAPTURING. Si falla, la sesión entra en ERROR con un mensaje claro: "No active markets configured. Set TRADY_AI_ACTIVE_MARKETS in .env."

Esto es consistente con:
- A4 (Fail-Fast): el error se detecta en el primer stage, no después de 60 segundos de capture vacío.
- REQ-PT-001: PRE_FLIGHT ya evalúa contratos antes de avanzar. Este sería un contrato más.
- `polymarket.py:390-391`: `EventCapture.start()` ya valida `market_ids` no vacío — el PRE_FLIGHT contract simplemente adelanta esa validación.

El CLI gate (`main.py:247-249`) también debería cambiarse de "mensaje + exit 0" a "error + exit 1", pero eso es code change. Para este análisis, el contrato operativo es suficiente como guía.

---

## Q6: Paper Trading Operator

### Repository Evidence

| Fuente | Evidencia |
|---|---|
| `RFC-005:401-424` | Hermes definido como integration layer: "reflection augmentation, operational summarization, proposal generation, anomaly interpretation. NOT: unrestricted execution, autonomous governance, architectural ownership." |
| `RFC-007 §Human Sovereignty` | "Human governance remains authoritative. Humans own capital allocation, production authorization, freeze approval, risk exposure." |
| `RFC-007 §Authority Hierarchy` | Governance > Deterministic Infrastructure > Reflection > Intelligence > External Platforms |
| `RFC-008` | Autonomous Coordination (Fase 8): bounded scheduling, coordination, sequencing. Aún no implementada. |
| `RFC-008 §Anti-Swarm` | "Agent swarms, recursive AI coordination, autonomous multi-agent governance" — explícitamente rechazados |
| `RFC-008 §Recursion Constraint` | "Recursive autonomy is prohibited. Agents spawning agents, autonomous orchestration trees, self-mutating execution graphs" — todo prohibido |
| `RFC-000 §Intelligence Containment` | "Intelligence systems must remain operationally sandboxed. Must never receive unrestricted signing, capital, deployment, infrastructure, or governance authority." |
| `Constitution §Values Hierarchy` | "1. Deterministic correctness > 7. Execution velocity" |
| `Roadmap §Core Principle` | "Stability before autonomy. Determinism before intelligence. Bounded execution before scale." |

### Análisis

**Operador recomendado para los primeros 30 días: Humano.**

Razón fundamental: el roadmap es explícito. Autonomous Coordination es **Fase 8**. Estamos en Fase 5. No hay bounded autonomy implementada. Poner a Hermes (o cualquier sistema) como operador de paper trading AHORA es adelantar 3 fases del roadmap. Viola el principio "Stability before autonomy."

**Sobre Hermes como Operational Operator vs Execution Decision Maker:**

La distinción es arquitectónicamente sólida y está alineada con los RFCs:

| Capa | Hermes hoy (RFC-005) | Hermes como Operator (Fase 8) |
|---|---|---|
| **Trading decisions** | ❌ Nunca — "intelligence assists operations, it does not own operations" | ❌ Nunca — la misma doctrina aplica |
| **Market discovery** | ❌ No en Fase 5 | ✅ Podría, si es bounded, observable, y atribuible (RFC-008) |
| **Rotate Condition IDs** | ❌ No en Fase 5 | ✅ Schedule approved workflows (RFC-008) |
| **Execute Paper Trading sessions** | ❌ No en Fase 5 | ✅ Coordinate bounded execution sequences (RFC-008) |
| **Capture evidence 24/7** | ❌ No en Fase 5 | ✅ Operational continuity automation (RFC-008) |
| **Produce operational summaries** | ✅ Ya lo hace — reflection augmentation, summarization | ✅ Mismo rol, expandido |

La arquitectura **permite** esta evolución, pero **no en Fase 5**. Los contratos operativos de RFC-008 (boundedness, observability, rollback, governance constraint) deben implementarse y verificarse antes.

**¿Mejora la eficiencia operativa sin violar boundaries?**
- Cuando esté implementado correctamente (Fase 8): SÍ. Hermes como scheduler bounded que ejecuta sesiones, rota markets, y produce summaries es exactamente el rol que RFC-008 define.
- AHORA: NO. Sería implementar autonomous coordination sin los contratos de boundedness que la hacen segura.

### Riesgos operativos

- **Adelantar autonomía**: si Hermes ejecuta sesiones sin bounded coordination contracts, cualquier error (market expirado, API down, WS disconnect) escala sin contención. Viola RFC-000 §Blast Radius Minimization.
- **Confusión de autoridad**: si Hermes rota markets Y propone parámetros, el límite entre "operational assistance" y "decision making" se vuelve borroso. Viola RFC-005 §Proposal-Only Doctrine.

### Recomendación

**Operador humano para los 30 días de Paper Trading.** Cada sesión se inicia manualmente con `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive`. Esto:

1. Respeta el roadmap (Fase 8 = Autonomous Coordination)
2. Preserva Human Sovereignty (RFC-007)
3. Genera evidencia operativa que Fase 8 usará para diseñar los bounded coordination contracts
4. Mantiene a Hermes en su rol actual: reflection augmentation, summarization, anomaly detection

La evolución de Hermes a Operational Operator debe diseñarse como SDD en Fase 8, respetando todos los contratos de RFC-008.

---

## Q7: Infrastructure Portability

### Repository Evidence

| Fuente | Evidencia |
|---|---|
| `RFC-000 §Infrastructure Isolation` | "Infrastructure systems must remain replaceable, bounded, auditable, operationally isolated, rollback-compatible. The architecture rejects infrastructure lock-in, hidden dependency ownership, opaque runtime coupling, irreversible operational mutation." |
| `Constitution B2 §Integration Hostility` | "Every integration introduces operational cost. The preferred integration is the one with fewer dependencies, smaller operational footprint, simpler rollback, explicit boundaries." |
| `Constitution §Forbidden Patterns 6.2` | "Framework-Driven Architecture prohibited. Tools, libraries, and frameworks must adapt to the project's boundaries. The project must not adapt to theirs." |
| `Roadmap §Fase 0` | "Platform-agnostic architecture, thin runtime doctrine" congelado desde Fase 0 |
| `RFC-001 §Platform Independence` | Core determinístico es platform-independent |
| `settings.py` | `pydantic-settings` con `.env` file — portabilidad inherente: un archivo de texto |
| `pyproject.toml`/`uv.lock` | Dependencias explícitas, version pinning, sin acoplamiento a infraestructura cloud |
| `polymarket.py` | Adaptador usa `httpx` y `websockets` — sin SDKs proprietary, sin cloud SDKs |
| `session.py` | PaperTradingSession usa `sqlite_utils` + imports directos de Python — sin message queues, sin orchestrators |

### Análisis

**La arquitectura actual YA garantiza portabilidad entre providers.** El diseño es inherentemente provider-agnostic por decisión arquitectónica desde Fase 0:

1. **Storage**: SQLite (archivo local). Cero dependencia de PostgreSQL, MySQL, DynamoDB, o cualquier managed database. El archivo `data/trady_ai.db` es portable con `scp` o `rsync`.

2. **Configuración**: `.env` file + `pydantic-settings`. Sin HashiCorp Vault, sin AWS Secrets Manager, sin Azure Key Vault. El archivo `.env` viaja con el repo.

3. **Runtime**: Python 3.12 + `uv`/`pip`. Sin Docker (aunque compatible), sin Kubernetes, sin serverless functions. Cualquier VPS con Python 3.12 corre el pipeline.

4. **Network**: `httpx` + `websockets` para Polymarket. Sin SDKs de cloud providers. La única dependencia externa es la API de Polymarket, que es un endpoint HTTP/WS público.

5. **Execution**: `click` CLI. Sin schedulers integrados (cron, systemd timers, Kubernetes CronJobs — todos compatibles, ninguno requerido).

**Migración entre infraestructuras:**

| Provider | ¿Funciona sin cambios? | Nota |
|---|---|---|
| **Local workstation** | ✅ Actual | WSL2 / Linux nativo |
| **Azure VPS** | ✅ | `apt install python3.12`, `git clone`, `uv sync`, listo |
| **Hostinger VPS** | ✅ | Ídem — Linux estándar |
| **Generic VPS (DO, Linode, Hetzner)** | ✅ | Cualquier Linux con Python 3.12 |
| **Future infrastructure** | ✅ | Mientras soporte Python 3.12 + filesystem |

El ÚNICO acoplamiento operativo actual es a Polymarket como plataforma de ejecución. Pero esto es intencional (Roadmap Fase 2) y el adapter pattern (`PolymarketAdapter`) ya abstrae la interfaz para que futuros adapters (Binance, XTB, IB) sigan el mismo contrato.

### Riesgos operativos

- **Estado no portable**: `data/trady_ai.db` y `paper_trading/` son state local. Migrar entre providers requiere copiar estos archivos. No hay mecanismo automático — y **no debería haberlo** en Fase 5 (eso es distributed systems, no implementado).
- **Secrets en `.env`**: `POLYMARKET_API_KEY`, `SECRET`, `PASSPHRASE` son texto plano. Para producción (Fase 6+) se necesitará secrets management. Pero para dry_run paper trading, las credenciales ni siquiera son necesarias (endpoints públicos).

### Recomendación

**No se requieren contratos operativos adicionales de portabilidad para Day 0.** La arquitectura ya garantiza portabilidad por diseño. Lo que SÍ debería congelarse:

1. **Runtime contract**: Python 3.12+, Linux, `uv` como package manager. Esto ya es implícito pero debería explicitarse.
2. **Data portability contract**: `data/` y `paper_trading/` son los únicos directorios con estado. Migrar entre providers = copiar esos directorios + `.env`.
3. **No cloud SDKs**: mantener la prohibición de SDKs de cloud providers en el código del pipeline. Ya se cumple, pero debería ser explícito.

---

## Operational Contracts to Freeze Before Day 0

Basado en el análisis de las 7 preguntas, estos son los contratos operativos mínimos que deberían congelarse:

### C1: Market Selection Contract
- **Source of Truth**: `TRADY_AI_ACTIVE_MARKETS` en `.env` como única fuente de market IDs.
- **Formato**: CSV de Polymarket Condition IDs (0x...).
- **Frecuencia de revisión**: semanal o bajo demanda del operador.
- **Evidencia**: cada sesión registra los `market_ids` usados en `SessionReport`.

### C2: Market Lifecycle Contract
- **Responsable**: Operador humano durante los 30 días.
- **Rotación**: documentada en commit message o session log cuando se modifica `ACTIVE_MARKETS`.
- **Detección de expiry**: PRE_FLIGHT debe validar que `ACTIVE_MARKETS` no está vacío (ver C4).

### C3: Domain Taxonomy Contract
- **Primer dominio**: `FOOTBALL-WINNER` — exclusivamente mercados "Winner (Full Time)" de fútbol en Polymarket.
- **Domain string**: case-sensitive, underscore-separated, validado en PRE_FLIGHT.
- **Expansión**: nuevas familias de mercado requieren nuevo domain string + 30 días de calibración independiente.

### C4: Pre-Flight Market Validation Contract
- **Validación**: `get_active_market_ids()` no vacío → condición para avanzar de PRE_FLIGHT a CAPTURING.
- **Fallback**: si está vacío, ERROR con mensaje explícito (no exit 0 silencioso).
- **Alineación**: extiende REQ-PT-001 sin modificar el state machine.

### C5: Operator Sovereignty Contract
- **Operador**: Humano para los 30 días iniciales.
- **Hermes**: rol limitado a reflection augmentation, summarization, anomaly detection (RFC-005).
- **Autonomous Coordination**: diferido a Fase 8, requiere implementación completa de RFC-008.
- **Sesiones**: iniciadas manualmente por el operador con `trady-ai paper-trade session`.

### C6: Infrastructure Portability Contract
- **Runtime**: Python 3.12+, Linux, `uv` package manager.
- **State**: `data/` + `paper_trading/` como únicos directorios con estado portable.
- **Prohibición**: SDKs de cloud providers en código del pipeline (ya se cumple).
- **Migración**: copiar repo + `.env` + `data/` + `paper_trading/` → funcional en cualquier provider.

### C7: Empty Market Policy Contract
- **Política**: Fail explícito (no wait, no success, no auto-discovery).
- **Detección**: PRE_FLIGHT, antes de cualquier llamada de red.
- **Severidad**: WARNING (no CRITICAL) — porque es una condición de configuración, no una violación de seguridad. El operador puede corregir `.env` y reintentar.

---

Estos 7 contratos congelan las decisiones operativas mínimas necesarias para arrancar los 30 días sin introducir complejidad innecesaria ni violar boundaries arquitectónicas existentes. Ninguno requiere cambios de código — son constraints operativos que guían al operador humano y documentan las decisiones explícitamente.
