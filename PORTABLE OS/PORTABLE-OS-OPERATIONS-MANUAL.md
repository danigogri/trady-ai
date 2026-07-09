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
