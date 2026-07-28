# Documentation Completeness & Clarity Review

Scope: Documentation quality only. Architecture is frozen. No architectural changes proposed.

## Q1 — Backlog Integration for Operational Findings

### Finding

The document defines how failures are detected (Section 20.1), how they are recovered (OC-4, Section 20.3), and how the operator reviews evidence (Section 14.3, Section 19.1). However, it does not explicitly state where operational findings should be persisted for future action.

Specifically, the following are not addressed:

- Bugs discovered during the 30-day campaign
- Implementation defects in the pipeline
- Contract violations that are WARNING (not CRITICAL)
- Unexpected behaviors that do not trigger a failure
- Improvement opportunities identified during operator review
- Operational anomalies requiring post-campaign investigation

The Backlog Protocol (BACKLOG-PROTOCOL.md) exists as a Portable OS artifact and uses BL-XXX identifiers. The contract references Backlog indirectly via the Constitution but never states that Paper Trading operational findings MUST flow into it.

### Classification

Clarification Needed — Documentation gap, not architectural gap.

### Recommended Documentation Addition

In Section 20 (Failure Model), add a subsection:

#### 20.4 Backlog Integration

All operational findings discovered during the 30-day campaign — including bugs, contract violations, unexpected behaviors, failed experiments, operational anomalies, and improvement opportunities — MUST be recorded as BL-XXX entries following the Backlog Protocol (BACKLOG-PROTOCOL.md).

Findings are triaged during the operator's review windows (approximately every 7 days) and may also be added ad-hoc when the operator detects an anomaly during any VPS session.

And in Section 25.1 (Must Preserve), add to the table:

| Backlog protocol for operational findings | All bugs, violations, anomalies, improvements |

### Existing Coverage Check

- Section 14.3: operator review evidence — covers WHAT to review, not WHERE to persist findings
- OC-4: failure recovery — covers recovery actions, not long-term tracking
- Section 19.1: operator authority — covers review responsibility, not outcome persistence
- BACKLOG-PROTOCOL.md: referenced in document preamble but never operationally connected to Paper Trading

## Q2 — Deferred Decision #23 Clarification

### Finding

Deferred Decision #23 reads:

"Continuous 24/7 capture (beyond session windows)"

This wording is ambiguous. An implementer could interpret it as:

- Interpretation A (incorrect): "The system does not operate continuously" — FALSE. The system operates 24/7 via cron at 15-minute intervals (96 sessions/day).
- Interpretation B (correct): "Market data capture occurs in discrete 60-second windows rather than as a continuous stream" — TRUE. The deferred capability is true 24/7 market data ingestion without gaps between session windows.

### Classification

Wording Improvement — The distinction between "continuous operation" and "continuous capture" is not explicit enough.

### Recommended Documentation Change

Change the wording in Section 23 (Deferred Decisions) from:

Continuous 24/7 capture (beyond session windows)

To:

Continuous 24/7 market data capture (uninterrupted event ingestion between session windows, as opposed to the current 60-second capture windows every 15 minutes)

And clarify in the Rationale column from:

15-min sessions with 60s capture windows are sufficient for calibration

To:

The system already operates continuously (96 sessions/day). The deferred capability is eliminating the 14-minute gaps between 60-second capture windows — i.e., ingesting market data as a continuous 24/7 stream. Current discrete-window capture is sufficient for calibration.

### Additional Clarification Needed

Section 1 (Executive Summary) states:

"The experiment runs continuously on a Linux VPS, scheduled via cron at 15-minute intervals."

This correctly describes continuous operation. The deferred decision should use different terminology to avoid conflating operation continuity with capture continuity.

## Q3 — MUST / MUST NOT / MAY Without Explicit Owner

### Findings

