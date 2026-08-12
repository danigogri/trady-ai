# AGENTS.md — Trady.AI

> Guía de orientación para agentes de IA. No reemplaza la documentación — es un mapa para llegar rápido.

## 1. Qué es Trady.AI

Infraestructura financiera **deterministic-first** para ejecutar, analizar y mejorar decisiones de trading multi-plataforma. NO es un trader autónomo con IA — la inteligencia asiste, las capas deterministas ejecutan.

**Filosofía**: determinismo > evidencia > límites > simplicidad.

## 2. Estado actual (2026-08-12)

| Dato | Valor |
|------|-------|
| Fase activa | **Paper Trading V1 — experimento de 30 días** |
| Día calendario | **Day 16** (DAY_ZERO = 2026-07-28) |
| Estado | 🟢 **Corriendo** en VPS Singapur |
| Dominio | BYBIT-SPOT (BTCUSDT + ETHUSDT, Bybit testnet) |
| Threshold | ATR α=1.0, N=14 (calibrado y frozen) |
| Sesiones | ~834 totales, 96/día |
| Eventos | ~1,847 acumulados (post-fix) |
| Trades | 0 (Markov en fase de acumulación) |
| Último fix | BL-023: `get_events()` sin límite + strategy restore + seq tracking |
| Crontab | ✅ ENABLED (`*/15` sesiones + `0 2` backup) |
| VPS | AWS Lightsail, Singapur, 52.220.172.112, `/opt/trady/` |

**Próximo hito**: Review window Day 21, luego Day 30 (fin del experimento → calibración final).

## 3. Paths críticos

| Path | Qué es |
|------|--------|
| `paper_trading/ROADMAP.md` | **Roadmap operacional** — checkboxes de progreso, LA fuente de verdad del experimento |
| `TRADY-AI-SOURCE-OF-TRUTH-001.md` | Identidad + filosofía del proyecto |
| `TRADY-AI-MASTER-ROADMAP-001,md` | Master roadmap (⚠️ el archivo tiene coma en el nombre) |
| `Papertrading review/PAPER-TRADING-ARCHITECTURE-CONTRACT.md` | Contrato arquitectónico frozen (v2.1) — 4 clocks, decisiones |
| `PORTABLE OS/` | Gobernanza: Constitución, Operations Manual, Git Workflux, SDD Governance, Backlog Protocol |
| `BACKLOG.md` | BL abiertos/cerrados |
| `RFC-000` … `RFC-009` | Arquitectura por capa (seguridad, core, estrategia, reflexión, IA, multi-dominio, gobernanza…) |
| `archive/` | Historial SDD (6 changes: calibration-framework, guard-script, binance, bybit, fix-calendar-day-counter, measurement-calibration) |
| `openspec/specs/` | Specs fuente de verdad |
| `src/trady_ai/` | Código fuente |
| `scripts/` | `ensure_active_market.py` (guard script) + `DEPLOYMENT.md` |

## 4. Cómo orientarse (según la tarea)

- **¿Dónde estamos?** → `paper_trading/ROADMAP.md`
- **¿Qué es esto / filosofía?** → `TRADY-AI-SOURCE-OF-TRUTH-001.md`
- **¿Reglas de gobernanza?** → `PORTABLE OS/` (empieza por la Constitución)
- **¿Bugs pendientes?** → `BACKLOG.md` (filtrar "abierto")
- **¿Historial de un cambio?** → `archive/<change>/`
- **¿Arquitectura del experimento?** → `Papertrading review/PAPER-TRADING-ARCHITECTURE-CONTRACT.md`

## 5. Convenciones

- **Commit**: convencional (`feat:`/`fix:`/`docs:`/`deuda:`/`spec:`). Sin Co-Authored-By, sin emojis.
- **SDD**: proposal → spec → design → tasks → apply → verify → archive. Solo para cambios sustanciales; fixes quirúrgicos van directo.
- **Portable OS**: 4 clocks (Discovery/Evidence/Decision/Reflection), determinismo obligatorio, freeze discipline.
- **Idioma**: el usuario habla español rioplatense (voseo). Artifacts técnicos en inglés por defecto.
- **Paths**: SIEMPRE Linux (`/home/danyg/projects/Trady.AI`). El viejo path `/mnt/d/dev/...` está muerto.
- **Engram**: project `trady-ai`. Usar `mem_context()` + `mem_search()` para recuperar historia.

## 6. Lo que NO hacer

- ❌ NO ejecutar `execution_mode=live` — el experimento es dry-run.
- ❌ NO cambiar α=1.0 / N=14 sin gobernanza explícita (están frozen y calibrados).
- ❌ NO reiniciar SDD phases archivadas.
- ❌ NO tocar backlog items sin autorización explícita (registrar sí, trabajar no).
- ❌ NO usar el path Windows viejo.
- ❌ NO commits directos a main local — usar branches (ver `PORTABLE OS/GIT-WORKFLUX.md`).

## 7. Primeras acciones recomendadas (nuevo chat)

1. `mem_context()` — recuperar contexto reciente de Engram.
2. `mem_current_project()` — confirmar proyecto `trady-ai`.
3. Leer `paper_trading/ROADMAP.md` — estado actual del experimento.
4. Si hay que tocar código: leer la sección correspondiente de `PORTABLE OS/` y el RFC relevante.
