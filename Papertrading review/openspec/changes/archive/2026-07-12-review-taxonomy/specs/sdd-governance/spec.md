# Delta for SDD Cycle Governance — Review Gates

> **Authority**: A2 (Architecture Before Implementation), A4 (Fail-Fast), A7 (Optional Doctrine), A8 (Evidence Before Complexity), B6 (Structured Work Cycle)
> **Target**: SDD-CYCLE-GOVERNANCE.md (new section — "Review Gates")

## ADDED Requirements

### Requirement: Gate Authority Level

Review gates MUST be defined as **SHOULD** at Portable OS level. A project that explicitly adopts review gates (by referencing them in its own SDD Cycle Governance) MUST treat them as **MUST**. This mirrors the Optional Doctrine pattern (Constitution A7).

#### Scenario: Project adopts gates

- GIVEN a project explicitly references the Review Gates section in its SDD Cycle Governance
- WHEN the project runs an SDD cycle
- THEN all adopted gates are MUST for that project

#### Scenario: Project does not adopt gates

- GIVEN a project does not reference the Review Gates section
- WHEN the project runs an SDD cycle
- THEN gates are SHOULD — the project may apply them or not without violating governance

---

### Requirement: Mandatory Review Gates

The system MUST define 7 gates, one for each SDD phase transition. Each gate applies the universal 12-step Review Methodology (Operations Manual §5.5) to that phase's artifact. The gated phase MUST NOT begin until the gate produces at least WARN.

| Gate | Artifact Reviewed | Gates Transition To |
|---|---|---|
| G0 | Exploration | → Proposal |
| G1 | Proposal | → Spec |
| G2 | Spec | → Design |
| G3 | Design | → Tasks |
| G4 | Tasks | → Apply |
| G5 | Verify-report | → Archive |
| G6 | Archive artifacts | → Close |

#### Scenario: All gates pass

- GIVEN an SDD cycle executes from Exploration through Close
- WHEN each gate produces PASS on its respective artifact
- THEN each phase transition proceeds without blocking

#### Scenario: Gate skipped

- GIVEN a project has adopted gates as MUST
- WHEN a phase transition attempts without the preceding gate
- THEN the transition MUST be blocked

---

### Requirement: Verdict Semantics

Each gate produces a traffic-light verdict using the methodology (Operations Manual §5.5):

| Verdict | Meaning | Effect |
|---|---|---|
| PASS | No CRITICAL findings, methodology complete | Phase transition permitted |
| WARN | Non-blocking concerns documented (SHOULD fix before next gate) | Phase transition permitted; caveats recorded for next gate |
| FAIL | CRITICAL finding(s) unresolved | Phase transition BLOCKED; artifact must be revised and re-reviewed |

#### Scenario: PASS gate

- GIVEN G0 (Exploration Review) produces PASS
- THEN Proposal phase MAY begin

#### Scenario: FAIL gate

- GIVEN G5 (Verify Review) produces FAIL
- THEN Archive phase MUST NOT begin until FAIL resolves and subsequent review produces at least WARN

#### Scenario: WARN with caveats

- GIVEN G2 (Spec Review) produces WARN with caveats
- THEN Design phase MAY begin
- AND caveats are recorded for G3 (Design Review) to verify

---

### Requirement: Gate-Specific PASS/FAIL Conditions

Each gate's verdict derives from applying the universal methodology to its specific artifact. At minimum:

| Gate | Typical CRITICAL findings (FAIL triggers) |
|---|---|
| G0 | Exploration scope misaligned with radar; missing alternatives; no clear recommendation |
| G1 | Proposal intent unclear; scope boundaries missing; no rollback plan; authority not identified |
| G2 | Requirements not using RFC 2119; scenarios missing edge cases; spec contradicts higher authority |
| G3 | Design introduces architectural drift; missing responsibility ownership; dependencies unresolved |
| G4 | Tasks not traceable to spec/design; acceptance criteria missing; effort estimates absent |
| G5 | Verify-report missing evidence; CRITICAL findings unresolved; apply-progress inconsistent |
| G6 | Archive artifacts incomplete; change record missing; cross-document consistency violated |

#### Scenario: G1 — No rollback plan

- GIVEN a proposal without a rollback plan
- WHEN Step 4 (Missing Information) detects this during the methodology
- THEN G1 produces FAIL until rollback plan is added

#### Scenario: G5 — Missing evidence

- GIVEN a verify-report claims passing tests without evidence
- WHEN Step 3 (Contradictions) detects claim-vs-evidence mismatch
- THEN G5 produces FAIL

---

### Requirement: Anti-Loop Safeguards

Gate review loops are bounded by Operations Manual §5.5 anti-loop rules (3 consecutive FAILs → escalation). Escalation path MUST document: recipient, iteration history, and the decision requiring higher authority.

#### Scenario: Escalation after max iterations

- GIVEN G2 produces FAIL for 3 consecutive iterations on the same spec
- WHEN the §5.5 threshold is reached
- THEN review escalates per §5.5 escalation path with full iteration history

---

### Requirement: Cross-Reference to Operations Manual

Review Gates MUST NOT restate the methodology (12 steps, verdict format, authority boundaries, anti-loop mechanics). This section defines ONLY lifecycle-specific rules: which artifact to review at which transition, and typical FAIL triggers per gate. All methodology mechanics SHALL be obtained from Operations Manual §5.5.

#### Scenario: Gate needs methodology details

- GIVEN an agent reads Review Gates and needs to understand the 12 steps
- THEN Review Gates cross-references §5.5

#### Scenario: Bidirectional references

- GIVEN both §5.5 and Review Gates exist
- WHEN an agent reads either section
- THEN both sections contain explicit cross-references to each other
