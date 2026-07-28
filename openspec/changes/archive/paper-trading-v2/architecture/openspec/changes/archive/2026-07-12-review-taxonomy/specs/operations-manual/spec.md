# Delta for Operations Manual — §5.5 Review Methodology

> **Authority**: A3 (Boundary Discipline), A6 (Governance Minimalism), A8 (Evidence Before Complexity)
> **Target**: PORTABLE-OS-OPERATIONS-MANUAL.md §5.5 (new section after §5.4)

## ADDED Requirements

### Requirement: Review Definition

§5.5 SHALL define "review" as a single universal 12-step methodology applied to any artifact. Definition MUST be generic — not SDD-specific or project-specific.

#### Scenario: Generic definition

- GIVEN an agent consults §5.5 to understand what a review is
- THEN the definition states a single 12-step methodology executed in order
- AND contains no type-specific or project-specific references

---

### Requirement: Universal Sequence (No Subsets)

§5.5 MUST define exactly one sequence. All 12 steps MUST execute in order for every review. If a step is not applicable to the artifact under review, the reviewer MUST conclude it with "Not applicable" and proceed to the next step. Subsets or alternative review flows MUST NOT be created.

#### Scenario: Inapplicable step for a simple artifact

- GIVEN an artifact with no architectural dependencies (e.g., a single document edit)
- WHEN the Dependency Analysis step executes
- THEN the reviewer concludes "Not applicable" and moves to the next step

#### Scenario: Full sequence always

- GIVEN any review on any artifact
- WHEN the methodology is applied
- THEN all 12 steps are executed in order, each producing a documented finding or "Not applicable"

---

### Requirement: Four Logical Phases

§5.5 MUST group the 12 steps into 4 phases for readability, training, and automation:

| Phase | Steps | Focus |
|---|---|---|
| Context Reconstruction | 1–2 | Authority identification, architectural context reconstruction |
| Consistency Analysis | 3–5 | Contradiction detection, missing information, duplication detection |
| Architectural Integrity | 6–8 | Responsibility allocation, dependency analysis, evolution evaluation |
| Quality Validation | 9–12 | Terminology consistency, principles compliance, operational risk, future technical debt |

Phases MUST NOT change the sequence or create alternative entry points. They are presentational grouping only.

#### Scenario: Phase grouping is cosmetic

- GIVEN an agent studies the phases
- WHEN the agent attempts to skip a phase
- THEN the methodology prevents skipping — all 12 steps execute regardless of phase grouping

---

### Requirement: Step 1 — Identify Authority

The reviewer MUST identify the artifact's authority level: what it is allowed to define, what it must inherit, and what it cannot override. Every review begins with authority before content.

#### Scenario: Proposal review

- GIVEN a proposal is under review
- WHEN Step 1 executes
- THEN the reviewer identifies which Constitution principles apply, what the proposal can/cannot override, and what it must inherit from higher-authority documents

---

### Requirement: Step 2 — Reconstruct Context

The reviewer MUST reconstruct the architectural context around the artifact. Review the artifact against the complete ecosystem (Constitution, Operations Manual, existing contracts, previous decisions, frozen artifacts), not against a single document.

#### Scenario: Spec review with cross-document context

- GIVEN a spec under review
- WHEN Step 2 executes
- THEN the reviewer loads: Constitution, Operations Manual, prior proposal, existing specs in the same domain, frozen contracts

---

### Requirement: Step 3 — Detect Contradictions

The reviewer MUST search for contradictions across all authoritative artifacts. Examples: conflicting ownership, responsibilities, lifecycle definitions, authority, terminology, contracts, boundaries.

#### Scenario: Contradiction found

- GIVEN a design creates a responsibility that contradicts an existing contract
- WHEN Step 3 executes
- THEN the contradiction is documented as a FAIL finding

---

### Requirement: Step 4 — Detect Missing Information

The reviewer MUST ask: Who owns this? Who initializes/destroys/validates/persists/approves it? Who is responsible if it fails? Missing information is often more critical than incorrect statements.

#### Scenario: Missing ownership

- GIVEN a task defines an action but not its owner
- WHEN Step 4 executes
- THEN the missing ownership is documented as a finding

---

### Requirement: Step 5 — Detect Duplication

The reviewer MUST search for duplicated concepts, ownership, responsibilities, doctrine, lifecycle definitions, contracts, or documentation. Determine whether duplication creates future drift risk.

#### Scenario: Drift-risk duplication

