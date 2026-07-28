# Paper Trading Continuous Operation — Operational Architecture

Premisa aceptada: Market discovery determinístico, sin Hermes en critical path, sin governance nuevo. El challenge ahora es uptime continuo durante ~30 días.

## 1. Executive Summary

La operación continua es viable sin nueva arquitectura. El pipeline ya soporta ejecución unattended vía --non-interactive. El state machine ya es idempotente vía _reconstruct_stages(). La evidencia ya se persiste vía EvidenceBundler. Lo que falta no es un coordinator ni governance nuevo — es un scheduler del sistema operativo (cron/systemd timer) y un contrato operativo sobre cuándo y cómo interviene el humano.

El modelo es: el scheduler dispara sesiones. El pipeline corre solo. El humano revisa evidencia cada pocos días.

Estado: READY TO FREEZE

## 2. Architectural Compatibility Assessment

### 2.1 Lo que YA soporta unattended execution

| Mecanismo | Ubicación | Evidencia |
| --- | --- | --- |
| --non-interactive | session.py:296-301 | Timed capture de 60s en vez de esperar Ctrl+C |
| _reconstruct_stages() | session.py:329-363 | Si una etapa ya se completó hoy, se skippea. Re-ejecución segura. |
| SessionReport + contracts.json | bundler.py:45-93 | Evidencia persistida por sesión con SHA-256 |
| frozen=True en Settings | settings.py:70 | Inmutable post-construcción — no hay riesgo de mutación en runtime |
| dry_run_enforced | contracts.py:30-49 | CRITICAL si execution_mode != dry_run |

### 2.2 Constraints que todo diseño debe respetar

| Constraint | Fuente | Implicación |
| --- | --- | --- |
| "hidden services, invisible background processes, uncontrolled daemons" — rechazados | RFC-000 §Runtime Hardening | El scheduler DEBE ser explícito y observable (cron loguea, systemd journal registra) |
| "schedule approved workflows, coordinate bounded execution sequences" | RFC-008 §Primary Responsibilities | Fase 8 — esto es LO QUE QUEREMOS, pero no está implementado. Usar scheduler del OS es el equivalente mínimo sin violar el roadmap. |
| "Limited autonomy may exist only inside explicitly approved boundaries" | RFC-007 §Bounded Autonomy | El scheduler del OS es el "approved boundary". Lo que ejecuta (el pipeline) es determinístico. |
| Settings es singleton inmutable | settings.py:74-82 | Cambiar markets requiere nuevo proceso Python. El scheduler naturalmente crea un proceso nuevo por ejecución — esto NO es un problema, es una feature. |

### 2.3 ¿Hay conflicto con RFC-008 (Autonomous Coordination)?

NO. Porque:

- RFC-008 gobierna sistemas de coordinación autónoma DENTRO de Trady AI (Fase 8).
- Lo que proponemos es un scheduler EXTERNO (cron/systemd) que invoca el CLI.
- El scheduler no es parte de Trady AI — es infraestructura del sistema operativo.
- El pipeline sigue siendo 100% determinístico. El scheduler solo decide CUÁNDO ejecutarlo.

Esto es análogo a como cron ejecuta backups, systemd ejecuta servicios, o GitHub Actions ejecuta CI. El scheduler es infrastructure, no architecture.

Estado: READY TO FREEZE

## 3. Continuous Operation Architecture

### 3.1 Modelo operativo: Scheduler-Driven Deterministic Cycles

