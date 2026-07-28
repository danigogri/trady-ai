# Q3 & Q6 — Boundary Reclassification Review

**Principle applied:** The Architecture Contract owns architectural truth. Implementation details belong to SDD. Operational procedures belong to the Operations Manual. Infrastructure decisions belong to Deployment.

## 1. Q3 Reclassification Table

### Observation Q3-1: AC-1 cross-session verification owner
- **Original finding:** AC-1 states cross-session determinism MUST hold, but does not state who verifies it.
- **Purpose:** Define who enforces the cross-session determinism contract.
- **Classification Layer:** A — Architecture Contract
- **Reasoning:** The architectural truth is "cross-session determinism is verifiable." WHO verifies it (operator during review windows via EvidenceBundler.regenerate_bundle()) is a governance boundary concern. This belongs in the architectural contract because it defines which layer owns verification responsibility. Section 19.1 already covers operator review duties — AC-1 should cross-reference it.
- **Keep in Architecture Contract?** YES — as a cross-reference from AC-1 to Section 19.1. The architectural truth (operator verifies cross-session determinism during review windows) already exists at 19.1. AC-1 just needs to point to it.
- **Future artifact if moved:** N/A (stays)

### Observation Q3-2: AC-3 enforcement mechanism owner
- **Original finding:** AC-3 states "No clock may import..." but does not state what enforces this.
- **Purpose:** Connect the architectural contract (AC-3) to its enforcement mechanism.
- **Classification Layer:** A — Architecture Contract
- **Reasoning:** The enforcement mechanism (ISOLATION_BOUNDARY check in PRE_FLIGHT, documented in Section 9.3) IS architectural knowledge. An architectural contract without its enforcement mechanism is incomplete. The contract says what must not happen; the enforcement says how it's caught. Both are architectural.
- **Keep in Architecture Contract?** YES — as a cross-reference from AC-3 to Section 9.3 (ISOLATION_BOUNDARY in PRE_FLIGHT). The connection between contract and enforcement is architectural, not operational.
- **Future artifact if moved:** N/A (stays)

### Observation Q3-3: §13.3 "Random market selection" — forbidden actor
- **Original finding:** States a prohibited pattern but not WHO is prohibited.
- **Purpose:** Define which bounded context is constrained by the prohibition.
- **Classification Layer:** A — Architecture Contract
- **Reasoning:** The prohibition "Random market selection" constrains the Discovery Clock (guard script). Stating who is constrained is architectural — it defines the boundary of the constraint. Without the actor, the prohibition is floating doctrine with no owner.
- **Keep in Architecture Contract?** YES — §13.3 table should include a "Constrains" column. Architectural because it defines which bounded context a deterministic constraint applies to.
- **Future artifact if moved:** N/A (stays)

### Observation Q3-4: §13.3 "LLM-based eligibility decisions" — forbidden actor
- **Original finding:** Same as Q3-3.
- **Classification Layer:** A — Architecture Contract
- **Reasoning:** Identical to Q3-3. The prohibition constrains the Discovery Context. Architectural because it defines the boundary of RFC-005 compliance.
- **Keep in Architecture Contract?** YES — same treatment as Q3-3.
- **Future artifact if moved:** N/A (stays)

### Observation Q3-5: OC-2 guard script — implementation owner
- **Original finding:** OC-2 states what the guard script does but not who implements it or who is responsible for its correctness.
- **Purpose:** Define ownership of guard script implementation and correctness.
- **Classification Layer:** B — SDD Specification
- **Reasoning:** The architectural truth already exists: AD-5 states the human operator defines frozen rules. AD-4 states the guard script applies them deterministically. WHO codes the guard script (an implementer) and WHO reviews its correctness (operator during Day 0 pre-flight) are implementation and operational concerns respectively. The architecture defines the contract; SDD defines who builds it.
- **Keep in Architecture Contract?** NO — belongs to the Paper Trading SDD Specification. The architectural truth (rules defined by human, applied by script) is already in AD-4 and AD-5. Implementation ownership adds no architectural knowledge.
- **Future artifact if moved:** SDD Specification — Implementation section: "The guard script is implemented as scripts/ensure_active_market.py. The human operator verifies its correctness during the Day 0 pre-flight session (Section 9.1)."

