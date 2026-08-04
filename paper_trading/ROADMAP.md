# 🧭 Paper Trading 30 Days — Navigation Roadmap

> **Source-of-truth references:**
> - Architecture Contract: `Papertrading review/PAPER-TRADING-ARCHITECTURE-CONTRACT.md`
> - Deployment Guide: `scripts/DEPLOYMENT.md`
> - Backlog: `BACKLOG.md`
>
> **Start date:** —  
> **Target duration:** 30 consecutive days  
> **Target sessions:** 2,880 (96/day × 30 days)

---

## Pre-Launch Checklist

## 🔒 Frozen VPS Specs (2026-07-21)

| Spec | Valor | Estado |
|------|-------|--------|
| **Proveedor** | AWS Lightsail | ✅ Congelado |
| **Nombre instancia** | `trady-paper-trading-v1` | ✅ Congelado |
| **Plan** | $7/mo — 1 GB RAM, 2 vCPUs, 40 GB SSD, 2 TB transfer | ✅ Congelado |
| **Región** | US East (N. Virginia) — `us-east-1` | ✅ Congelado |
| **OS** | Ubuntu 24.04 LTS | ✅ Congelado |
| **Static IP** | Incluido en el plan | ✅ |
| **SSH key** | Nueva (se genera al crear la instancia) | ⬜ Pendiente |
| **Cuenta AWS** | Nueva con $200 créditos | ⬜ Pendiente |

### 🪪 Cómo crear la cuenta AWS y obtener los $200 créditos

AWS cambió el Free Tier recientemente. El modelo actual:

**Lo que obtenés como cliente nuevo:**
- **$100** en créditos inmediatamente al crear la cuenta
- **Hasta $100 más** completando actividades en el dashboard "Explore AWS" (ej: lanzar una instancia EC2, crear un bucket S3)
- **Total: hasta $200** en créditos válidos por 12 meses
- **Lightsail 3 meses gratis**: oferta específica para instancias Lightsail nuevas

**Plan recomendado: PAID (no Free)**
- El **Free plan** limita acceso a un subset de servicios. No está claro si Lightsail entra en ese subset.
- El **Paid plan** da acceso completo a todos los servicios. Los $200 créditos aplican igual.
- No te van a cobrar la tarjeta a menos que los créditos se agoten.
- Podés monitorear el saldo desde el dashboard de Billing.

**Pasos:**
1. Ir a https://aws.amazon.com/free/
2. Click "Create a free account"
3. Elegir **Paid plan** (no Free plan)
4. Completar registro con email + tarjeta (débito/crédito, verificación de identidad)
5. Verificar email y número de teléfono
6. En el AWS Console Home, buscar el widget "Explore AWS" → filtrar por "Earn AWS credits" → completar actividades para ganar los $100 adicionales

**Costo estimado para nuestro caso:**
- Lightsail $7/mo × 1 mes = **$7** (30 días del experimento)
- Con $200 créditos = cubierto 28+ meses
- Si usáramos el Free plan en vez de Paid: gratis 6 meses, después la cuenta se cierra automáticamente (hay que upgradear antes)

---

### ✅ Code & Quality

- [x] SDD cycle complete (propose → spec → design → tasks → apply → verify → archive)
- [x] PR #7 merged to `main` (34 files, +3,496/−182)
- [x] 456/456 tests passing
- [x] 91% coverage
- [x] mypy strict: 0 errors
- [x] ruff: clean (23 warnings non-blocking, tracked as BL-025/BL-026)
- [x] Backlog reviewed — 0 items blocking deploy
- [x] `.gitignore` updated (`paper_trading/`, `skills/`)
- [x] Architecture Contract v1.0 frozen
- [x] `scripts/ensure_active_market.py` — standalone guard script ready
- [x] `.env.example` — template ready

---

## 🟢 Phase 1 — VPS Decision

> **Gate:** VPS provisioned, SSH access confirmed.

