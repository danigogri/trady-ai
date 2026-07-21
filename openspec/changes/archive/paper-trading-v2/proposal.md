# Proposal: Paper Trading v2 — Architecture Contract Alignment

## Intent

Fase 5's session-centric model couples Evidence, Decision, and Reflection, blocking independent clock frequencies and sub-daily reconstruction. This change aligns implementation with the frozen 4-clock event-centric Architecture Contract — already designed, approved, frozen.

## Scope

**In Scope:** Guard script (`ensure_active_market.py`) for deterministic market rotation via frozen rules. Per-clock reconstruction by sequence ID (not calendar day). Session lifecycle refined from 7-stage state machine to 4-clock unidirectional flow. 15-min cron rhythm (2,880 sessions/30 days). `--duration` flag for 60s timed capture. Daily DB backup. Frozen eligibility rules. `SessionReport.market_ids` field for operator audit traceability. Initial `TRADY_AI_ACTIVE_MARKETS` configuration (5–10 Condition IDs for week 1). Backlog Protocol integration — all operational findings (bugs, contract violations, anomalies, improvement opportunities) recorded as `BL-XXX` entries per Contract §20.4.

**Out of Scope:** New strategies/analyzers. Hermes (RFC-005). Multi-domain (RFC-006). Autonomous (RFC-008). Live trading (RFC-000). Architecture changes — contract is FROZEN.

## Relationship to Fase 5

Fase 5 (`openspec/changes/archive/fase-5-paper-trading/`) implemented a session-centric orchestrator. This SDD decouples its state machine into 4 independent clocks. Archive remains the baseline. Bundling and contract validation preserved; sequencing and reconstruction change per the Architecture Contract.

## Capabilities

**Modified:** `paper-trading` — transitions from session-centric (7-stage state machine, daily cadence) to 4-clock event-centric (Discovery → Evidence → Decision → Reflection, 15-min cadence, per-sequence reconstruction). Guard added as Discovery Clock.

**New:** None — 4-clock architecture refines the existing capability.

## Approach

Implement frozen Paper Trading Architecture Contract (PAPER-TRADING-ARCHITECTURE-CONTRACT.md, §5-20):
1. **Guard script**: `ensure_active_market.py` — pre-session, stateless, first valid market.
2. **15-min cron**: `*/15 * * * * guard && trady-ai paper-trade session --domain FOOTBALL-WINNER --non-interactive`
3. **Per-clock reconstruction**: Discovery (`.env`), Evidence (`max_seq`), Decision (`last_processed_seq`), Reflection (`last_report_date`)
4. **Session decoupling**: `PaperTradingSession` stages → 4-clock responsibilities, unidirectional flow
5. **Evidence continuity**: guard detects expired markets via API, rotates deterministically

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/ensure_active_market.py` | New | Discovery Clock guard |
| `src/trady_ai/paper_trading/` | Modified | 4-clock unidirectional flow |
| `src/trady_ai/cli/main.py` | Modified | `--duration`, `--non-interactive` |
| `src/trady_ai/paper_trading/models.py` | Modified | `SessionReport.market_ids` field |
| `src/trady_ai/config/` | Modified | `TRADY_AI_ACTIVE_MARKETS` |
| crontab (VPS) | New | 15-min + daily backup |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Guard finds no markets | Low | Fail-fast, next cron retries (OC-2) |
| Reconstruction gap | Low | Sequence-based, sub-daily (AC-4) |
| 96 sessions/day overload | Low | SQLite handles 10M+ rows |

## Rollback Plan

1. Revert `paper_trading/` to Fase 5 archive
2. Remove `scripts/ensure_active_market.py`
3. Restore pre-v2 crontab
4. No migration — uses existing tables

## Success Criteria

- [ ] Guard exits 0 with active markets pre-session
- [ ] Guard rotates expired market to first valid candidate
- [ ] Per-clock reconstruction resumes from interrupted seq
- [ ] 96 sessions/day at 15-min intervals, 30 days
- [ ] Daily DB backup with SHA-256 checksum
- [ ] All existing tests + new guard + 4-clock tests pass
- [ ] Operational findings recorded as BL-XXX entries (Backlog Protocol per Contract §20.4)