### Observation Q3-6: OC-4 DB corruption — detection owner
- **Original finding:** "Backup integrity check" is stated as detection mechanism but who performs it is not specified.
- **Purpose:** Define who detects DB corruption.
- **Classification Layer:** C — Operations Manual
- **Reasoning:** The architectural truth is "DB backups exist daily" (OC-1). HOW backups are verified and WHO verifies them are operational procedures. The Architecture Contract defines the backup requirement and RTO. The Operations Manual defines the verification procedure.
- **Keep in Architecture Contract?** NO — belongs to the Operations Manual under incident response procedures. The architectural contract already defines the RTO (Section 20.3: ~10 minutes via restore + replay). The detection procedure is operational.
- **Future artifact if moved:** Operations Manual — Paper Trading Operations section: "DB integrity is verified by the operator during each review window by running sqlite3 data/trady_ai.db "PRAGMA integrity_check" or by restoring the latest backup and comparing checksums. Anomalies trigger the DB corruption recovery procedure."

### Observation Q3-7: OC-4 Disk full — detection owner
- **Original finding:** "cron log monitoring" is stated but who monitors and how alerts work is unspecified.
- **Purpose:** Define disk full detection and alerting.
- **Classification Layer:** D — Infrastructure / Deployment
- **Reasoning:** The architectural truth is "sessions fail to write bundles when disk is full, and the operator must free space" (OC-4). HOW disk usage is monitored (cron, systemd, external monitoring) and HOW the operator is alerted are infrastructure/deployment decisions. They depend on the VPS provider, OS tooling, and operator preferences.
- **Keep in Architecture Contract?** NO — belongs to the Deployment documentation. The architectural contract already defines the failure mode and recovery action. The monitoring mechanism is infrastructure.
- **Future artifact if moved:** Deployment — VPS setup section: "Disk usage monitoring via df -h in a daily cron job or external VPS monitoring dashboard. Sessions write failures in logs/paper-trading.log are the primary detection mechanism. Operator reviews logs during batched windows."

## 2. Q6 Reclassification Table