```text
┌─────────────────────────────────────────────────────────┐
│                  SCHEDULER (cron / systemd)              │
│                                                         │
│  Cada N horas:                                          │
│  trady-ai paper-trade session                           │
│    --domain FOOTBALL-WINNER                              │
│    --non-interactive                                     │
│                                                         │
│  Output:                                                │
│  → paper_trading/dia-NNN/session_report.json             │
│  → paper_trading/dia-NNN/contracts.json                  │
│  → paper_trading/dia-NNN/manifest.json                   │
│  → data/trady_ai.db (event_store + trades + reflection)  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              HUMANO (cada 2-7 días)                      │
│                                                         │
│  1. Revisa bundles en paper_trading/dia-NNN/             │
│  2. Ejecuta discover_markets.py si hay markets expirados │
│  3. Actualiza TRADY_AI_ACTIVE_MARKETS en .env            │
│  4. Reinicia scheduler si cambió .env                    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 ¿Por qué esto funciona?

| Propiedad | Mecanismo |
| --- | --- |
| Idempotencia | _reconstruct_stages() — si ya hubo sesión hoy, PRE_FLIGHT detecta TEMPORAL_INTEGRITY violation o reconstruction skippea etapas |
| Aislamiento de fallos | Cada ejecución es un proceso Python nuevo. Si una sesión falla (WS disconnect, API down), la siguiente ejecución arranca fresca. |
| Determinismo | Mismo .env + mismo market_ids + misma DB → mismo comportamiento. El scheduler no afecta el pipeline. |
| Observabilidad | Cada sesión deja session_report.json + contracts.json. El scheduler loguea stdout/stderr. structlog escribe a stderr. |
| Sin estado compartido | No hay coordinator process que mantenga estado entre ciclos. El estado está en data/trady_ai.db y paper_trading/. |

### 3.3 ¿Qué pasa si falla una sesión?

Escenario: WS de Polymarket caído a las 3 AM

1. Scheduler ejecuta session --non-interactive
2. CAPTURING → WS connect fails → Exception
3. session.py captura: "capture_stage_failed" → ERROR state
4. SessionReport se retorna con ERROR
5. BUNDLING aún se ejecuta → evidencia se persiste
6. Exit code != 0 (SystemExit(1) en main.py:278)
7. Scheduler registra el failure
8. Próxima ejecución (N horas después): intenta de nuevo
9. Si WS ya está up → CAPTURING exitoso → session continúa normalmente

El evidence bundle con ERROR state le dice al operador exactamente qué pasó y cuándo.

Estado: READY TO FREEZE

## 4. Operational Evidence Architecture

### 4.1 Lo que YA se persiste (extender, no reinventar)

| Artifact | Contenido |
| --- | --- |
| session_report.json | day, domain, event_count, trade_count, reflection_report_id, calibration_state, stage_timestamps |
| contracts.json | Lista de ContractViolation con severity, detail, timestamp |
| manifest.json | SHA-256 de artifacts |
| reflection_reports (DB) | Outcome summary, signal quality, drift alerts, proposals |
| event_store (DB) | Cada tick capturado con market_id, price, volume, timestamp |
| trades (DB) | Cada trade ejecutado con signal_id, action, price, size |
| structlog output (stderr) | Logs estructurados de cada stage |

### 4.2 Lo que FALTA para revisión post-hoc del operador

El operador necesita responder, después de 3 días sin mirar:

"¿Qué pasó en cada ciclo? ¿Qué markets se usaron? ¿Hubo fallos?"

El SessionReport actual no incluye los market_ids usados. El campo domain dice FOOTBALL-WINNER pero no qué Condition IDs específicos se capturaron.

Gap: SessionReport no registra market_ids.

Solución: Extender SessionReport con un campo market_ids: list[str]. Ya se pasan a run_session() — solo falta persistirlos en el report. Esto es un cambio mínimo (1 campo en un dataclass).

```python
# models.py — agregar:
market_ids: list[str] = field(default_factory=list)

# session.py — en run_session():
report = SessionReport(
    day=day,
    domain=domain,
    market_ids=market_ids,  # ← nuevo
    event_count=0,
    trade_count=0,
    reflection_report_id=None,
)
```

Con este campo, session_report.json contiene todo lo que el operador necesita para auditar un ciclo sin estar presente.

### 4.3 ¿Se necesita un "ciclo de reporte" separado?

NO. La evidencia YA se genera después de cada sesión vía EvidenceBundler.bundle() en el stage BUNDLING. El scheduler naturalmente ejecuta el ciclo completo → el bundle se crea automáticamente. Cero mecanismos nuevos.

Estado: READY TO FREEZE (el gap del campo market_ids en SessionReport es BACKLOG, no bloquea)

## 5. Modularity Assessment: Coordinator vs Independent Scripts

### 5.1 Alternative A: Independent scripts + external scheduler

```text
cron/systemd
    ├── trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive
    │   (ejecuta el ciclo completo: PRE_FLIGHT → CAPTURING → ... → BUNDLING)
    │
    └── (nada más — el pipeline hace todo)
