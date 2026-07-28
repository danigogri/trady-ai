# Delta for GIT-WORKFLUX.md

**Authority**: A3 (Boundary Discipline), A6 (Governance Minimalism), A8 (Evidence Before Complexity)

> No existing `openspec/specs/git-workflux/` exists. These are ADDED requirements defining what GIT-WORKFLUX.md MUST contain after this change.

## ADDED Requirements

### Requirement: WIP Commit Type in §2

§2 (Commit Convention) MUST list `wip:` as a valid commit type with a cross-reference to SDD-CYCLE-GOVERNANCE.md §4 for WIP semantics. §2 MUST NOT redefine WIP rules (amend, squash, push prohibition) — those belong to SDD-CYCLE-GOVERNANCE §4.

*Traces to: A3, A6*

#### Scenario: Agent finds wip: in commit types table

- GIVEN an agent reads §2
- WHEN scanning valid commit types
- THEN the table MUST contain a `wip:` row with a note linking to SDD-CYCLE-GOVERNANCE.md §4

---

### Requirement: SDD Branch Naming in §3

§3 (Branch Strategy) MUST define the `sdd/<change-name>` pattern alongside existing patterns (`fix/BL-XXX`, `feat/<nombre-fase>`). `<change-name>` MUST match the directory name in `openspec/changes/<change-name>/`.

*Traces to: A3*

#### Scenario: Agent creates branch for SDD change

- GIVEN an agent creates a branch for change `cross-reference-alignment`
- WHEN consulting §3 for naming
- THEN `sdd/<change-name>` MUST be documented as a valid pattern

---

### Requirement: PR Timing Note in §3 Flow

§3 flow section MUST include a note: for SDD changes, PR is created at Archive phase (SDD-CYCLE-GOVERNANCE §3 step 5), after squashing WIP commits. The note MUST link to SDD-CYCLE-GOVERNANCE §3.

*Traces to: A8*

#### Scenario: Agent reads §3 flow for PR timing

- GIVEN an agent reads the §3 flow diagram
- WHEN looking for PR creation timing on SDD changes
- THEN a note MUST state PR creation happens at Archive, after squash, with a link to SDD-CYCLE-GOVERNANCE §3

---

### Requirement: Verify-Report Cross-Ref in §5

§5 (Relación con SDD) MUST cross-reference SDD-CYCLE-GOVERNANCE §6 for the verify-report contract.

*Traces to: A8*

#### Scenario: Agent needs verify-report format from §5

- GIVEN an agent is in verify phase
- WHEN reading §5
- THEN §5 MUST link to SDD-CYCLE-GOVERNANCE §6 for verify-report requirements

---

### Requirement: SDD-CYCLE-GOVERNANCE in §8 References

§8 (Referencias) MUST list SDD-CYCLE-GOVERNANCE.md as a reference.

*Traces to: A6*

#### Scenario: §8 reference list is complete

- GIVEN an agent reads §8
- WHEN scanning references
- THEN SDD-CYCLE-GOVERNANCE.md MUST appear

---

### Requirement: Bidirectional Cross-References

All cross-refs from GIT-WORKFLUX → SDD-CYCLE-GOVERNANCE MUST have matching refs from SDD-CYCLE-GOVERNANCE → GIT-WORKFLUX. No unidirectional references permitted.

*Traces to: A3, A8*

#### Scenario: No orphan references

- GIVEN final state of both documents
- WHEN enumerating cross-refs from GIT-WORKFLUX → SDD-CYCLE-GOVERNANCE
- THEN each MUST have a corresponding back-reference
- AND zero orphan (unidirectional) references MUST exist