- GIVEN two documents define the same lifecycle rule with slightly different wording
- WHEN Step 5 executes
- THEN the duplication is documented with drift-risk assessment

---

### Requirement: Step 6 — Analyze Responsibility Allocation

The reviewer MUST verify every component owns one coherent responsibility. Detect mixed concerns, responsibility leakage, ownership collapse, boundary violations.

#### Scenario: Mixed concern detected

- GIVEN a component handles both validation AND persistence without separation
- WHEN Step 6 executes
- THEN the mixed concern is documented

---

### Requirement: Step 7 — Analyze Dependencies

The reviewer MUST reconstruct dependency graphs and detect: cycles, reverse dependencies, hidden/unnecessary coupling, excessive depth, implicit architectural relationships.

#### Scenario: Circular dependency

- GIVEN two components reference each other
- WHEN Step 7 executes
- THEN the cycle is documented as a finding

---

### Requirement: Step 8 — Evaluate Evolution

The reviewer MUST determine: Can this be extended? Replaced? Frozen? Can it survive future roadmap phases? Can it scale without architectural drift?

#### Scenario: Extension prevented by current design

- GIVEN a design cannot accommodate a known future requirement
- WHEN Step 8 executes
- THEN the limitation is documented

---

### Requirement: Step 9 — Verify Terminology

The reviewer MUST search for inconsistent names, inconsistent concepts, similar concepts with different wording, different concepts sharing the same name. Terminology debt is future technical debt.

#### Scenario: Naming conflict

- GIVEN two different concepts share the same term
- WHEN Step 9 executes
- THEN the naming conflict is documented

---

### Requirement: Step 10 — Compare Against Foundational Principles

The reviewer MUST compare the artifact against the Constitution, philosophy, deterministic-first principles, boundary discipline, fail-fast, governance principles. Detect philosophical drift even when implementation appears technically correct.

#### Scenario: Technically correct but philosophically inconsistent

- GIVEN an implementation works but violates a Constitution principle
- WHEN Step 10 executes
- THEN the philosophical drift is documented

---

### Requirement: Step 11 — Operational Risk Review

The reviewer MUST analyze: maintainability, testability, auditability, observability, operational complexity, failure modes, debuggability, long-term maintenance burden.

#### Scenario: High operational complexity

- GIVEN a design requires manual recovery on failure
- WHEN Step 11 executes
- THEN the operational risk is documented

---

### Requirement: Step 12 — Future Technical Debt Review

The reviewer MUST determine whether the artifact introduces future rigidity, unnecessary abstraction, hidden complexity, future duplication, governance expansion, maintenance cost, or operational debt — even if technically correct today.

#### Scenario: Technically correct but rigid

- GIVEN a spec defines a hardcoded list where extension is foreseeable
- WHEN Step 12 executes
- THEN the future rigidity is documented

---

### Requirement: Cross-Reference Audit Protocol (§5.3)

§5.5 MUST NOT duplicate §5.3 (Audit Protocol). Steps 3–6 (Contradictions, Missing Info, Duplication, Responsibility) overlap with audit criteria. §5.5 MUST cross-reference §5.3 whenever audit-specific validation criteria are needed. §5.3 defines WHAT to validate; §5.5 defines HOW to systematically reach conclusions.

#### Scenario: Reviewer needs audit criteria

- GIVEN Step 3 (Contradictions) requires specific audit criteria
- WHEN the reviewer needs to know WHAT counts as a contradiction
- THEN §5.5 cross-references §5.3 for the criteria definition

---

### Requirement: Anti-Loop Safeguards

Review loops MUST be bounded. After 3 consecutive FAILs on the same work product, the review MUST escalate per §5.3 escalation path. Recipient, information, and decision authority MUST be documented.

#### Scenario: Repeated failure

- GIVEN 3 consecutive FAILs on the same work product
- WHEN a 4th iteration also produces FAIL
- THEN the reviewer MUST escalate per the defined path

#### Scenario: Eventual pass

- GIVEN FAIL → WARN → PASS across iterations
- THEN iteration count is recorded; no escalation occurs

---

### Requirement: Extension Mechanism

New review steps require: (1) evidence of recurring gaps not covered by existing 12 steps, (2) integration into the sequence without creating subsets, (3) approval via Discovery Protocol (§6).

#### Scenario: New step proposal

- GIVEN a project identifies a recurring gap not covered by the 12 steps
- WHEN a new step is proposed
- THEN it follows §6 Discovery Protocol for approval and must integrate into the universal sequence
