# Paper Trading — VPS Deployment Guide

## Overview

The Paper Trading 30-day experiment runs continuously on a **Linux VPS**,
scheduled via **cron** at **15-minute intervals**. The deployment model follows
the Architecture Contract (OC-1, AD-7, AD-10):

- No long-running daemon (each invocation is a fresh Python process)
- No orchestration framework (cron is the scheduler)
- No cloud SDKs (SQLite + Python stdlib + cron)

---

## 1. VPS Requirements

| Requirement | Specification |
|---|---|
| **OS** | Linux (any distribution with cron) |
| **Python** | 3.12+ |
| **Package manager** | `uv` (preferred) or `pip` |
| **Disk** | SSD recommended. DB + backups: ~500 MB for 30 days |
| **RAM** | 512 MB minimum |
| **Runtime** | 24/7 for 30 consecutive days |

---

## 2. Initial Setup

```bash
# Clone repository
git clone <repo-url> /opt/trady
cd /opt/trady

# Create environment file from template
cp .env.example .env

# ⚠️ EDIT .env — REQUIRED before first run:
#   Set TRADY_AI_ACTIVE_MARKETS with 5-10 Condition IDs for FOOTBALL-WINNER domain
#   Verify TRADY_AI_ENVIRONMENT is set correctly

# Install dependencies
uv sync

# Verify installation
python scripts/ensure_active_market.py
echo $?   # Should exit 0 if markets are configured

# Create backup directory
mkdir -p data/backups

# Dry-run a session
.venv/bin/trady-ai paper-trade session --domain FOOTBALL-WINNER \
    --non-interactive --duration 10
```

---

## 3. Crontab Configuration (T-011)

The crontab runs two jobs:

### 3.1 Session Cron (`*/15 * * * *`)

```crontab
# Paper Trading — 15-minute session cycle
# Guard runs first; session runs only if guard exits 0
*/15 * * * * cd /opt/trady && python scripts/ensure_active_market.py \
    >> logs/paper-trading.log 2>&1 \
    && .venv/bin/trady-ai paper-trade session \
    --domain FOOTBALL-WINNER --non-interactive --duration 60 \
    >> logs/paper-trading.log 2>&1
```

**Execution flow per trigger:**
1. `ensure_active_market.py` — checks active markets, rotates if expired
2. If guard exits 0 → `trady-ai paper-trade session` runs
3. Session runs: PRE_FLIGHT → CAPTURING (60s) → EXECUTING → REFLECTING → VERIFYING → BUNDLING → COMPLETE
4. Output appended to `logs/paper-trading.log`

**Target:** 2,880 sessions over 30 days (96 sessions/day).

### 3.2 Backup Cron (`0 2 * * *`)

```crontab
# Daily DB backup at 02:00 UTC
0 2 * * * cp /opt/trady/data/trady_ai.db \
    /opt/trady/data/backups/trady_ai-$(date +\%Y\%m\%d).db \
    && sha256sum /opt/trady/data/backups/trady_ai-$(date +\%Y\%m\%d).db \
    > /opt/trady/data/backups/trady_ai-$(date +\%Y\%m\%d).sha256
```

**Note:** In crontab, `%` must be escaped as `\%`.

---

## 4. Daily DB Backup (T-012)

Backups are produced by the 02:00 UTC cron job.

### Backup files

```
data/backups/
├── trady_ai-20260701.db
├── trady_ai-20260701.sha256
├── trady_ai-20260702.db
├── trady_ai-20260702.sha256
...
```

### Verification

```bash
sha256sum -c data/backups/trady_ai-20260701.sha256
```

### Restore

```bash
cp data/backups/trady_ai-20260701.db data/trady_ai.db
```

---

## 5. Initial .env Configuration (T-013)

### Required Variables

```env
# REQUIRED — must be set before first session
TRADY_AI_ACTIVE_MARKETS=0xabc123...,0xdef456...,0x789ghi...
```

Set **5-10 Condition IDs** for the FOOTBALL-WINNER domain. The guard script
will rotate expired markets automatically, but starting with multiple IDs
reduces rotation frequency.

### Polymarket Credentials

For `dry_run` mode (default), Polymarket credentials are optional — the
public REST API is used for market discovery and the WebSocket for event
capture. No API key is required for dry-run market data access.

For `live` execution mode (Phase 6+), set:
```env
TRADY_AI_POLYMARKET_API_KEY=your_api_key
TRADY_AI_POLYMARKET_SECRET=your_secret
TRADY_AI_POLYMARKET_PASSPHRASE=your_passphrase
```

### Per-Process Re-read

Settings uses `frozen=True` with `@lru_cache`. Each cron invocation is a
**fresh Python process** that re-reads `.env` on startup. The guard script
writes updated `TRADY_AI_ACTIVE_MARKETS` to `.env`, and the next process
picks up the change automatically. No daemon restart needed.

---

## 6. Verification Checklist

| # | Check | Command |
|---|-------|---------|
| 1 | Guard exits 0 | `python scripts/ensure_active_market.py; echo $?` |
| 2 | Session dry-run completes | `trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive --duration 10` |
| 3 | Bundles created | `ls -la paper_trading/dia-*/` |
| 4 | DB backup works | Manual: `cp data/trady_ai.db data/backups/test.db` |
| 5 | Crontab active | `crontab -l` |
| 6 | .env readable | `trady-ai status` shows active markets |
| 7 | Logs writing | `tail -f logs/paper-trading.log` |

---

## 7. Rollback Procedure

To revert to Fase 5 (pre-v2) behavior:

```bash
# 1. Remove guard script
rm scripts/ensure_active_market.py

# 2. Revert paper_trading/ to Fase 5 archive
git checkout <fase-5-tag> -- src/trady_ai/paper_trading/

# 3. Restore original crontab
crontab -e
# Replace with pre-v2 entry

# 4. Verify
trady-ai status
```

---

## 8. Monitoring

| Signal | Source | What to watch |
|--------|--------|---------------|
| Rotation events | `grep ROTATION logs/paper-trading.log` | Market change activity |
| Session errors | `grep ERROR logs/paper-trading.log` | Capture/execute/reflect failures |
| Contract violations | `grep CRITICAL logs/paper-trading.log` | TEMPORAL_INTEGRITY violations |
| Session count | `wc -l logs/paper-trading.log` | 96 entries/day expected |
| Disk usage | `df -h /opt/trady/data/` | Backup storage growth |
