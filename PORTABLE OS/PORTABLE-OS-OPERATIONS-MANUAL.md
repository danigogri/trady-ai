# PORTABLE-OS OPERATIONS MANUAL

**Status:** ACTIVE
**Authority Level:** Architecture + Execution (adaptable)
**Version:** 1.0
**Derives Authority From:** PORTABLE-OS-CONSTITUTION.md

---

# 1. PURPOSE

This document defines the operational procedures, protocols, and optional doctrines for projects adopting the Portable Operating System.

It translates the Constitution's principles into actionable procedures.

This Manual is adaptable. Projects may modify procedures to fit their context, provided they do not violate the Constitution.

The Constitution is immutable. This Manual is not.

---

# 2. RELATIONSHIP TO THE CONSTITUTION

This Manual derives its authority from the Constitution.

Where this Manual and the Constitution appear to conflict, the Constitution prevails.

This Manual does not restate Constitutional principles. It references them by designation (A1-A8, B1-B6) and builds procedures upon them.

Before adding any procedure to this Manual, verify it does not duplicate an existing procedure or restate a Constitutional principle. Governance minimalism (A6) applies here.

---

# 3. INTEGRATION DOCTRINE

*Built upon: A1 (Deterministic-First), A3 (Boundary Discipline), B2 (Integration Hostility)*

---

## 3.1 Core Posture

Every integration changes the operational shape of the system.

Every dependency introduces operational cost. Every tool introduces lifecycle assumptions. Every service introduces architectural exposure.

The objective is NOT maximizing integrations. The objective is preserving coherent system evolution.

---

## 3.2 Integration Lifecycle

No integration enters stable baseline directly.

```
PROPOSED
  → UNDER REVIEW
  → SANDBOX TESTED
  → APPROVED
  → STABILIZED
  → BASELINE-ACCEPTED
  → DEPRECATED
  → REMOVED
```

Rules:
- experimental integrations must remain isolated
- sandbox testing precedes operational acceptance
- stabilization is mandatory before baseline admission
- deprecated integrations must remain auditable
- removal is incomplete until operational surface disappearance is verified

---

## 3.3 Integration Review Requirements

Every integration must pass:

1. **Functional review** — What does it do? What problem does it solve?
2. **Architectural review** — Does it fit the project's boundaries and contracts?
3. **Installation review** — What does the installer mutate? (shells, environments, services, hooks, startup behavior)
4. **Dependency review** — What does it depend on? What depends on it transitively?
5. **Operational review** — What is the maintenance, rollback, and audit burden?
6. **Boundary review** — What modules, contracts, and freezes does it affect?

No integration is considered safe by default. Official installation instructions are not automatically trusted.

---

## 3.4 Direct Remote Execution

Direct remote execution is prohibited by default:

```
curl ... | bash
wget ... | sh
```

Required process: retrieve → inspect → analyze → isolate → execute.

No remote script receives implicit trust.

---

## 3.5 Integration Drift Types

| Type | Description |
|---|---|
| Dependency drift | Dependencies evolve silently outside reviewed assumptions |
| Runtime drift | Runtime behavior evolves outside the expected operational model |
| Boundary drift | An integration invades responsibilities outside its intended boundary |
| Operational drift | An integration alters expected lifecycle behavior |
| Complexity drift | An integration increases cumulative complexity without proportional value |

Undocumented drift is operational risk.

---

## 3.6 Integration Risk Levels

| Level | Characteristics | Requirements |
|---|---|---|
| 0 — Safe | No runtime mutation, no orchestration | Minimal review |
| 1 — Development | Affects dev environment, not runtime | Isolated installation, shell review |
| 2 — Runtime-adjacent | Interacts with lifecycle, may affect execution flow | Boundary audit, rollback plan, freeze impact review |
| 3 — Architectural | Capable of redefining operational architecture | Full architectural review, explicit approval, isolated experimentation |

---

## 3.7 Revalidation

Approval is not permanent.

Revalidation triggers:
- dependency changes
- runtime behavior changes
- major version upgrades
- transitive dependency expansion
- operational drift

Dependency drift equals operational drift. Critical integrations require periodic re-audit.

---