### Observation Q6-1: last_processed_seq storage location
- **Original finding:** AC-4 says Decision tracks last_processed_seq but does not specify where it is stored.
- **Purpose:** Define persistence mechanism for Decision Clock progress tracking.
- **Classification Layer:** B — SDD Specification
- **Reasoning:** The architectural truth is "Decision Clock processes only new events since last_processed_seq" (AC-4). WHERE this value is persisted is an implementation decision. It could be a decision_progress table, a column in event_store, an in-memory variable with DB-derived initialization, or a config file. The architecture defines the contract (what must be tracked). SDD defines the mechanism (how it's stored).
- **Keep in Architecture Contract?** NO — belongs to SDD. The architectural contract is satisfied by stating "Decision tracks progress." The implementation chooses the storage mechanism.
- **Future artifact if moved:** SDD Specification — Decision Clock implementation section: "last_processed_seq is derived at session start from SELECT MAX(seq) FROM event_store WHERE processed = 1 or equivalent tracking mechanism. Implementation may add a processed column to event_store or maintain a separate decision_state table."

### Observation Q6-2: last_report_date storage location
- **Original finding:** AC-4 says Reflection tracks last_report_date but does not specify where.
- **Purpose:** Define persistence mechanism for Reflection Clock progress tracking.
- **Classification Layer:** B — SDD Specification
- **Reasoning:** Identical reasoning to Q6-1. The architecture defines the contract. SDD defines the storage. last_report_date can be derived from SELECT MAX(created_at) FROM reflection_reports WHERE domain = ? — this is an implementation detail.
- **Keep in Architecture Contract?** NO — belongs to SDD.
- **Future artifact if moved:** SDD Specification — Reflection Clock implementation section: "last_report_date is derived at session start from the most recent reflection_reports.created_at for the active domain. No separate state table is required."

### Observation Q6-3: Session day numbering (dia-NNN) with sub-daily execution
- **Original finding:** With 96 sessions/day, how is dia-NNN computed?
- **Purpose:** Define evidence organization contract for sub-daily sessions.
- **Classification Layer:** A — Architecture Contract
- **Reasoning:** This IS architectural. The contract defines a 30-day experiment with evidence organized per day (dia-NNN). If N increments every session, you'd have 2,880 directories, not 30. The architectural truth — "one day = one calendar day (UTC), all sessions within that day share the same day number" — defines the evidence organization contract. This affects how the operator reviews evidence, how calibration readiness is computed, and how reconstruction works.
- **This is NOT an implementation detail because it defines the grouping semantics of the entire evidence model. A different interpretation (N = session counter) would produce a fundamentally different evidence structure.**
- **Keep in Architecture Contract?** YES — should be explicitly stated in Section 9.1 or Section 14. The architectural truth must be explicit, not implied.
- **Future artifact if moved:** N/A (stays)

### Observation Q6-4: Guard script — Polymarket API response format
- **Original finding:** OC-2 algorithm references tags field but the Polymarket API response format is not specified.
- **Purpose:** Document the platform-specific data format for eligibility filtering.
- **Classification Layer:** B — SDD Specification
- **Reasoning:** The API response format is platform-specific implementation knowledge. The architectural contract states the eligibility rules (tags contains "football" AND "winner"). HOW those tags are extracted from the API response is adapter-level implementation. Different platforms will have different response formats — the architecture must not embed platform specifics.
- **Keep in Architecture Contract?** NO — belongs to SDD (Polymarket adapter specification) or to the guard script's own documentation. The architecture defines the contract; the adapter defines the mapping.
- **Future artifact if moved:** SDD Specification — Guard script implementation section: "Eligibility rules reference logical field names. The guard script's Polymarket adapter module maps API response fields to these logical names. For Polymarket, tags maps to response['tags'] (list of strings). For future platforms, new adapter modules provide equivalent mappings."

### Observation Q6-5: Guard script — "take the FIRST market" determinism
- **Original finding:** "First" is ambiguous — first in API response order? Lexicographic? By creation date?
- **Purpose:** Define the deterministic ordering contract for market selection.
- **Classification Layer:** A — Architecture Contract (the determinism constraint) + B — SDD Specification (the specific ordering mechanism)
- **Reasoning:** This observation has two layers:
  - Architectural (Layer A): The contract MUST state that market selection is deterministic. The current contract says "no ranking, no optimization, no AI" (AD-4) but does not explicitly state that the selection order is deterministic. The architectural truth is: "Given identical eligibility rules and identical API state, the same market is always selected." This IS architectural because it's a determinism guarantee.
  - Implementation (Layer B): HOW determinism is achieved (iteration order, sorting by a field, etc.) is an implementation choice. The architecture says it must be deterministic; the implementation chooses the mechanism.
- **Keep in Architecture Contract?** YES — for the determinism constraint. The Architecture Contract must state: "The guard script selects markets deterministically. Given identical frozen eligibility rules and identical platform API state, the same market is always selected." The implementation mechanism (iteration order, stable sort, fixed key) is SDD.
- **Future artifact if moved:** The determinism constraint stays in OC-2. The specific ordering mechanism belongs in SDD: "The guard script iterates the API response in its native order. Polymarket returns markets in a stable order for identical queries. If future platforms do not guarantee stable ordering, the guard script MUST apply a deterministic sort key (e.g., condition_id lexicographic order)."

### Observation Q6-6: Alert mechanism for operator
- **Original finding:** "Operator alerted" is stated but no alert mechanism is specified.
- **Purpose:** Define how the operator receives notification of failures.
- **Classification Layer:** D — Infrastructure / Deployment
- **Reasoning:** The architectural truth is "the operator detects failures during review windows by inspecting evidence bundles and logs" (Section 14.3, Section 19.1). The architecture already defines the detection mechanism: batch review, not real-time alerting. Adding a real-time alert mechanism would be an infrastructure/deployment decision that depends on the VPS provider, available tooling, and operator preference.
- **The contract states:** "No real-time alert mechanism exists in Phase 5." This IS already implicit in the batched review model. Making it explicit is documentation clarity, not architectural change.
- **Keep in Architecture Contract?** NO — belongs to Deployment documentation. The architecture defines the review model (batched, ~7 days). Whether the operator also configures optional alerts is infrastructure.
- **Future artifact if moved:** Deployment — VPS configuration section: "Phase 5 relies on batched operator review for failure detection. Optional: configure cron MAILTO for cron job output, or external VPS monitoring (e.g., Hetzner Cloud monitoring, UptimeRobot) for host-level alerts. These are infrastructure decisions, not architectural requirements."

## 3. Layer Justification

| Layer | Owns | Examples from Q3/Q6 |
| --- | --- | --- |
| A — Architecture Contract | Architectural truth, bounded contexts, contracts, governance boundaries, determinism guarantees, clock definitions, dependency direction | Q3-1 through Q3-4, Q6-3, Q6-5 (determinism constraint) |
| B — SDD Specification | Implementation design, persistence mechanisms, adapter mappings, algorithm details, storage decisions | Q3-5, Q6-1, Q6-2, Q6-4, Q6-5 (ordering mechanism) |
| C — Operations Manual | Operational procedures, operator workflows, monitoring procedures, incident response, maintenance playbooks | Q3-6 |
| D — Infrastructure / Deployment | VPS configuration, cron behavior, filesystem layout, logging infrastructure, alerting, OS, networking | Q3-7, Q6-6 |

## 4. Recommended Owner Artifact

| Observation | Keep in Contract? | Owner Artifact |
| --- | --- | --- |
| Q3-1: AC-1 cross-session verification owner | YES | Architecture Contract (cross-reference to §19.1) |
| Q3-2: AC-3 enforcement mechanism | YES | Architecture Contract (cross-reference to §9.3) |
| Q3-3: §13.3 "Random market selection" forbidden actor | YES | Architecture Contract (add "Constrains" column) |
| Q3-4: §13.3 "LLM-based eligibility" forbidden actor | YES | Architecture Contract (add "Constrains" column) |
| Q3-5: OC-2 guard script implementation owner | NO | SDD Specification |
| Q3-6: OC-4 DB corruption detection owner | NO | Operations Manual |
| Q3-7: OC-4 Disk full detection owner | NO | Deployment |
| Q6-1: last_processed_seq storage | NO | SDD Specification |
| Q6-2: last_report_date storage | NO | SDD Specification |
| Q6-3: Session day numbering (dia-NNN) | YES | Architecture Contract (§9.1 or §14) |
| Q6-4: Guard script API response format | NO | SDD Specification |
| Q6-5: Guard script "FIRST market" determinism | YES (constraint) + NO (mechanism) | Architecture Contract (determinism constraint in OC-2) + SDD (ordering mechanism) |
| Q6-6: Alert mechanism for operator | NO | Deployment |

## 5. Final Recommendation

Of the 13 observations in Q3 and Q6, only 6 belong in the Architecture Contract. The remaining 7 belong to lower layers:

| Layer | Count | Observations |
| --- | --- | --- |
| A — Architecture Contract | 6 | Q3-1, Q3-2, Q3-3, Q3-4, Q6-3, Q6-5 (determinism constraint) |
| B — SDD Specification | 5 | Q3-5, Q6-1, Q6-2, Q6-4, Q6-5 (ordering mechanism) |
| C — Operations Manual | 1 | Q3-6 |
| D — Deployment | 2 | Q3-7, Q6-6 |

Architectural Contract additions (6 items):
1. AC-1 → cross-reference to §19.1 (operator verifies cross-session determinism)
2. AC-3 → cross-reference to §9.3 (ISOLATION_BOUNDARY enforces clock isolation)
3. §13.3 → add "Constrains" column to forbidden non-determinism table
4. §13.3 → same (combined with #3)
5. §9.1 or §14 → explicit day numbering contract: "Day counter (dia-NNN) increments once per calendar day (UTC). All sessions within the same UTC day share the same day number."
6. OC-2 → explicit determinism statement: "Given identical frozen eligibility rules and identical platform API state, the guard script MUST select the same market."

Deferred to lower layers (7 items):
- SDD: guard script implementation ownership, last_processed_seq storage, last_report_date storage, API response format mapping, ordering mechanism
- Operations Manual: DB backup integrity check procedure
- Deployment: disk usage monitoring, operator alert mechanism

The Architecture Contract should not absorb implementation details, operational procedures, or deployment decisions. This boundary discipline keeps the contract focused on architectural truth.