- [x] Choose VPS provider and plan → **AWS Lightsail $7/mo, us-east-1**
- [x] Name instance → **trady-paper-trading-v1**
- [x] Crear cuenta AWS (Paid plan + $200 créditos) — *2026-07-22*
- [x] Completar actividades "Explore AWS" para ganar $100 adicionales — *2026-07-22*
- [x] Crear instancia Lightsail: $7 plan, Ubuntu 24.04, us-east-1 — *2026-07-22*
- [x] Generar/descargar SSH key pair — *2026-07-22*
- [x] Configurar firewall: inbound SSH (22) only, IPv6 disabled — *2026-07-22*
- [x] Asignar static IP: `34.226.243.33` → `trady-paper-trading-v1-static-ip` — *2026-07-22*
- [x] Verify SSH access via `ssh trady-vps` alias from WSL2 — *2026-07-22*
- [x] Install base packages: `git` 2.43.0, `python3` 3.12.3, `uv` 0.11.31, `cron` active — *2026-07-22*

**✅ PHASE 1 COMPLETA — 2026-07-22**

**Provider comparison table:**

| Provider | Plan | Price/mo | vCPU | RAM | SSD | Transfer | Commit | Regions | ✅/❌ |
|----------|------|----------|------|-----|-----|----------|--------|---------|-------|
| **Hetzner** | CX22 (Regular) | **€3.99** (~$4.40) | 2 vCPU | 4 GB | 40 GB NVMe | 20 TB | Hourly | DE, FI, US (OR,VA), SG | 🏆 Recomendado |
| **Hetzner** | CX32 (Regular) | **€7.99** (~$8.80) | 4 vCPU | 8 GB | 80 GB NVMe | 20 TB | Hourly | DE, FI, US (OR,VA), SG | Overkill para esto |
| **Hetzner** | Cost-Opt (shared) | **~€2.49** (~$2.70) | 1 vCPU† | 2 GB | 20 GB NVMe | 20 TB | Hourly | DE, FI, US (OR,VA), SG | Mínimo, pero alcanza |
| **DigitalOcean** | Basic | **$6.00** | 1 vCPU | 1 GB | 25 GB SSD | 1 TB | Per-sec | NYC, SF, AMS, SGP, LON, FRA, TOR, BLR | Simple, dev-friendly |
| **AWS Lightsail** | $7 plan | **$7.00** | 2 vCPU‡ | 1 GB | 40 GB SSD | 2 TB | Monthly | Worldwide (multi-region) | 3 meses gratis nuevos |
| **AWS Lightsail** | $5 plan | **$5.00** | 2 vCPU‡ | 0.5 GB | 20 GB SSD | 1 TB | Monthly | Worldwide | RAM insuficiente (512MB) |
| **Hostinger** | KVM 1 | **$6.49** promo ⚠️ | 1 vCPU | 4 GB | 50 GB NVMe | 4 TB | 2 años | US, EU, Asia, SA | Renueva a $11.99/mo |
| **Azure** | B1s | **~$7-12** est. | 1 vCPU | 1 GB | ~30 GB | Pay/GB | Pay-as-you-go | Worldwide | Complejo; costos ocultos de egress |

> † Shared vCPU — variable performance. Suficiente para Python cron jobs.
> ‡ Burstable — ráfagas cortas, no sostenido. Nuestro workload es bursty (60s por sesión, 96 veces/día), así que calza bien.
> ⚠️ Hostinger renueva a $11.99/mo después del período promocional de 2 años. Para 30 días no es problema, pero infla el TCO real.

**Veredicto técnico:**
- **Mejor precio/performance**: Hetzner CX22 — €3.99/mo por 4 GB RAM + 2 vCPU + 40 GB NVMe. Es literalmente 4x más RAM que DigitalOcean o Lightsail por menos plata.
- **Mejor ecosistema**: AWS Lightsail — 3 meses gratis para cuentas nuevas, consola madura, más regiones para baja latencia.
- **Mejor simplicidad**: DigitalOcean — experiencia dev pulida, per-second billing, docs excelentes.
- **Evitar para este proyecto**: Azure B1s — pricing complejo, egress se cobra aparte, sobreingeniería para un cron job de Python.

---

## 🔒 Phase 2 — Day -1: FREEZE

> **Gate:** Dry-run session completes all 6 stages (PRE_FLIGHT → COMPLETE) without errors.