# 4. DEPENDENCY GOVERNANCE

*Built upon: B2 (Integration Hostility), A1 (Deterministic-First)*

---

## 4.1 Trust Philosophy

Popularity is not trust. Trust is not security. Security is not architectural fit.

A dependency may be:
- popular but unsafe
- secure but operationally expensive
- trusted but architecturally incompatible
- technically excellent but operationally unnecessary

Each dimension must be evaluated independently.

---

## 4.2 Version Pinning

Determinism takes precedence over convenience.

Approved: explicit version pins (`package@1.4.2`)

Discouraged: floating ranges (`^1.4.2`, `~1.4.2`, `latest`)

Dependency versions should remain explicit whenever operationally practical.

---

## 4.3 Cooling Periods

Newly published versions should not be adopted immediately.

| Dependency type | Recommended wait |
|---|---|
| Development tools | 24 hours |
| Standard libraries | 72 hours |
| Core dependencies | 7 days |
| Security-critical dependencies | 14 days |
| Critical infrastructure | Manual review required |

Immediate adoption requires explicit justification.

---

## 4.4 Supply Chain Controls

Recommended controls:
- lock files (version controlled, treated as security artifacts)
- post-install script review (scripts disabled by default)
- provenance verification
- dependency auditing
- allow lists
- dependency scanners

Lock files are security artifacts. Manual lock file modification is discouraged.

---

## 4.5 Dependency Removal

Unused dependencies are operational debt.

Dependencies should be removed when:
- no longer required
- operational value declines
- maintenance burden exceeds benefit
- security exposure becomes unjustified

Removal capability must remain feasible throughout the lifecycle.

---

# 5. STABILIZATION PROTOCOL

*Built upon: B1 (Freeze Discipline), B4 (Stabilization Progression), A8 (Evidence Before Complexity)*

---

## 5.1 Lifecycle Windows

| Window | Purpose |
|---|---|
| Implementation | Controlled construction and bounded mutation |
| Audit | Drift analysis, boundary review, architecture validation |
| Freeze | Contract stabilization and mutation hardening |
| Reconciliation | Controlled foundational mutation with explicit lineage |

---

## 5.2 Freeze Hierarchy

Not all layers freeze equally. Foundational layers freeze earlier and mutate less.

| Layer | Expected Stability |
|---|---|
| Core principles | Permanent |
| Source of truth | Near-permanent |
| Governance doctrine | Extremely stable |
| Contracts | Highly stable |
| Interfaces | Stable |
| Parameters | Semi-adaptive |
| Heuristics | More adaptive |
| Experimental layers | Most adaptive |

---

## 5.3 Audit Protocol

Audits must verify:
- doctrinal adherence
- architectural drift
- complexity inflation
- ownership violations
- boundary preservation
- observability degradation
- dependency expansion

Audits should be:
- lifecycle-aware (what phase is being audited)
- mutation-aware (what changed since last audit)
- evidence-aware (what claims are being validated)

"Looks correct" is not validation (A8).

---

## 5.4 Reconciliation Rules

Foundational mutation may occasionally become necessary.

When it does:
- reconciliation should remain rare
- lineage must remain explicit
- rollback feasibility must survive
- reasoning must remain documented
- approval must remain mandatory

Reconciliation exists to preserve survivability, not to normalize instability.

---

## 5.5 Review Methodology

*Built upon: A3 (Boundary Discipline), A6 (Governance Minimalism), A8 (Evidence Before Complexity), B6 (Structured Work Cycle)*

### Definition

A review is the systematic application of a single universal 12-step analytical methodology. All 12 steps execute in order on every artifact under review, regardless of artifact type, size, or complexity. Every review begins here.

If a step is not applicable to the artifact under review, the reviewer concludes "Not applicable" and proceeds to the next step. Subsets, shortcuts, and alternative review flows are not permitted (A3 — Boundary Discipline).

This methodology is generic. It applies to any artifact: governance documents, specs, designs, code, configuration, proposals, reports, or records. It is the methodology that Review Gates (see SDD Cycle Governance) apply at each lifecycle transition.

### Phase Structure

The 12 steps are grouped into 4 logical phases for readability, training, and automation. These phases are presentational only — they do not create alternative entry points, and all 12 steps execute regardless of phase grouping.

