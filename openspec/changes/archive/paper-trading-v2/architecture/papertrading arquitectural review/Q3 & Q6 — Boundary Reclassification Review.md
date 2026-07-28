# Q3 & Q6 — Boundary Reclassification Review

**Status:** PARTIALLY RESOLVED — 7 observations resolved, 6 pending
**Principle:** The Architecture Contract owns architectural truth. Implementation details belong to SDD. Operational procedures belong to the Operations Manual. Infrastructure decisions belong to Deployment.

---

## 1. Q3 Reclassification Table

| ID | Observation | Classification Layer | Keep in Contract? | Owner Artifact | Status |
|---|---|---|---|---|---|
| Q3-1 | AC-1 cross-session verification owner | A — Architecture | YES (cross-reference to §19.1) | Architecture Contract | PENDING |
| Q3-2 | AC-3 enforcement mechanism | A — Architecture | YES (cross-reference to §9.3) | Architecture Contract | PENDING |
| Q3-3 | §13.3 "Random market selection" forbidden actor | A — Architecture | YES (add "Constrains" column) | Architecture Contract | PENDING |
| Q3-4 | §13.3 "LLM-based eligibility" forbidden actor | A — Architecture | YES (add "Constrains" column) | Architecture Contract | PENDING |
| Q3-5 | OC-2 guard script implementation owner | B — SDD Specification | NO | SDD Specification | ✅ RESOLVED |
| Q3-6 | OC-4 DB corruption detection owner | C — Operations Manual | NO | Operations Manual | ✅ RESOLVED |
| Q3-7 | OC-4 Disk full detection owner | D — Deployment | NO | Deployment | ✅ RESOLVED |

---

## 2. Q6 Reclassification Table

| ID | Observation | Classification Layer | Keep in Contract? | Owner Artifact | Status |
|---|---|---|---|---|---|
| Q6-1 | `last_processed_seq` storage location | B — SDD Specification | NO | SDD Specification | ✅ RESOLVED |
| Q6-2 | `last_report_date` storage location | B — SDD Specification | NO | SDD Specification | ✅ RESOLVED |
| Q6-3 | Session day numbering (`dia-NNN`) with sub-daily execution | A — Architecture | YES (§9.1 or §14) | Architecture Contract | PENDING |
| Q6-4 | Guard script API response format | B — SDD Specification | NO | SDD Specification | ✅ RESOLVED |
| Q6-5 | Guard script "FIRST market" determinism | A — Architecture (constraint) + B — SDD (mechanism) | YES (constraint) + NO (mechanism) | Architecture Contract + SDD | PENDING |
| Q6-6 | Alert mechanism for operator | D — Deployment | NO | Deployment | ✅ RESOLVED |

---

## 3. Resolved Observations — Layer Justification

### Q3-5 — Guard Script Implementation Ownership → SDD

**Classification:** B — SDD Specification

**Reasoning:** The architectural truth already exists: AD-5 states the human operator defines frozen rules. AD-4 states the guard script applies them deterministically. Who codes the guard script and who reviews its correctness are implementation and operational concerns. The architecture defines the contract; SDD defines who builds it.

**Owner Artifact:** SDD Specification — Implementation section: "The guard script is implemented as `scripts/ensure_active_market.py`. The human operator verifies its correctness during the Day 0 pre-flight session (Section 9.1 of the Architecture Contract)."

---

### Q3-6 — DB Corruption Detection → Operations Manual

**Classification:** C — Operations Manual

**Reasoning:** The architectural truth is "DB backups exist daily" (OC-1). How backups are verified and who verifies them are operational procedures. The Architecture Contract defines the backup requirement and RTO (Section 20.3). The Operations Manual defines the verification procedure.

**Owner Artifact:** Operations Manual — Paper Trading Operations section: "DB integrity is verified by the operator during each review window by running `sqlite3 data/trady_ai.db "PRAGMA integrity_check"` or by restoring the latest backup and comparing checksums. Anomalies trigger the DB corruption recovery procedure defined in the Architecture Contract Section 20.3."

---

### Q3-7 — Disk Monitoring → Deployment

**Classification:** D — Infrastructure / Deployment

**Reasoning:** The architectural truth is "sessions fail to write bundles when disk is full, and the operator must free space" (OC-4). How disk usage is monitored and how the operator is alerted are infrastructure decisions that depend on the VPS provider, OS tooling, and operator preferences.