### 2.1 — Repository & Dependencies

- [ ] `git clone <repo-url> /opt/trady`
- [ ] `cp .env.example .env`
- [ ] `uv sync`
- [ ] Verify: `uv run trady-ai --help`

### 2.2 — Market Configuration (Approach A: Autonomous-first)

- [x] *Decision: Approach A* — leave `.env` with `TRADY_AI_ACTIVE_MARKETS=` empty, let the guard script auto-discover the first valid market on first run. *2026-07-22*
- [x] Review frozen eligibility rules in `scripts/ensure_active_market.py`:
  - [x] `_DOMAIN = "FOOTBALL-WINNER"`
  - [x] `_REQUIRED_TAGS = {"football", "winner"}`
  - [x] `_check_eligibility()` rules: `active=True`, `closed=False`, tags contain `football` AND `winner`
  - [x] Confirmed: guard handles empty `.env` (initial discovery branch, lines 293-303)
- [x] *Evidence: ARCHITECTURE-CONTRACT AD-4 — guard script applies frozen eligibility rules deterministically, no AI, no ranking*
- [x] **After first guard run:** verify `.env` shows a discovered market_id (proves autonomous discovery works) — *2026-07-22 ✅* discovered `0x8d53cf3ae...` (Atlético San Luis win on 2026-07-31, Liga MX)
- [x] Freeze date recorded: `2026-07-22`

### 2.5 — Dry-Run Session ✅

- [x] **Run dry-run session** — *2026-07-22 ✅* — exit 0, State: COMPLETE, 1 event capturado, bundle completo
- [x] **Verify bundle** — `paper_trading/dia-001/session_report-180334.json` + `manifest-180334.json` con SHA-256 checksums
- [x] **Verify all 6 stages** — PRE_FLIGHT → CAPTURING (60s) → EXECUTING → REFLECTING → VERIFYING → BUNDLING

**Bugs fixed during dry-run validation (P1):**
- session.py: `conditionId` → `token_id` translation for WS subscription (added `_resolve_token_ids()`)
- adapters/polymarket.py: `get_market_data()` URL `/market/` → `/markets/` (singular → plural)
- adapters/polymarket.py: WS subscribe format `type=subscribe/asset_ids` → `type=market/assets_ids`
- adapters/polymarket.py: WS message parser rewritten to handle Polymarket's book snapshot format (bids/asks/last_trade_price)
- BL-030 (registered): bundle path `paper_trading/paper_trading/dia-001/` shows doubled prefix (minor — paths in code, not blocker) — ver BACKLOG.md #BL-030

**✅ APPROACH A EXITOSO — 2026-07-22** Sistema autonomous-first funciona end-to-end.

**⚠️ DEVIATION FROM ARCHITECTURE-CONTRACT (documented):**
- Original: clob.polymarket.com/markets with tags `["football", "winner"]`
- Reality: API returns `tags=["All"]` (uninformative). Sports markets only via `polymarket.com/sports/{league}/games` (HTML) + `gamma-api/events?slug={slug}`
- New filter: question matches `^Will .+ win on YYYY-MM-DD?$`
- See: `scripts/ensure_active_market.py` docstring for full deviation notes
- Backlog candidate (do NOT create per "do not touch backlog" rule)

### 2.3 — Directory Structure

- [ ] `mkdir -p data/backups`
- [ ] `mkdir -p logs`
- [ ] `mkdir -p paper_trading`

### 2.4 — Guard Script Validation

- [ ] `python scripts/ensure_active_market.py` → exit 0
- [ ] Verify `.env` shows active markets after guard run

### 2.5 — Dry-Run Session

- [x] Run: `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive --duration 60` — *2026-07-22 ✅* exit 0, State: COMPLETE
- [x] Verify: PRE_FLIGHT stage completes
- [x] Verify: CAPTURING stage runs 60s
- [x] Verify: EXECUTING stage completes
- [x] Verify: REFLECTING stage completes
- [x] Verify: BUNDLING stage produces output in `paper_trading/dia-001/`
- [x] Verify: `session_report-180334.json` exists with valid content (1 event, 0 trades, all 6 stages)