**Context Reconstruction** (Steps 1–2): Establish what the artifact is authorized to define and what ecosystem it belongs to. Before analyzing content, understand authority and context.

**Consistency Analysis** (Steps 3–5): Search for what is wrong, what is missing, and what is duplicated. These steps overlap with audit criteria defined in §5.3 (Audit Protocol) — see cross-reference below for guidance on WHAT to validate.

**Architectural Integrity** (Steps 6–8): Verify that responsibilities are coherent, dependencies are intentional, and the artifact can evolve without architectural drift.

**Quality Validation** (Steps 9–12): Validate terminology, philosophical alignment, operational risk, and future technical debt. These steps look beyond correctness toward sustainability.

### Step 1 — Identify Authority

Every review begins with authority before content. Identify the artifact's authority level: what it is allowed to define, what it must inherit from higher-authority documents, and what it cannot override.

Determine:
- Which principles, policies, or contracts govern this artifact?
- What does the artifact have authority to define?
- What boundaries must it respect?
- What is outside its scope?

The artifact must not contradict its governing authority. If it does, that is a finding.

### Step 2 — Reconstruct Context

Review the artifact against the complete ecosystem, not against a single document. Reconstruct the architectural context: which documents, contracts, decisions, and frozen artifacts relate to this work product?

Load at minimum:
- The artifact's governing authority (identified in Step 1)
- Related artifacts in the same domain
- Previously frozen or archived decisions
- Existing contracts and boundaries that intersect with the artifact

A review that only inspects the artifact in isolation misses contextual contradictions.

### Step 3 — Detect Contradictions

Search for contradictions across all authoritative artifacts. Contradictions include conflicting ownership, overlapping responsibilities, incompatible lifecycle definitions, competing authority claims, inconsistent terminology, or broken boundary contracts.

(see §5.3 — Audit Protocol for criteria on what constitutes architectural drift, ownership violation, and boundary breach)

Document each contradiction as a finding with: the conflicting statements, the source locations, and the authority that resolves the conflict.

### Step 4 — Detect Missing Information

Ask: Who owns this? Who initializes it? Who destroys it? Who validates it? Who persists it? Who approves it? Who is responsible if it fails?

Missing information is often more critical than incorrect statements. An artifact that omits ownership, lifecycle, or failure responsibility is incomplete regardless of how correct its stated content is.

(see §5.3 — Audit Protocol for audit-specific validation criteria on ownership and lifecycle verification)

### Step 5 — Detect Duplication

Search for duplicated concepts, ownership, responsibilities, doctrine, lifecycle rules, contracts, or documentation across the artifact and the broader ecosystem.

Determine whether duplication creates future drift risk: when two sources define the same rule, one will evolve and the other will be forgotten. Document drift-risk assessment for each instance.

(see §5.3 — Audit Protocol for criteria on complexity inflation and dependency expansion detection)

### Step 6 — Analyze Responsibility Allocation

Verify that every component, module, or entity owns one coherent responsibility. Detect:
- Mixed concerns — a component handling multiple unrelated responsibilities
- Responsibility leakage — a component reaching beyond its boundary
- Ownership collapse — too many responsibilities concentrated in one entity
- Boundary violations — a component crossing into another's domain

(see §5.3 — Audit Protocol for criteria on boundary preservation and ownership violation identification)

### Step 7 — Analyze Dependencies

Reconstruct dependency graphs for the artifact and its ecosystem. Detect:
- Circular dependencies (A depends on B, B depends on A)
- Reverse dependencies (a lower layer depends on a higher layer)
- Hidden or unnecessary coupling
- Implicit architectural relationships not documented anywhere
- Excessive dependency depth

Document each issue as a finding with the dependency chain and the risk it creates.

### Step 8 — Evaluate Evolution

Determine the artifact's ability to survive future change:
- Can it be extended without breaking existing consumers?
- Can it be replaced without rewriting dependents?
- Can it be frozen without losing adaptability?
- Can it survive the next roadmap phases?
- Can it scale without architectural drift?

Document limitations as findings even if they do not block current acceptance.

### Step 9 — Verify Terminology

