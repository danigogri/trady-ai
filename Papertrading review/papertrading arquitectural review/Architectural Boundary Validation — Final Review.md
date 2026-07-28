# Architectural Boundary Validation — Final Review

## Summary Table

| ID | Observation | Real Ambiguity? | Weakens Contract? | Recommendation | Justification |
| --- | --- | --- | --- | --- | --- |
| Q3-1 | AC-1 cross-session verification owner | No | No | REJECT | AC-1 defines the invariant. Verification ownership is operational, not architectural. |
| Q3-2 | AC-3 enforcement mechanism | No | No | REJECT | AC-3 defines the contract. Enforcement mechanism is implementation, not architecture. |
| Q3-3 | §13.3 Random market selection — forbidden actor | No | No | REJECT | Already constrained by Discovery bounded context (§7.1) + AD-4. |
| Q3-4 | §13.3 LLM eligibility — forbidden actor | No | No | REJECT | Same reasoning as Q3-3. |
| Q6-3 | Session day numbering (dia-NNN) | Yes | Yes | ACCEPT | The semantic meaning of dia-NNN is genuinely ambiguous in a sub-daily execution model. |
| Q6-5 | Guard script deterministic selection | No | No | REJECT | AD-4 already states the determinism guarantee. OC-2 is its operational specification. |

## Detailed Justifications

### Q3-1 — AC-1 Cross-Session Verification Owner

**Current text (AC-1, lines 527-528):**

> Cross-session: Any two sessions with the same market_ids, same since_seq, same strategy parameters, and same event_store state must produce identical SessionReport data.

**Analysis:**

The question is whether AC-1 should state WHO verifies cross-session determinism (for example, a cross-reference to §19.1 — operator review windows).

The architectural purpose of AC-1 is to define an invariant — a truth that must hold regardless of who checks it or when. Invariants survive changes in verification mechanism. The per-session verification (verify_replay() in VERIFYING) is stated because it is a runtime enforcement mechanism embedded in the pipeline — it IS architectural (the pipeline self-validates). Cross-session verification is different: it is performed by the operator during review windows, but that could change (automated comparison in Phase 8, CI pipeline, etc.) without changing the invariant.

Adding the cross-reference would:

- Tie the invariant to a specific operational workflow (operator review windows)
- Create a dependency that must be updated if verification moves
- Add navigation convenience without architectural knowledge

**Distinction:** The per-session verify_replay() is architectural because it is a pipeline-embedded enforcement mechanism. The cross-session verification is operational because it is a human-performed check. Architectural contracts should reference the former, not the latter.

**Verdict:** The contract already communicates the architectural truth sufficiently. The invariant is explicit. Who checks it is an operational concern.

→ REJECT

### Q3-2 — AC-3 Enforcement Mechanism

**Current text (AC-3, lines 534-542):**

> No clock may import or depend on modules belonging to another clock's bounded context. Specifically:
>
> - Evidence MUST NOT import from Decision or Reflection
> - Decision MUST NOT import from Reflection
> - Discovery MUST NOT import from Evidence, Decision, or Reflection
>
> Cross-clock communication occurs exclusively through the database and configuration files.

**Analysis:**

The question is whether AC-3 should cross-reference §9.3 (ISOLATION_BOUNDARY check in PRE_FLIGHT).

The ISOLATION_BOUNDARY check is an AST-level import validator in contracts.py. It is one possible enforcement mechanism. But the architectural contract — "clocks are isolated" — survives regardless of enforcement mechanism. If Phase 6 replaces the AST check with a CI lint rule or an architectural fitness function, the contract does not change.

Adding the cross-reference would:

- Tie the contract to a specific implementation of enforcement
- Create staleness risk if enforcement evolves
- Add implementation guidance, not architectural knowledge

**Distinction:** The architectural truth is "clocks do not import from each other." The ISOLATION_BOUNDARY check is implementation of that truth. The contract defines the truth. The SDD defines the check.

**Verdict:** The contract already communicates the architectural truth sufficiently. The enforcement mechanism belongs to implementation.

→ REJECT

### Q3-3 — §13.3 Random Market Selection — Forbidden Actor

**Current text (§13.3, lines 690):**

| Random market selection | Violates A1. Every decision must be reproducible. |

**Analysis:**

The question is whether to add a "Constrains" column specifying that the Discovery Clock (guard script) is the constrained actor.

The constraint "Random market selection" can only apply to one component: the guard script, which is the sole component that selects markets. This is already established by:

1. §7.1 Discovery bounded context MUST NOT: "Rank or optimize markets"
2. AD-4: "No AI, no ranking, no optimization, no strategic selection"
3. §6.1 Discovery Clock definition: "Maintain the catalog of observable markets"

The reader already knows — from three independent locations — that the guard script is the market selector and that it must not rank or randomize. Adding a fourth statement ("Constrains: Discovery Clock") adds redundancy, not architectural knowledge.

**Distinction:** The constraint's owner is already established through bounded context definitions and architectural decisions. The §13.3 table serves as a determinism-specific reinforcement of constraints already stated elsewhere, not as a primary ownership declaration.

**Verdict:** The constrained actor is already unambiguous through context and prior definitions. No architectural ambiguity exists.

→ REJECT

### Q3-4 — §13.3 LLM Eligibility — Forbidden Actor

**Current text (§13.3, lines 691):**