```

Ventajas:

- ✅ Cero código nuevo de coordinación — el pipeline YA es el coordinator de su propio ciclo
- ✅ Failure isolation total: cada ejecución es un proceso nuevo
- ✅ Sin estado en memoria: todo en DB + filesystem
- ✅ El scheduler del OS es reemplazable (cron → systemd timer → lo que sea)
- ✅ Testeable: trady-ai paper-trade session --non-interactive ya se puede probar manualmente
- ✅ Blast-radius mínimo: un crash afecta solo esa ejecución

Desventajas:

- ❌ Sin lógica de "si falló 3 veces seguidas, notificar al operador" — requiere tooling externo
- ❌ Sin rotación automática de markets — requiere intervención humana periódica

### 5.2 Alternative B: Centralized coordinator (Python daemon)

```text
paper_trading_coordinator.py (proceso long-running)
    ├── loop:
    │   ├── discover_markets()
    │   ├── evaluate_candidates()
    │   ├── update_config()
    │   ├── run_session()
    │   ├── generate_report()
    │   └── sleep(N hours)
```

Ventajas:

- ✅ Lógica de retry y notificación integrada
- ✅ Podría rotar markets automáticamente

Desventajas:

- ❌ Proceso long-running = single point of failure. Si crashea, todo se detiene hasta que el operador lo note.
- ❌ Si se cuelga en un WS disconnect loop, bloquea ciclos futuros.
- ❌ Estado en memoria entre ciclos — riesgo de corrupción silenciosa.
- ❌ Viola RFC-000 §Runtime Hardening: "uncontrolled daemons" son rechazados. Un daemon hecho en casa sin supervision es exactamente eso.
- ❌ Viola Constitution A5 (Simplicity): 200 líneas de coordinator vs 1 línea de cron.
- ❌ Viola Constitution B2 (Integration Hostility): introduce un nuevo componente con su propio lifecycle, superficie de fallo, y burden de mantenimiento.
- ❌ Viola RFC-008: es un coordinator autónomo implementado en Fase 5 cuando RFC-008 es Fase 8. Aunque no use AI, sigue siendo autonomous coordination no aprobada.

### 5.3 Veredicto

Alternative A gana por margen amplio. El pipeline YA es un coordinator determinístico de su propio ciclo (PRE_FLIGHT → BUNDLING). Agregar OTRO coordinator arriba es redundante y arquitectónicamente regresivo.

La pregunta "¿scripts independientes o coordinator centralizado?" tiene una tercera respuesta que es superior a ambas: ninguno de los dos. No necesitamos ni scripts independientes ni un coordinator. Necesitamos que el scheduler del OS invoque el pipeline existente. El pipeline ya coordina sus propias etapas.

NO:  scripts independientes coordinados externamente
NO:  coordinator centralizado
SÍ:  pipeline existente + scheduler del OS

Estado: READY TO FREEZE

## 6. Scheduling Alternatives

| Estrategia | Simplicidad | Observabilidad | Portabilidad | Determinismo |
| --- | --- | --- | --- | --- |
| cron | ✅ Máxima: 1 línea en crontab | ✅ Logs vía syslog/MTA | ✅ Universal en Linux | ✅ Dispara en tiempos fijos |
| systemd timer | ⚠️ Media: 2 archivos (.service + .timer) | ✅ Journal integrado | ✅ Linux con systemd | ✅ Dispara en tiempos fijos |
| Windows Task Scheduler | ⚠️ GUI-based, menos scriptable | ✅ Event log | ❌ Solo Windows | ✅ Dispara en tiempos fijos |
| Python daemon | ❌ Máxima complejidad | ❌ Hay que buildearla | ✅ Portable | ⚠️ Depende del código |
| Docker restart policy | ⚠️ Requiere Docker | ⚠️ docker logs | ⚠️ Docker dependency | ❌ Restart no es schedule |
| VPS daemon | ❌ Misma crítica que Python daemon | ❌ Ídem | ✅ | ❌ Ídem |

¿Cuál es el más alineado con los RFCs?

cron. Razones:

1. Simplicidad (A5): 1 línea. 0 */6 * * * cd /path && .venv/bin/python -m trady_ai paper-trade session --domain FOOTBALL-WINNER --non-interactive
2. Observabilidad (RFC-000): cron loguea cada ejecución. stdout/stderr va al MTA o a un archivo. structlog del pipeline agrega structured logging.
3. Portabilidad (RFC-000 §Infrastructure Isolation): cron existe en TODO Linux, BSD, y macOS. No es un vendor lock-in — es POSIX.
4. Determinismo (A1): cron dispara en tiempos fijos. El comportamiento del pipeline no depende de cron — solo el timing.
5. Rollback (RFC-000): crontab -e, comentar la línea, listo. Instantáneo.
6. No es un "daemon" (RFC-000 §Runtime Hardening): cron es un servicio del sistema operativo, no un daemon custom. Es explícito, documentado, y universal.

systemd timer es una alternativa válida si el entorno es Linux con systemd (más granularidad, mejor integración con journal). La decisión cron vs systemd timer es operativa, no arquitectónica. Ambos son aceptables.

Estado: READY TO FREEZE (cron como default, systemd timer como alternativa)

## 7. Local vs VPS Continuous Execution

| Factor | Local (WSL2/workstation) | VPS |
| --- | --- | --- |
| Uptime | ❌ La workstation se apaga, suspende, o reinicia | ✅ 99.9%+ uptime |
| Network | ⚠️ Depende de WiFi/VPN doméstica | ✅ Datacenter-grade |
| Costo | ✅ $0 adicional | ⚠️ ~$5-20/mes |
| Observabilidad | ✅ Acceso directo | ✅ SSH + logs |
| Portabilidad | ✅ Mismo código | ✅ Mismo código |
| 30 días continuos | ❌ Imposible sin mantener la workstation 24/7 | ✅ Diseñado para esto |

Veredicto

VPS es necesario para 30 días continuos. Una workstation local no puede garantizar uptime 24/7 por 30 días. Suspensión, reinicios por updates, cortes de luz — todo rompe la continuidad.

La arquitectura ya es portable (ver Q7 del review anterior). Migrar a un VPS es:

```bash
git clone <repo>
cp .env .  # con secrets y ACTIVE_MARKETS
uv sync
crontab -e  # agregar la línea de cron
```

El runtime contract es: Python 3.12 + Linux + uv. Cualquier VPS de $5-10/mes (Hetzner, DigitalOcean, Linode, Hostinger, Azure) lo cumple.

Estado: READY TO FREEZE

## 8. Operational Risks

### 8.1 Riesgos de ejecución unattended

| Riesgo | Probabilidad | Impacto | Mitigación |
| --- | --- | --- | --- |
| WS disconnect loop | Alta (APIs externas fallan) | Medio — sesión entra en ERROR, se reintenta en el próximo ciclo | _reconstruct_stages() + exit code != 0 notifica al scheduler. El operador revisa en la próxima ventana. |
| Polymarket API rate limit | Media | Bajo — la sesión falla, la siguiente reintenta | El pipeline no hace retry agresivo. Una sesión fallida no bloquea la siguiente. |
| DB corruption | Baja (SQLite es robusto) | Alto — pérdida de datos | Backup diario de data/trady_ai.db (1 línea en cron). SQLite es un archivo → cp data/trady_ai.db data/backups/trady_ai-$(date +%Y%m%d).db |
| Disco lleno | Baja (event_store crece lento) | Alto — sesiones no pueden escribir | Monitoreo de disco (92% → alerta). event_store crece ~100-1000 filas por sesión de 60s → insignificante en 30 días. |
| Market expirado → 0 eventos → ERROR | Media (fútbol: markets duran días) | Bajo — sesión falla explícitamente, operador lo ve en el próximo review | El operador rota markets en su ventana de revisión (cada 2-7 días) |
| Deriva de configuración | Baja (Settings es frozen) | Medio — si .env se modifica mal, sesiones fallan | .env en git. Cambios via commit. |
| Proceso zombi | Muy baja (cron maneja procesos hijo) | Bajo | cron tiene timeout implícito. El pipeline siempre termina (COMPLETE o ERROR). |

### 8.2 Riesgos que NO aplican

- ❌ Real funds: DRY_RUN_ENFORCED en PRE_FLIGHT lo bloquea.
- ❌ AI hallucination: Hermes no está en el critical path.
- ❌ Governance bypass: No hay governance nuevo. El pipeline no decide qué tradear — ejecuta lo configurado.
- ❌ Silent data loss: Fail-fast en cada stage. Si algo falla, queda registrado.

Estado: READY TO FREEZE (los riesgos son conocidos y mitigables sin nueva arquitectura)

## 9. Final Recommendation

Minimum Viable Continuous Operation Architecture

```text
┌──────────────────────────────────────────────────────────┐
│                    VPS (Linux, Python 3.12)               │
│                                                          │
│  crontab:                                                │
│  0 */6 * * * cd /opt/trady.ai && \                       │
│    .venv/bin/trady-ai paper-trade session \              │
│    --domain FOOTBALL-WINNER --non-interactive \           │
│    >> logs/paper-trading.log 2>&1                        │
│                                                          │
│  0 2 * * * cp data/trady_ai.db \                         │
│    data/backups/trady_ai-$(date +\%Y\%m\%d).db           │
│                                                          │
│  Evidencia generada automáticamente:                     │
│  paper_trading/dia-NNN/session_report.json                │
│  paper_trading/dia-NNN/contracts.json                     │
│  paper_trading/dia-NNN/manifest.json                      │
│  logs/paper-trading.log (structured logging)              │
│  data/backups/trady_ai-YYYYMMDD.db                        │
└──────────────────────────────────────────────────────────┘
                            │
                            │  (cada 2-7 días)
                            ▼