Search for terminology issues:
- Different names for the same concept
- Same name for different concepts
- Similar-but-distinct concepts with confusingly similar names
- Terms used inconsistently across the artifact and ecosystem

Terminology debt is future technical debt. Misnamed concepts survive in documentation and conversation long after the original meaning drifts.

### Step 10 — Compare Against Foundational Principles

Compare the artifact against the governing philosophy and foundational principles. Detect philosophical drift even when implementation appears technically correct. Questions to ask:
- Does this violate a foundational principle (even if it works)?
- Does this create a precedent that undermines the governing philosophy?
- Is this technically correct but architecturally inconsistent?

Technically correct work that drifts from foundational principles creates hidden governance debt.

### Step 11 — Operational Risk Review

Analyze the artifact's operational impact:
- Maintainability — can future agents understand and modify this?
- Testability — can correctness be verified?
- Auditability — can decisions and changes be traced?
- Observability — is operational state visible?
- Failure modes — what happens when this breaks?
- Debuggability — can failures be diagnosed?
- Long-term maintenance burden — what is the ongoing cost?

Document each risk with severity assessment.

### Step 12 — Future Technical Debt Review

Determine whether the artifact introduces future rigidity, unnecessary abstraction, hidden complexity, or governance expansion — even if it is technically correct today. Look for:
- Hardcoded lists where extension is foreseeable
- Over-engineering beyond current known requirements
- Hidden coupling that will become visible only during future changes
- Process or documentation that will need ongoing maintenance without proportional value

Not all technical debt is avoidable. All technical debt must be deliberate and documented.

### Cross-Reference: Audit Protocol (§5.3)

Steps 3, 4, 5, and 6 overlap with audit criteria defined in §5.3 (Audit Protocol). These two sections serve complementary roles:

- **§5.3 defines WHAT to validate**: doctrinal adherence, architectural drift, complexity inflation, ownership violations, boundary preservation, observability degradation, dependency expansion.
- **§5.5 defines HOW to systematically reach conclusions**: the 12-step methodology that surfaces findings.

When executing Steps 3–6, consult §5.3 for the specific validation criteria. Do not duplicate §5.3 content here.

The methodology described in this section is applied at each lifecycle gate defined in the Review Gates section of the SDD Cycle Governance document. This section defines the methodology; Review Gates define when it runs.

### Anti-Loop Safeguards

Review loops must be bounded. After 3 consecutive FAILs on the same work product, the review MUST escalate per the §5.3 escalation path. The escalation record MUST document: the recipient of the escalated decision, the complete iteration history (findings from each iteration), and the specific decision requiring higher authority.

If a work product eventually passes (e.g., FAIL → WARN → PASS), no escalation occurs. The iteration count is recorded for audit.

The 3-FAIL counter resets when the artifact substantially changes scope or when a higher authority overrides the escalation.

### Extension Mechanism

New review steps may be added when there is evidence of recurring gaps not covered by the existing 12 steps. The process:
1. Document the recurring gap with at least 3 independent instances
2. Propose the new step as part of the universal sequence (not as a subset or alternative)
3. Follow the Discovery Protocol (§6) for approval
4. Integrate into the sequence preserving the existing step order

Steps cannot be removed. Subsets cannot be created. Governance minimalism (A6) applies — one methodology.

---

# 6. DISCOVERY PROTOCOL

*Built upon: B6 (Structured Work Cycle), A2 (Architecture Before Implementation), A8 (Evidence Before Complexity)*

---

## 6.1 Purpose

When a project identifies a need for structural change (new governance, new architectural domain, new process), the change should follow a structured discovery protocol rather than ad-hoc implementation.

This protocol is an application of the PDCA-aligned work cycle (B6) to governance and architectural changes.

---

## 6.2 Protocol Phases

```
Discover   →  Identify the need and its scope
              (Intent)

Assess     →  Analyze impact, affected components, risk
              (Design)

Authorize  →  Obtain approval to proceed
              (Design → Execution gate)

Execute    →  Implement the change
              (Execution)

Validate   →  Verify the change meets its objectives
              (Verification)

Close      →  Record outcome and update authority
              (Adaptation)
```

---