### 2.6 — Crontab Installation

> **2026-07-22 review**: Deep analysis of the 4 clocks vs crontab timing found 2 bugs + 2 gaps in the original proposal. See `paper_trading/WS-CAPTURE-FIX-2026-07-22.md` §6 for the full analysis. Fixes applied:
> 1. **Lock file** (`flock -n`) — prevents concurrent sessions (original had no protection)
> 2. **Safe backup** (`sqlite3 .backup`) — replaces unsafe `cp` for WAL-mode SQLite
> 3. **Session timeout** (`timeout 300`) — kills hung sessions after 5 min

**Session cron (every 15 min, DISABLED until Day 0):**
```cron
# */15 * * * * cd /opt/trady && python scripts/ensure_active_market.py >> logs/paper-trading.log 2>&1 && flock -n /tmp/trady-session.lock timeout 300 .venv/bin/trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive --duration 60 >> logs/paper-trading.log 2>&1
```

**Backup cron (daily at 02:00 UTC, DISABLED until Day 0):**
```cron
# 0 2 * * * sqlite3 /opt/trady/data/trady_ai.db ".backup /opt/trady/data/backups/trady_ai-$(date +\%Y\%m\%d).db" && sha256sum /opt/trady/data/backups/trady_ai-$(date +\%Y\%m\%d).db > /opt/trady/data/backups/trady_ai-$(date +\%Y\%m\%d).sha256
```

- [x] Install crontab with both entries (commented out) — *2026-07-22 ✅*
- [x] Verify: `crontab -l` shows both entries (disabled) — *2026-07-22 ✅*
- [x] Verify `sqlite3` available on VPS: `which sqlite3` — *installed 3.45.1*
- [x] Test backup command manually: `sqlite3 data/trady_ai.db ".backup /tmp/test-backup.db"` — *1 event restored, SHA-256 verified*
- [x] Verify backup integrity: `sha256sum` PASS
- [x] **→ DISABLED — re-enable on Day 0 (Phase 3)**

---

### 2.7 — Research & Architecture (2026-07-22/23)

> **Gap filled:** Between Phase 2.6 (crontab) and Phase 3 (PRE-FLIGHT), the project underwent deep architectural research and an SDD cycle.

**Research documents produced (paper_trading/):**
- [x] `MARKOV-VS-REAL-DATA-REVIEW` — Markov model vs real Polymarket data (tick-size mismatch, NEUTRAL domination risk)
- [x] `TRADING-WINDOW-RESEARCH` — Polymarket trading continues during match (not stopped at kickoff)
- [x] `MARKOV-DOMAIN-ANALYSIS` — Football violates 4/6 Markov prerequisites; crypto 10,000x better for V1
- [x] `UNIVERSAL-MARKOV-ARCHITECTURE` — Engine is 90% domain-agnostic; boundary leaks at 3 points (persistence.py:21-23)
- [x] `MARKOV-STATE-SPACE-METHODOLOGY` — Cross-disciplinary scientific methodology for state-space construction
- [x] `CALIBRATION-FRAMEWORK` — Operationalizing the methodology as deterministic pipeline

**SDD Cycle: Calibration Framework — *2026-07-22 ✅***
- [x] Proposal → Specs (5 files, 19 reqs) → Design (218 lines) → Tasks (30 tasks)
- [x] Phase A: StateGenerator ABC, engine N×N domain-agnostic (500/500 tests, zero assertion changes)
- [x] Phase B: Evidence pipeline — AIC, BIC, Markov χ², CLI `calibrate review` + `calibrate adopt` (558 tests)
- [x] Verify Phase A + Phase B: PASS, 0 CRITICAL
- [x] Archive: delta specs merged into 5 main specs, local copy at `archive/calibration-framework/`

**Commit:** `e1912fd` — 59 files, +7457/-282 lines

### 2.8 — V1 Platform Decision (2026-07-28)

> **Research-driven decision:** `MARKOV-DOMAIN-ANALYSIS` recommends continuous markets (crypto/forex) for V1. Polymarket crypto markets are event-prediction (airdrops, IPOs), not continuous price trading. Evaluated platforms:

