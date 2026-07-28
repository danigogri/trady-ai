# Delta for SDD-CYCLE-GOVERNANCE.md

**Authority**: A3 (Boundary Discipline), A6 (Governance Minimalism), A8 (Evidence Before Complexity)

> No existing `openspec/specs/sdd-cycle-governance/` exists. These are ADDED requirements defining what SDD-CYCLE-GOVERNANCE.md MUST contain after this change.

## ADDED Requirements

### Requirement: PR Creation Timing in §3

§3 step 5 (Archive) MUST explicitly state: create PR after squash, before push. Current text says "Merge PR = freeze" but does not state when the PR is created. The text MUST clarify PR is NOT created at Apply phase.

*Traces to: A8*

#### Scenario: Agent knows PR timing from Archive step

- GIVEN an agent executes Archive phase
- WHEN reading §3 step 5
- THEN the step MUST state: create PR after squash, before push

---

### Requirement: Merge Strategy in §3

§3 step 5 MUST explicitly define merge strategy for SDD changes as `squash-and-merge`. Current text mentions WIP squash but does not name the PR merge strategy. Must be consistent with GIT-WORKFLUX §4.

*Traces to: A3*

#### Scenario: Agent knows merge strategy for SDD PR

- GIVEN an agent created a PR for an SDD change
- WHEN reading §3 for merge instructions
- THEN §3 MUST state merge strategy is `squash-and-merge`

---

### Requirement: GIT-WORKFLUX Cross-Ref in §3

§3 MUST include a cross-reference to GIT-WORKFLUX.md §3 for branch naming (`sdd/<change-name>`) and general git operations.

*Traces to: A6*

#### Scenario: Agent needs branch naming from §3

- GIVEN an agent reads §3 and needs to create a branch
- WHEN looking for branch naming conventions
- THEN §3 MUST link to GIT-WORKFLUX §3 for branch patterns

---

### Requirement: WIP Type Reference in §4

§4 (Reglas del Commit Local WIP) SHOULD cross-reference GIT-WORKFLUX §2 confirming `wip:` is recognized as a valid commit type in the parental convention.

*Traces to: A6. Strength: SHOULD*

#### Scenario: Agent reads §4 and sees parental link

- GIVEN an agent reads §4 about WIP rules
- WHEN checking if `wip:` is a recognized type
- THEN §4 SHOULD note that GIT-WORKFLUX §2 lists `wip:` as valid

---

### Requirement: Verify-Report Cross-Ref in §6

§6 (Verify-Report Contract) MUST cross-reference GIT-WORKFLUX §5, indicating verify-report is the evidence artifact connecting SDD cycle to git workflow.

*Traces to: A8*

#### Scenario: Agent reads §6 and sees git-workflux link

- GIVEN an agent reads §6 for verify-report requirements
- WHEN looking for how verify-report connects to git workflow
- THEN §6 MUST link to GIT-WORKFLUX §5

---

### Requirement: Bidirectional Cross-References

All cross-refs from SDD-CYCLE-GOVERNANCE → GIT-WORKFLUX MUST have matching refs from GIT-WORKFLUX → SDD-CYCLE-GOVERNANCE. No unidirectional references permitted.

*Traces to: A3, A8*

#### Scenario: No orphan references

- GIVEN final state of both documents
- WHEN enumerating cross-refs from SDD-CYCLE-GOVERNANCE → GIT-WORKFLUX
- THEN each MUST have a corresponding back-reference
- AND zero orphan (unidirectional) references MUST exist