## 6.3 Sequencing Rules

- Discovery and assessment are analysis work — they do not modify the system
- Authorization must precede execution
- Execution without authorization creates ungoverned change
- Validation must precede closure
- Closure records the outcome and feeds the next cycle

If a lifecycle governance for changes does not yet exist, define it before implementing changes that would be governed by it. Do not invert dependencies: the governance should exist before the work it governs.

---

# 7. OPTIONAL DOCTRINES

The following doctrines are optional. Projects adopt them based on context, scale, and need.

---

## C1. AUTHORITY HIERARCHY

*Applies to: team-based projects with multiple roles or external reviewers*

### Principle

Knowledge flows upward. Authority flows downward.

No entity may approve the consequences of its own actions.

- Those who produce work do not approve it
- Those who approve work do not produce it
- When authority is unclear: escalate
- When approval is unclear: escalate
- Every role receives only the minimum authority necessary

### When to adopt

- Multi-person teams with role separation
- Projects requiring external audit
- Projects with compliance requirements

### When to skip

- Solo work
- Informal collaborations without formal approval needs

---

## C2. DOCUMENT CLASSIFICATION

*Applies to: projects with sufficient document volume that types become ambiguous (>15-20 documents)*

### Principle

Documents declare their type to enable clear identification and authority tracking.

Recommended types (aligned with the work cycle, B6):

| Type | Purpose |
|---|---|
| Principles | Immutable foundational authority |
| Architecture | Structural decisions, boundaries, contracts |
| Execution | Procedures, plans, implementation records |
| Evidence | Audits, validation, closure records |

### When to adopt

- Large projects with many artifacts
- Multi-team coordination
- Audit or compliance requirements

### When to skip

- Small projects with few documents
- Solo work where types are implicitly understood

---

## C3. DISCOVERY PROTOCOL (as Governance)

*Applies to: projects with evolving governance, regulatory compliance, or multi-stakeholder changes*

### Principle

Structural changes follow the Discovery Protocol (§6) rather than ad-hoc modification.

### When to adopt

- Projects with formal governance that evolves over time
- Projects with regulatory or compliance change requirements
- Projects where multiple stakeholders must approve changes

### When to skip

- Projects with stable, simple governance
- Solo projects where changes are self-approved

---

## C4. MINIMAL EFFECTIVE CONTEXT

*Applies to: AI-orchestrated projects, large-team coordination, complex handoff scenarios*

### Principle

Receivers (agents, team members, tools) should receive the minimum context required to perform their function.

More context is not inherently better. Irrelevant context increases noise, drift, and ambiguity.

Context should be:
- progressive (loaded as needed, not all at once)
- bounded (limited to what is operationally applicable)
- traceable (source is identifiable)

The most recent validated representation has priority over raw history.

### When to adopt

- AI-orchestrated projects with context windows
- Large teams with role-based information needs
- Projects with complex handoff scenarios

### When to skip

- Solo work
- Small projects with no context-management overhead

---

## C5. OPERATIONAL ENTROPY CONTROL

*Applies to: long-lived projects, maintained systems, ongoing operations*

### Principle

Small operational mutations accumulate gradually into architectural instability.

Entropy accumulation is gradual before becoming irreversible.

Entropy emerges through:
- tooling accumulation
- hidden operational mutation
- dependency layering
- silent drift
- unnecessary complexity layering

Freeze discipline, stabilization, audit loops, and complexity containment exist to slow entropy growth before instability becomes systemic.

The objective is NOT zero complexity. The objective is:
- controlled complexity
- observable complexity
- auditable complexity
- reversible complexity
- justified complexity

Complexity that cannot justify its operational cost becomes architectural liability.

### When to adopt

- Long-lived projects
- Maintained systems
- Ongoing operations

### When to skip

- Short-lived projects
- One-time deliverables
- Disposable experiments

---

# 8. ADAPTATION GUIDE

This section tells new projects how to adapt the Portable Operating System to their context.

---

## 8.1 Universal Adoption (No Adaptation Needed)

The following apply without modification to all project types:
- All Mandatory Core principles (A1-A8)
- B5 (Operational Progress Over Conceptual Expansion)
- B6 (Structured Work Cycle)
- Values hierarchy
- Forbidden patterns