| Platform | Testnet | Geoblocked? | VPS | Result |
|----------|---------|------------|-----|--------|
| **Binance** | testnet.binance.vision | ❌ US + testnet WS 404 | Singapore | Descartado |
| **Bybit** | api-testnet.bybit.com | ❌ US only | **Singapore** | ✅ Funciona |

**Infrastructure decision:**
- [x] VPS `trady-binance` (Singapore, 52.220.172.112) — active
- [x] VPS `trady-vps` (Virginia, 34.226.243.33) — cancelled (geoblocked by Binance/Bybit)
- [x] SDD cycle: BybitAdapter (~300 LOC, tick-by-tick trade stream) — *2026-07-28 ✅*
- [x] Deploy BybitAdapter to Singapore VPS — *2026-07-28 ✅*
- [x] Dry-run session with Bybit testnet — *2026-07-28 ✅* 6 events in 15s, State: COMPLETE
- [x] Architecture Contract: v2.0 (multi-domain, multi-platform) — *2026-07-27 ✅*
- [x] Crontab installed on Singapore VPS (DISABLED) — *2026-07-28 ✅* — session every 15 min + daily backup at 02:00 UTC
- [x] Dry-run session with Bybit testnet — *2026-07-28 ✅* 6 events in 15s, State: COMPLETE

---

## 🟡 Phase 3 — Day 0: PRE-FLIGHT

> **Gate:** All 5 infrastructure checks pass. Crontab re-enabled for Day 1.

### 3.1 — Infrastructure Validation

- [x] Crontab active and correct (`crontab -l`) — *2026-07-28 ✅* DISABLED, entries correct
- [x] Manual session produces output in logs — *2026-07-28 ✅* 18 events, 0 trades, State COMPLETE, BTCUSDT+ETHUSDT
- [x] Manual backup: `sqlite3 data/trady_ai.db ".backup data/backups/test.db"` works — *2026-07-28 ✅* 126KB backup, sha256sum valid, 6 events confirmed
- [x] Bundle created: `ls paper_trading/dia-001/session_report.json` — *2026-07-28 ✅* dia-001 + dia-002 created (BL-030: double prefix cosmetic)
- [x] `trady-ai status` shows active markets with valid IDs — *2026-07-28 ✅* (note: status shows `active_markets` not `active_symbols`, but session confirmed BTCUSDT+ETHUSDT)

### 3.2 — Final Go/No-Go

- [x] All 5 checks passed — *2026-07-28 ✅*
- [x] `.env` config frozen — *2026-07-28 ✅*
- [x] Crontab **enabled** for automated execution — *2026-07-28 ✅* → **REDISABLED** 18:50 UTC (bug detected: session counter = day counter false positive)
- [x] Day 0 date recorded: `2026-07-28 18:23 UTC` — *2026-07-28 ✅*

### 3.3 — Incident: Session Counter False Positive (CRITICAL)

> **Detectado**: 2026-07-28 18:30-18:50 UTC | **Resuelto**: 2026-07-28 22:00 UTC
> **SDD Cycle**: `fix-calendar-day-counter` (commit `52d0c71`)
> **Informe**: `paper_trading/archive/bug-session-counter-2026-07-28/INCIDENT-REPORT.md`

- [x] Bug identified: `_compute_day()` = COUNT of reflection_reports = session counter, not calendar day — *2026-07-28 ✅*
- [x] Crontab disabled immediately — *2026-07-28 ✅*
- [x] Root cause analysis + contra-argumentación (Portable OS A1, A5, B1, B5) — *2026-07-28 ✅*
- [x] SDD cycle: fix-calendar-day-counter (proposal → specs → tasks → apply → verify → archive) — *2026-07-28 ✅*
- [x] VPS DB cleaned: reflection_reports, event_store, execution_log wiped — *2026-07-29 ✅*
- [x] Forensic archive saved locally — *2026-07-29 ✅*
- [x] Day 0 Restart: re-enable crontab with clean DB and fixed code — *2026-07-29 03:11 UTC ✅*

### 3.4 — Measurement Calibration SDD (ATR Foundation)