| Location | Statement | Issue |
| --- | --- | --- |
| AC-1 (line 521) | "Every stage of the pipeline MUST produce identical output given identical input state." | Owner is verify_replay() in VERIFYING stage (stated in next sentence). OK — but the enforcement mechanism is mentioned only for per-session, not for cross-session. The cross-session verification owner is not specified. |
| AC-3 (line 532) | "No clock may import or depend on modules belonging to another clock's bounded context." | Owner is not stated. Enforcement mechanism is ISOLATION_BOUNDARY in PRE_FLIGHT (Section 9.3) but this connection is not made explicit here. |
| §13.3 (line 690-694) | "Random market selection — Violates A1." | States what is forbidden but not WHO is forbidden. The guard script is the only component that selects markets — but this should be explicit. |
| §13.3 (line 691) | "LLM-based eligibility decisions — Violates RFC-005." | Same — WHO is forbidden? The Discovery Context MUST NOT statement (Section 7.1) already covers this ("Rank or optimize markets" belongs to Governance). But §13.3 could cross-reference. |
| OC-2 (lines 568-589) | Guard script algorithm | States WHAT the guard script does, but not WHO implements it or who is responsible for its correctness. The "Discovery Clock" is the owner (Section 6.1), but OC-2 doesn't explicitly state this. |
| OC-4 (line 614) | "DB corruption — Backup integrity check" | Detection mechanism says "Backup integrity check" — but who performs this check? The operator? A cron job? This is not specified. |
| OC-4 (line 615) | "Disk full — cron log monitoring" | Same ambiguity. Who monitors the cron log? How is the operator alerted? "Operator alerted" is stated in Response, but the Detection column says "cron log monitoring" which implies automated monitoring — but no automated alert mechanism is defined. |

### Classification

Explicit Ownership Missing — Several enforcement and detection responsibilities lack explicit owners.

### Recommended Documentation Changes

1. AC-1: Add sentence: "Cross-session determinism is verified by the operator during review windows using EvidenceBundler.regenerate_bundle()."
2. AC-3: Add sentence: "This contract is enforced by the ISOLATION_BOUNDARY check in the PRE_FLIGHT stage (Section 9.3)."
3. §13.3: Add a column "Prohibited For" to the table, e.g.:
   - Random market selection → Guard script
   - LLM-based eligibility decisions → Discovery Context
4. OC-2: Add preamble: "The Discovery Clock (guard script) implements this contract. The human operator is responsible for the correctness of frozen eligibility rules embedded in the script."
5. OC-4, DB corruption row: Change Detection from "Backup integrity check" to "Operator-performed integrity check during review windows or ad-hoc investigation."
6. OC-4, Disk full row: Change Detection from "cron log monitoring" to "Session writes fail (ERROR in session_report.json). Operator detects during review window."

## Q4 — "The System Decides" Pattern Search

### Findings

The document was searched for instances of "the system decides," "the system determines," "the system selects," "the system evaluates," and similar agent-ambiguous phrasing.

| Location | Text | Status |
| --- | --- | --- |
| §2.3 (line 55) | "The architecture is domain-agnostic by design." | OK — refers to the architecture, not an agent |
| §6.3 (line 213) | "The architecture was validated for completeness..." | OK |
| §8.2 (line 377) | "Human retains freeze, rollback, and override authority over every clock." | OK — explicit owner |
| §13.2 (line 684) | "Guard script detects via API, not via timing assumptions" | OK — explicit owner |
| §9.3 | Session lifecycle stages | OK — each stage has explicit actors (contracts, analyzers) |
| §20.3 (line 965) | "Reconstruction skips completed stages" | Clarification Needed — WHO/WHAT performs reconstruction? The answer is _reconstruct_stages() in PaperTradingSession, but this is not stated in Section 20. |
| §20.3 (line 966) | "Each cron execution retries guard" | OK — explicit mechanism |

### Classification

Wording Improvement — One instance where an action ("Reconstruction skips completed stages") lacks an explicit actor reference. The rest of the document consistently uses explicit owners.

### Recommended Documentation Change

Section 20.3, "Single session failure" row, change "Reconstruction skips completed stages" to "_reconstruct_stages() in PaperTradingSession skips already-completed stages."

## Q5 — Duplicated Doctrinal Statements

### Findings

The following statements appear in multiple sections. This is generally intentional (cross-referencing for different audiences), but some pairs could drift if only one is updated:

| Statement | Appears In | Drift Risk |
| --- | --- | --- |
| "Hermes excluded from critical path / operational critical path" | AD-6 (line 101), Section 17.3 (line 843), RA-2 (line 1053) | Low — all three say the same thing with different levels of detail. AD-6 is the authoritative statement. |
| "Dry run enforced" | Section 2.2 (line 43), Section 9.3 (line 450), Section 16.2 (line 809) | Low — each appearance serves a different purpose (scope, lifecycle stage, risk constraint) |
| "Fail-fast" as principle and as failure model behavior | Section 3 (line 67), Section 20.1 (lines 944-948) | Low — principle vs operational application |
| "Human sovereignty / governance externalized" | AD-5 (line 99), Section 12.1 (line 624), Section 19.1 (line 905) | Medium — AD-5 says "batched windows (7 days)". Section 19.1 also says "7 days". If one changes, the other must be updated. Add a cross-reference from Section 19.1 to AD-5. |
| "15-minute execution rhythm" | AD-9 (line 115), OC-1 (line 561) | Medium — Both state 15 minutes. If changed, both must be updated. Add a cross-reference from OC-1 to AD-9. |