---

## 8.2 Software Projects

Full adoption. No adaptation required.

All Optional doctrines (C1-C5) are likely applicable.

---

## 8.3 AI Projects

Full adoption. No adaptation required.

The principles are especially relevant for AI:
- A1 (Deterministic-First) is critical for reproducible AI behavior
- B3 (Knowledge Persistence) is critical for surviving model replacement
- C4 (Minimal Effective Context) is critical for context management

---

## 8.4 Research Projects

Adopt with these reinterpretations:

| Principle | Standard | Research Adaptation |
|---|---|---|
| A1 (Deterministic-First) | Identical inputs → identical outputs | Reproducibility within stated confidence intervals. Methodology must produce reproducible results. |
| B1 (Freeze Discipline) | Freeze architecture | Freeze methodology, not the research question. Exploration continues within frozen method. |
| B4 (Stabilization Progression) | Infrastructure stabilizes over time | Methodology stabilizes before data collection. Data collection stabilizes before analysis. |
| B5 (Operational Progress) | Execution over conceptualization | Empirical evidence over theoretical correctness. Still prefer bounded experimentation over endless speculation. |

C4 (Minimal Effective Context) is less relevant for solo research. C2 (Document Classification) is useful for research publications and lab records.

---

## 8.5 Engineering Projects

Full adoption. No adaptation required.

Engineering is the natural home for these principles:
- B1 (Freeze Discipline) maps to design freeze
- B4 (Stabilization Progression) maps to commissioning
- B2 (Integration Hostility) maps to supplier/contractor management
- C1 (Authority Hierarchy) maps to project management structure

---

## 8.6 Business Projects

Adopt with these reinterpretations:

| Principle | Standard | Business Adaptation |
|---|---|---|
| A1 (Deterministic-First) | Identical inputs → identical outputs | Process reproducibility for operations. Strategy is inherently uncertain — A1 applies to operations, not strategy. |
| B2 (Integration Hostility) | Integration is liability | Partnership diligence. Partnerships carry operational cost. Softened from "hostility" to "diligence." |
| C4 (Minimal Effective Context) | Minimum context for receivers | Less relevant. Business communication has different constraints. |

B5 (Operational Progress) maps to "ship and iterate." C1 (Authority Hierarchy) maps to organizational structure. C3 (Discovery Protocol) maps to change management.

---

## 8.7 Solo Work

- All Mandatory Core principles (A1-A8) apply
- B1-B6 apply if the work is non-trivial
- C1 (Authority Hierarchy) — skip (no multi-role approval needed)
- C2 (Document Classification) — skip for small projects
- C3 (Discovery Protocol) — skip for simple changes
- C4 (Minimal Effective Context) — skip (no context-management overhead)
- C5 (Operational Entropy Control) — adopt if the project is long-lived

---

## 8.8 Adaptation Rules

1. The Constitution cannot be adapted. It is adopted as-is or not at all.
2. The Operations Manual can be adapted per project, provided no Constitutional principle is violated.
3. Optional doctrines (C1-C5) are adopted or skipped based on project context.
4. Adaptations must be explicit — do not silently modify procedures.
5. If a project's context requires a procedure not covered here, add it to the project's own Operations Manual extension. Do not add it to this Manual unless it is universally applicable.

---

# 9. MAINTENANCE

This Manual is maintained through the Discovery Protocol (§6).

Changes to this Manual:
- must not violate the Constitution
- must follow the Discovery Protocol
- must be reviewed for duplication against existing content (A6)
- must be compressed before addition (does this increase operational surface unnecessarily?)

The Constitution's Governance Minimalism doctrine (A6) is the permanent constraint on this Manual's growth.

Warning threshold: if this Manual exceeds 700 lines, procedures are likely over-detailed or new procedures have been added that should have been resisted.

---

# 10. FINAL RULE

Most systems collapse operationally before they collapse technically.

Protect architectural clarity aggressively.

Operational simplicity is a long-term strategic asset.

Controlled evolution is sustainable evolution.

---

**This Operations Manual derives its authority from the Portable OS Constitution. It is adaptable per project. It does not override the Constitution.**