**Owner Artifact:** Deployment — VPS configuration section: "Disk usage monitoring via `df -h` in a daily cron job or external VPS monitoring dashboard. Session write failures in `logs/paper-trading.log` are the primary detection mechanism. Operator reviews logs during batched windows. Optional: external monitoring (e.g., provider dashboard, UptimeRobot) for host-level alerts."

---

### Q6-1 — `last_processed_seq` Persistence → SDD

**Classification:** B — SDD Specification

**Reasoning:** The architectural truth is "Decision Clock processes only new events since last_processed_seq" (AC-4). Where this value is persisted is an implementation decision. It could be a `decision_progress` table, a column in `event_store`, an in-memory variable with DB-derived initialization, or a config file. The architecture defines the contract (what must be tracked). SDD defines the mechanism (how it's stored).

**Owner Artifact:** SDD Specification — Decision Clock implementation section: "`last_processed_seq` is derived at session start from `SELECT MAX(seq) FROM event_store WHERE processed = 1` or equivalent tracking mechanism. Implementation may add a `processed` column to `event_store` or maintain a separate `decision_state` table."

---

### Q6-2 — `last_report_date` Persistence → SDD

**Classification:** B — SDD Specification

**Reasoning:** Identical reasoning to Q6-1. The architecture defines the contract (Reflection tracks report dates). SDD defines the storage mechanism. `last_report_date` can be derived from `SELECT MAX(created_at) FROM reflection_reports WHERE domain = ?` — this is an implementation detail.

**Owner Artifact:** SDD Specification — Reflection Clock implementation section: "`last_report_date` is derived at session start from the most recent `reflection_reports.created_at` for the active domain. No separate state table is required."

---

### Q6-4 — Platform API Response Mapping → SDD

**Classification:** B — SDD Specification

**Reasoning:** The API response format is platform-specific implementation knowledge. The architectural contract states the eligibility rules (tags contains "football" AND "winner"). How those tags are extracted from the API response is adapter-level implementation. Different platforms will have different response formats — the architecture must not embed platform specifics.

**Owner Artifact:** SDD Specification — Guard script implementation section: "Eligibility rules reference logical field names. The guard script's Polymarket adapter module maps API response fields to these logical names. For Polymarket, `tags` maps to `response['tags']` (list of strings). For future platforms, new adapter modules provide equivalent mappings."

---

### Q6-6 — Operator Alert Mechanisms → Deployment

**Classification:** D — Infrastructure / Deployment

**Reasoning:** The architectural truth is "the operator detects failures during review windows by inspecting evidence bundles and logs" (Section 14.3, Section 19.1). The architecture already defines the detection mechanism: batch review, not real-time alerting. Whether the operator also configures optional real-time alerts is an infrastructure decision.

**Owner Artifact:** Deployment — VPS configuration section: "Phase 5 relies on batched operator review for failure detection. Optional: configure `cron` MAILTO for cron job output, or external VPS monitoring (e.g., provider dashboard, UptimeRobot) for host-level alerts. These are infrastructure decisions, not architectural requirements."

---

## 4. Pending Observations — Summary

These 6 observations remain under evaluation for the next review iteration. They are all classified as Layer A (Architecture Contract) and are candidates for inclusion as documentation clarifications.

| ID | Observation | Proposed Action |
|---|---|---|
| Q3-1 | AC-1 cross-session verification owner | Add cross-reference from AC-1 to §19.1 |
| Q3-2 | AC-3 enforcement mechanism | Add cross-reference from AC-3 to §9.3 |
| Q3-3 | §13.3 "Random market selection" forbidden actor | Add "Constrains" column to forbidden patterns table |
| Q3-4 | §13.3 "LLM-based eligibility" forbidden actor | Same as Q3-3 (combined) |
| Q6-3 | Session day numbering (`dia-NNN`) | Explicit day numbering contract in §9.1 or §14 |
| Q6-5 | Guard script "FIRST market" determinism | Add determinism constraint to OC-2 (mechanism deferred to SDD) |

---

## 5. Layer Distribution Summary

| Layer | Resolved | Pending | Total |
|---|---|---|---|
| A — Architecture Contract | 0 | 6 | 6 |
| B — SDD Specification | 5 | 0 | 5 |
| C — Operations Manual | 1 | 0 | 1 |
| D — Deployment | 1 | 0 | 1 |
| **Total** | **7** | **6** | **13** |

---

**Status:** The 7 resolved observations are confirmed and ownership is assigned to their respective artifacts. No modifications to the Architecture Contract are required for these items. The 6 pending observations (Q3-1, Q3-2, Q3-3, Q3-4, Q6-3, Q6-5) await the next review iteration.