| LLM-based eligibility decisions | Violates RFC-005. Intelligence is for analysis, not operations. |

**Analysis:**

Identical reasoning to Q3-3. The constraint applies to the Discovery context. This is already established by:

1. AD-6: "Hermes and all intelligence systems are excluded from market discovery, market selection..."
2. §7.1 Discovery bounded context MUST NOT: "Rank or optimize markets (belongs to Governance)"
3. RFC-005 §Proposal-Only Doctrine: "Intelligence outputs are proposals"

The constraint is documented in three places already. Adding a "Constrains" column would be the fourth statement of the same architectural truth.

**Verdict:** No architectural ambiguity. The forbidden actor is explicit through AD-6, §7.1, and RFC-005.

→ REJECT

### Q6-3 — Session Day Numbering (dia-NNN)

**Current text (multiple locations):**

- "Evidence bundles written to paper_trading/dia-NNN/" (§9.1)
- "paper_trading/dia-001/session_report.json" (§14.3)
- "Day counter (dia-NNN)" — NOT currently in the contract

**Analysis:**

This is the only observation where a genuine architectural ambiguity exists. Here is why:

The contract defines a 30-day experiment with sub-daily execution (96 sessions/day, AD-9 + OC-1). The evidence model uses dia-NNN as directory naming. But nowhere does the contract explicitly state whether N represents:

- **Interpretation A (correct):** Calendar day (UTC). N ∈ {1..30}. All 96 sessions within the same UTC day share the same dia-NNN directory. Each session overwrites or appends to the same day's bundle.
- **Interpretation B (plausible but wrong):** Session counter. N ∈ {1..2880}. Each of the 2,880 sessions gets its own directory. dia-0001 through dia-2880.

Both interpretations are consistent with the current text. An implementer reading the contract for the first time would need to infer the correct interpretation from context clues ("30-day experiment," "Day 1-30") rather than from an explicit data model contract.

**Why this is architectural, not implementation:**

The dia-NNN semantics define the evidence grouping model — how observations are aggregated for operator review, for calibration readiness computation, and for the Reflection Engine's period scoping. Interpretation A produces 30 evidence bundles reflecting daily aggregates. Interpretation B produces 2,880 bundles reflecting per-session snapshots. These are fundamentally different evidence models.

The calibration gate (§17.2) requires "reflection_reports >= 30 (one per day)." This only makes sense if "day" means calendar day. But the connection between dia-NNN and the calibration gate's definition of "day" is implicit, not explicit.

**Why removal would weaken the contract:**

Without explicit clarification, an implementer could:

- Create 2,880 directories instead of 30, breaking the operator's batch review workflow
- Miscompute the calibration gate (expecting 2,880 reports instead of 30 daily reports)
- Design the bundling stage incorrectly (per-session vs per-day overwrite semantics)

**Verdict:** A real architectural ambiguity exists. The contract must explicitly define the data model.

→ ACCEPT

**Recommended addition to §9.1 or §14:**

The day counter (dia-NNN) increments once per calendar day (UTC). Multiple sessions within the same UTC day share the same day number. The first session of a new UTC day creates a new dia-NNN directory. For the 30-day experiment, N ranges from 1 to 30.

### Q6-5 — Guard Script Deterministic Selection

**Current text (AD-4, line 95):**

> Market rotation — replacing expired Condition IDs to preserve evidence continuity — is a deterministic operation. The guard script applies frozen eligibility rules defined by the human operator before Day 0. No AI, no ranking, no optimization, no strategic selection.

**Analysis:**

The question is whether OC-2 should additionally state: "Given identical frozen eligibility rules and identical platform API state, the guard script MUST select the same market."

AD-4 already states that market rotation "is a deterministic operation." This IS the determinism guarantee. The phrase "deterministic operation" in the context of Constitution A1 means: identical inputs → identical outputs. AD-4 already communicates this unambiguously.

OC-2 describes the algorithm that achieves this determinism ("Take the FIRST market that passes — no ranking, no optimization"). But OC-2 is the operational specification — HOW the guarantee is implemented. The architectural guarantee (THAT it is deterministic) already lives in AD-4.

Adding the formal guarantee to OC-2 would duplicate AD-4's statement without adding new architectural knowledge. The reader who wants to know "is market rotation deterministic?" finds the answer in AD-4. The reader who wants to know "how is it implemented?" finds the answer in OC-2. Both information needs are already satisfied.

**Verdict:** The determinism guarantee is already explicit in AD-4. OC-2 is its operational specification. No architectural ambiguity exists.

→ REJECT

## Final Verdict

| Result | Count | Observations |
| --- | --- | --- |
| ACCEPT | 1 | Q6-3 — Session day numbering (dia-NNN) |
| REJECT | 5 | Q3-1, Q3-2, Q3-3, Q3-4, Q6-5 |

The Architecture Contract requires exactly one addition: an explicit statement defining dia-NNN as a calendar day (UTC) counter, ensuring that sub-daily sessions aggregate their evidence into the same daily directory.

The remaining 5 observations are rejected because the architectural truth they seek to clarify is already present in the contract — either through bounded context definitions (Q3-3, Q3-4), architectural decisions (Q6-5), or because the observation concerns operational/implementation concerns rather than architectural invariants (Q3-1, Q3-2).

This closes the Q3 & Q6 review cycle. All 13 observations are now resolved.