> **SDD Cycle**: `measurement-calibration` (commit `4cf223f`)
> **Discovery Phase**: 5 reports (Status → Architectural Review → Research → Discovery → Closure)
> **Veredicto verify**: FAIL (7 PARTIAL — coverage gaps, no defects)
> **Backlog**: BL-034 a BL-040

- [x] Discovery Phase: 4 investigaciones + 1 cierre — threshold = measurement instrument, no strategy parameter — *2026-07-29 ✅*
- [x] SDD cycle: proposal → specs (14 REQs, 5 domains) → design → tasks (20) → apply (13/13, 3 PRs) → verify (35/48) → archive — *2026-07-29 ✅*
- [x] Architecture Contract: §28 v2.0→v2.1, §29 D-003 (ATR-based threshold methodology) — *2026-07-29 ✅*
- [x] `ATRCalculator` + `MarketStateTracker` ATR integration (backward compat) — *2026-07-29 ✅*
- [x] Reflection snapshot pipeline: ExecutionResult → ReflectionEngine.persist_snapshot() → created_by column — *2026-07-29 ✅*
- [x] 712+ tests pass, mypy strict clean, ruff clean — *2026-07-29 ✅*
- [x] Pre-Day-0 calibration pilot: α y N determinados — *2026-08-04 ✅*
  - **α = 1.0** (4 sesiones: 0.5→27%, 1.0→36%🏆, 2.0→21%, 5.0→0%)
  - **N = 14** (7 sesiones: 10→biased, 14/15/20→35.7%🏆, 25-40→28%)
  - Informe: `archive/measurement-calibration/ATR-CALIBRATION-REPORT-2026-08-04.md`
- [x] Operador adopta α=1.0, N=14 via `calibrate adopt --confirm` — *2026-08-04 ✅* (adoption ID: 1, bundle: cal-004)
- [x] Activar ATR path frozen en `session.py` (α=1.0, N=14 fijos, sin env var) — *2026-08-04 ✅* (commit 79c8c58)
- [x] Limpiar DB para experimento confirmatorio — *2026-08-04 ✅*
- [x] Day 0 con ATR-based measurement instrument — *2026-08-04 16:19 UTC ✅* (α=1.0, N=14 frozen)
- [ ] Cerrar BL-034 a BL-040 (7 PARTIAL verify findings) ⬜

---

## 🔵 Phase 4 — Days 1-30: CONTINUOUS OPERATION

> **Gate:** 2,880 sessions with full audit trail. Review windows every ~7 days.

### 4.1 — Automated Execution (no human intervention)

- [ ] Crontab running — verify after first hour
- [ ] Check `logs/paper-trading.log` for first automated session
- [ ] Daily backup cron confirmed working (check `data/backups/` after 02:00 UTC)

### 4.2 — Review Window: Day 7

- [ ] Session count: `grep -c "SESSION_START" logs/paper-trading.log` → target ~672
- [ ] Errors: `grep ERROR logs/paper-trading.log`
- [ ] Rotations: `grep ROTATION logs/paper-trading.log`
- [ ] Contract violations: `grep CRITICAL logs/paper-trading.log`
- [ ] Disk usage: `df -h /opt/trady/data/`
- [ ] Backup integrity: `sha256sum -c data/backups/trady_ai-*.sha256`
- [ ] Notes / findings:

```
(record any observations here)
```

### 4.3 — Review Window: Day 14

- [ ] Session count: target ~1,344
- [ ] Errors: `grep ERROR logs/paper-trading.log`
- [ ] Rotations: `grep ROTATION logs/paper-trading.log`
- [ ] Contract violations: `grep CRITICAL logs/paper-trading.log`
- [ ] Disk usage: `df -h /opt/trady/data/`
- [ ] Notes / findings:

```
(record any observations here)
```

### 4.4 — Review Window: Day 21

- [ ] Session count: target ~2,016
- [ ] Errors: `grep ERROR logs/paper-trading.log`
- [ ] Rotations: `grep ROTATION logs/paper-trading.log`
- [ ] Contract violations: `grep CRITICAL logs/paper-trading.log`
- [ ] Disk usage: `df -h /opt/trady/data/`
- [ ] Notes / findings:

```
(record any observations here)
```

### 4.5 — Review Window: Day 28

- [ ] Session count: target ~2,688
- [ ] Errors: `grep ERROR logs/paper-trading.log`
- [ ] Rotations: `grep ROTATION logs/paper-trading.log`
- [ ] Contract violations: `grep CRITICAL logs/paper-trading.log`
- [ ] Disk usage: `df -h /opt/trady/data/`
- [ ] Notes / findings:

```
(record any observations here)
```

---

## 🟣 Phase 5 — Day 30: CALIBRATION GATE

> **Gate:** Reflection Engine evaluates 30 days of evidence. Operator decides next phase.

### 5.1 — Evidence Collection

- [ ] Session count final: `grep -c "SESSION_START" logs/paper-trading.log` → target 2,880
- [ ] All 30 `dia-NNN` directories present
- [ ] `calibration_report.json` produced by Reflection Engine
- [ ] Complete backup: `tar -czf paper-trading-archive-$(date +%Y%m%d).tar.gz paper_trading/ data/backups/`

### 5.2 — Calibration Decisions

- [ ] Review calibration report
- [ ] **Decision 1:** Is the pipeline stable enough for `execution_mode=live`?
  - [ ] Yes → proceed to governance review
  - [ ] No → continue dry-run or fix issues
- [ ] **Decision 2:** Do MarkovStrategy parameters need adjustment?
  - [ ] `warmup_ticks` current: 50
  - [ ] `threshold_pct` current: 0.001
- [ ] **Decision 3:** Expand to more domains?
  - [ ] Stay with FOOTBALL-WINNER only
  - [ ] Add domain(s): `________`
- [ ] **Decision 4:** Proceed to Phase 6 (multi-domain portfolio, Hermes integration)?
  - [ ] Yes — start Phase 6 SDD cycle
  - [ ] No — continue Paper Trading or pause

### 5.3 — Archive

- [ ] `paper_trading/` directory archived and preserved
- [ ] DB backups archived
- [ ] Logs archived
- [ ] Post-experiment retrospective documented
- [ ] New backlog items recorded (bugs, findings, improvements)

---

## 📋 Backlog — Open Items (Non-Blocking)

| ID | Priority | Description | Deferred Until |
|----|----------|-------------|----------------|
| BL-018 | baja | `_last_state` not persisted in snapshots | Schema evolution |
| BL-020 | baja | `dry_run_enforced` doc discrepancy | No operational impact |
| BL-021 | baja | `_compute_day()` uses COUNT(*) | Cosmetic |
| BL-022 | baja | Bundler ignores `day` param | Cosmetic |
| BL-023 | media | `get_events()` limit 2000, no pagination | Post-experiment |
| BL-024 | media | `last_processed_seq` proxy via `tick_number` | Phase 6+ schema |
| BL-025 | baja | MockCapture naming convention (ruff N806) | Lint cleanup |
| BL-026 | baja | Import hygiene (ruff I001/F401/F841) | Lint cleanup |

---

## 🚨 Alert Signals — What to Watch During Operation

| Signal | Command | Meaning |
|--------|---------|---------|
| `CRITICAL` in logs | `grep CRITICAL logs/paper-trading.log` | TEMPORAL_INTEGRITY violation — **stop and investigate** |
| `ERROR` recurring | `grep ERROR logs/paper-trading.log` | Capture/execute/reflect failure — investigate |
| Frequent `ROTATION` | `grep ROTATION logs/paper-trading.log` | Condition IDs expiring fast — add more |
| <90 sessions/day | `grep -c SESSION_START` | Cron failure or guard blocking — investigate |
| Disk >80% | `df -h /opt/trady/data/` | Backups accumulating — rotate old ones |

---

## 🔄 Rollback Procedure

If Paper Trading v2 must be reverted:

```bash
# 1. Disable crontab
crontab -e  # comment out both entries

# 2. Revert to Fase 5 archive
git checkout <fase-5-tag> -- src/trady_ai/paper_trading/

# 3. Remove guard script
rm scripts/ensure_active_market.py

# 4. Verify
trady-ai status
```