┌──────────────────────────────────────────────────────────┐
│                    OPERADOR HUMANO                        │
│                                                          │
│  1. ssh al VPS                                           │
│  2. Revisa últimos bundles:                              │
│     ls paper_trading/dia-NNN/                             │
│  3. Revisa log:                                          │
│     tail -100 logs/paper-trading.log                      │
│  4. Si hay markets expirados:                            │
│     python scripts/discover_markets.py --domain FOOTBALL  │
│     → actualiza .env                                     │
│     → git commit -m "ops: rotate football markets"       │
│  5. Si todo OK → nada más. El scheduler sigue solo.      │
└──────────────────────────────────────────────────────────┘
```

Componentes

| Componente | Tipo | ¿Nuevo? |
| --- | --- | --- |
| cron (scheduler) | Infraestructura del OS | No — existe en todo Linux |
| trady-ai paper-trade session --non-interactive | Pipeline existente | No — ya implementado |
| scripts/discover_markets.py | Tooling determinístico | Sí — script de ~50 líneas |
| logs/paper-trading.log | Observabilidad | No — structlog ya escribe a stderr |
| data/backups/ | Backup | Sí — 1 línea en cron |
| SessionReport.market_ids | Campo nuevo en dataclass | Sí — BACKLOG |

Lo que NO se construye

- ❌ Coordinator daemon
- ❌ "Operational Governance Layer"
- ❌ Hermes en market discovery
- ❌ Rotación automática de markets
- ❌ Sistema de notificaciones
- ❌ Dashboard de monitoreo
- ❌ Nuevos contratos operativos

### Contratos operativos finales (3, consolidados)

#### OC-1: Execution Rhythm

- Scheduler: cron cada 6 horas (0 */6 * * *)
- Comando: trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive
- Idempotencia: garantizada por _reconstruct_stages() — múltiples ejecuciones el mismo día son seguras
- Frecuencia: 4 sesiones/día × 30 días = 120 puntos de datos para calibración

#### OC-2: Operator Review Window

- Frecuencia: cada 2-7 días
- Responsabilidades: revisar bundles, rotar markets expirados, verificar backups
- Market rotation: manual, asistida por discover_markets.py
- Evidencia: session_report.json contiene market_ids usados (BACKLOG para el campo)

#### OC-3: Failure Recovery

- Fail-fast: cada sesión fallida genera session_report.json con ERROR state
- Retry: automático en la próxima ejecución del scheduler
- Escalación: el operador detecta failures en su ventana de revisión
- Backup: diario de data/trady_ai.db

### Final Verdict

| Decisión | Estado |
| --- | --- |
| Continuous operation es viable con arquitectura actual | ✅ READY TO FREEZE |
| Scheduler: cron (o systemd timer) | ✅ READY TO FREEZE |
| VPS requerido para 30 días de uptime | ✅ READY TO FREEZE |
| Sin coordinator daemon — el pipeline YA coordina sus etapas | ✅ READY TO FREEZE |
| Sin Hermes en critical path | ✅ READY TO FREEZE (decisión previa) |
| Sin governance nuevo | ✅ READY TO FREEZE |
| Campo market_ids en SessionReport | 🔲 BACKLOG |
| Script discover_markets.py | 🔲 BACKLOG |
| Backup diario de DB | 🔲 BACKLOG |
| Market rotation automática | ❌ RECHAZADO — Fase 8 |

La operación continua de 30 días requiere 3 cosas que no existen hoy: un VPS, una línea de cron, y un script de discovery. Nada más. El resto ya está construido.