### Classification

No Action Required — The duplications serve distinct purposes (decision record vs operational contract vs principle application). The drift risk is acceptable because:

1. The document is frozen — changes require explicit amendment (Section 27)
2. Cross-references between sections would reduce but not eliminate drift risk
3. The two medium-risk pairs (Human Sovereignty, Execution Rhythm) could benefit from explicit cross-references

### Optional Improvement

Add to AD-5: "(see Section 19.1 for detailed authority boundaries)"

Add to AD-9: "(see OC-1 for operational schedule specification)"

## Q6 — Implementation Completeness

### Assessment

After reviewing every section for architectural decisions an implementer would still need to make, the following gaps were identified:

| Gap | Location | Impact |
| --- | --- | --- |
| last_processed_seq storage | AC-4 (line 546), Section 16.1 (line 798) | The contract says Decision tracks last_processed_seq but does not specify WHERE this is stored (in-memory? DB table? config file?). An implementer must decide. |
| last_report_date storage | AC-4 (line 547), Section 17.1 (line 826) | Same ambiguity for Reflection's progress tracking. |
| Session day numbering (dia-NNN) | Section 5 diagram (line 164), Section 9.1 (line 410), Section 14.1 (line 708) | With sub-daily execution (96 sessions/day), how is dia-NNN computed? The current _compute_day() counts reflection_reports. With per-sequence reconstruction, day numbering needs clarification: is each cron execution a new day counter, or do 96 sessions share the same day number? |
| Guard script: API response format | OC-2 (lines 578-580) | The algorithm assumes tags contains "football" AND "winner" — but Polymarket API response format for tags is not specified. An implementer must discover the actual field name and structure. |
| Guard script: "take the FIRST market" | OC-2 (line 583) | "First" is ambiguous: first in API response order? Lexicographically? By creation date? This affects determinism. |
| Alert mechanism for operator | OC-4 (lines 614-615) | "Operator alerted" is stated as response for DB corruption and disk full, but no alert mechanism is specified. SSH? Email? External monitoring? |

### Classification

Clarification Needed — The architecture is conceptually complete, but 6 implementation-level decisions remain implicit. None require architectural changes — only documentation clarification.

### Recommended Documentation Changes

1. AC-4: Add column "Storage" to the reconstruction tracking table:
   - Discovery: .env (existing)
   - Evidence: event_store.max(seq) (derived from DB)
   - Decision: decision_progress table or event_store marker column
   - Reflection: reflection_reports.max(created_at) (derived from DB)
2. Section 9.3: Add note about day numbering:
   "Day counter (dia-NNN) increments once per calendar day (UTC). Multiple sessions within the same calendar day share the same day number. The first session of a new UTC day creates a new dia-NNN directory."
3. OC-2: Document the Polymarket API response field used for tags. Currently the algorithm is pseudo-code. Add:
   "The guard script queries GET /markets and inspects the tags field (list of strings) in each market object from the Polymarket API response."
4. OC-2: Clarify "first":
   "Take the FIRST market that passes (first in API response iteration order — this is deterministic because the API response order is deterministic for a given request at a given time)."
5. OC-4: Add explicit alert mechanism:
   "Operator detection occurs during batched review windows (~7 days) by inspecting session_report.json ERROR states, contracts.json CRITICAL violations, and logs/paper-trading.log for rotation failures. No real-time alert mechanism exists in Phase 5."

### Overall Assessment

The architecture appears implementation-complete — no implementer needs to make an architectural decision. The 6 gaps above are documentation clarifications, not missing architectural decisions. Every bounded context, clock, dependency, contract, and constraint is explicitly defined.

### Summary of All Findings

| # | Question | Classification | Count |
| --- | --- | --- | --- |
| Q1 | Backlog integration | Clarification Needed | 1 gap |
| Q2 | Deferred Decision #23 wording | Wording Improvement | 1 ambiguity |
| Q3 | MUST/MUST NOT/MAY without owner | Explicit Ownership Missing | 6 instances |
| Q4 | "The system decides" pattern | Wording Improvement | 1 instance |
| Q5 | Duplicated doctrinal statements | No Action Required | 0 changes needed (2 optional cross-references) |
| Q6 | Implementation completeness | Clarification Needed | 6 gaps (all documentation, none architectural) |

Total: 15 observations. Zero architectural changes proposed. All are documentation-quality improvements.