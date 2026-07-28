# Exploration: GIT-WORKFLUX / SDD-CYCLE-GOVERNANCE Audit + Review Framework Evaluation

**Date**: 2026-07-12
**Mode**: openspec
**Status**: Exploration (not binding)

---

## Exploration A — Audit: GIT-WORKFLUX vs SDD-CYCLE-GOVERNANCE

### Documents Read

| Document | Lines | Authority Level | Key Content |
|----------|-------|-----------------|-------------|
| PORTABLE-OS-CONSTITUTION.md | 493 | Principles (immutable) | A1-A8, B1-B6, values hierarchy, forbidden patterns |
| PORTABLE-OS-OPERATIONS-MANUAL.md | 624 | Architecture+Execution (adaptable) | Integration doctrine, dependency governance, stabilization, audit protocol, discovery protocol, optional doctrines C1-C5 |
| SDD-CYCLE-GOVERNANCE.md | 129 | Architecture (binding for SDD) | SDD cycle phases, WIP commit rules, verify-report contract, archive rules |
| GIT-WORKFLUX.md | 156 | Architecture+Execution (adaptable) | Commit types, branch strategy, PR rules, merge strategy, security |
| BACKLOG-PROTOCOL.md | 318 | Execution | Issue tracking, scope discipline, finding registration |

### What SDD-CYCLE-GOVERNANCE Mandates

**Phases**: Apply → Verify #1 → Triage → Verify #2 → Archive

**Core invariant**: Commit pushed to GitHub = verified state. Never push unverified code.

**Rules**:
- WIP commits are local-only, prefix `wip:`, amendable freely, squashed at archive
- Verify-report MUST include: hash, full tool output (mypy, ruff, pytest+coverage), findings classified as CRITICAL/WARNING/SUGGESTION, apply-progress consistency, PASS/FAIL verdict
- GitHub docs (PR bodies, assessment reports) MUST be archived locally before squash (Constitution B2)
- Exceptions: trivial changes (≤1 file annotation/import), docs-only changes

**Relationship declared**: "Extension of GIT-WORKFLUX.md. GIT-WORKFLUX.md is the parental document."

### What GIT-WORKFLUX Mandates

**Commit types**: `feat`, `fix`, `deuda`, `docs`, `spec`

**Branch strategy**: `main` + `fix/BL-XXX` + `feat/<name>`

**PR rules**:
- Author does NOT self-merge (except documented urgency)
- Minimum 1 approval before merge
- `Squash and merge` for fix branches
- `Merge commit` for complete phases

**Other rules**:
- No direct commits to main — everything starts from a branch
- Branches deleted post-merge
- Main always stable and deployable
- Short branches: one change per branch
- Security: .gitignore, noreply email, no secrets

### Specific Gaps, Overlaps, and Conflicts Found

#### CONFLICT 1: `wip:` commit type is invisible to GIT-WORKFLUX

**Location**: SDD-CYCLE-GOVERNANCE §4 vs GIT-WORKFLUX §2

SDD-CYCLE-GOVERNANCE introduces `wip:` as a commit prefix. GIT-WORKFLUX §2 lists exactly 5 valid types: `feat`, `fix`, `deuda`, `docs`, `spec`. The `wip:` type does NOT appear.

**Practical consequence**: An agent following ONLY GIT-WORKFLUX would consider `wip:` commits invalid. An agent following ONLY SDD-CYCLE-GOVERNANCE would not know the final commit types to use.

**Fix needed**: GIT-WORKFLUX §2 must add `wip` to valid types with a note that it is local-only and never pushed (cross-referencing SDD-CYCLE-GOVERNANCE §4).

#### CONFLICT 2: PR timing is ambiguous

**Location**: GIT-WORKFLUX §3 (flow diagram) vs SDD-CYCLE-GOVERNANCE §3

GIT-WORKFLUX §3 shows this flow:
```
branch → commit → push → gh pr create → review → merge
```

SDD-CYCLE-GOVERNANCE §3 says PR merge happens at Archive (step 5), AFTER squash. The WIP commits are never pushed.

**The gap**: When is the PR CREATED for an SDD change? GIT-WORKFLUX implies PR is created right after push. SDD-CYCLE-GOVERNANCE implies push happens at archive. But the PR needs to exist BEFORE merge for the approval rule to work.

**Practical consequence**: Agents are left guessing whether to:
(a) Create PR after the final squash+push (at archive time), or
(b) Create PR earlier and update it during the SDD cycle

Neither document says explicitly.

**Fix needed**: SDD-CYCLE-GOVERNANCE should specify when the PR is created relative to the apply→verify→archive flow. Most logical: PR is created at archive time, after squash and before merge.

#### GAP 1: Merge strategy for SDD changes is undefined

**Location**: GIT-WORKFLUX §4 vs SDD-CYCLE-GOVERNANCE §3

GIT-WORKFLUX §4 defines:
- `Squash and merge` for fix branches
- `Merge commit` for complete phases

SDD-CYCLE-GOVERNANCE §3 step 5 says "Squash commits WIP into ONE clean commit" and "Merge PR = freeze." But it doesn't say which merge strategy applies.

**Question**: Is an SDD change a "fix" (squash) or a "phase" (merge commit)? SDD-CYCLE-GOVERNANCE already squashes WIP into one commit before merge, so the merge strategy is somewhat moot — but it should be stated explicitly.

#### GAP 2: Branch naming for SDD changes

**Location**: GIT-WORKFLUX §3

Branch patterns defined: `fix/BL-XXX` and `feat/<phase-name>`.

SDD changes are neither fixes nor roadmap phases. They have names like `polymarket-integration`. Which pattern applies? `feat/<change-name>`? There's no explicit mapping.

**Fix needed**: GIT-WORKFLUX §3 should add `feat/<change-name>` or `change/<change-name>` for SDD changes, or SDD-CYCLE-GOVERNANCE should specify which branch pattern to use.

#### GAP 3: GIT-WORKFLUX does not reference SDD-CYCLE-GOVERNANCE

**Location**: GIT-WORKFLUX §8 (References)

SDD-CYCLE-GOVERNANCE explicitly declares GIT-WORKFLUX as parental (§1 Nota de jerarquía, §8). But GIT-WORKFLUX does NOT mention SDD-CYCLE-GOVERNANCE anywhere — not in §5 (Relación con SDD), not in §8 (Referencias).

**Practical consequence**: An agent reading GIT-WORKFLUX has no way to know SDD-CYCLE-GOVERNANCE exists. It references "SDD" generically in §5 but not the specific governance document.

**Fix needed**: GIT-WORKFLUX §5 and §8 must add cross-reference to SDD-CYCLE-GOVERNANCE.

#### GAP 4: Verify requirements are disconnected

**Location**: GIT-WORKFLUX §5 vs SDD-CYCLE-GOVERNANCE §6

GIT-WORKFLUX §5 mentions "métricas de verificación (tests, coverage, mypy)" in PR descriptions. SDD-CYCLE-GOVERNANCE §6 defines a strict verify-report contract with specific tool outputs.

**The gap**: These are not connected. GIT-WORKFLUX doesn't say "see SDD-CYCLE-GOVERNANCE for verify-report contract." SDD-CYCLE-GOVERNANCE doesn't say "this verify-report feeds the PR description required by GIT-WORKFLUX."

**Fix needed**: Cross-reference in both directions.

#### GAP 5: Neither document covers

| Missing topic | Why it matters |
|---------------|----------------|
| Hotfix procedure | What happens when main needs an urgent fix? Both docs assume normal flow. |
| Tag/release strategy | No mention of git tags, releases, or versioning. |
| Conflict resolution | What to do when branches diverge from main. |
| CI/CD expectations | No mention of automated checks, required status checks on PRs. |
| PR description template | GIT-WORKFLUX says `gh pr create --fill` but doesn't define what the PR body should contain for SDD changes vs fixes. |
| Rebase vs merge for keeping branches current | No guidance on how to keep branches up-to-date with main. |

#### OVERLAP 1: "Verification" concept

Both documents reference verification but with different rigor:
- GIT-WORKFLUX: "verificación" mentioned generically in §3 flow
- SDD-CYCLE-GOVERNANCE: Strict verify-report contract in §6

These should be one concept with one definition, not two parallel mentions.

#### OVERLAP 2: "Freeze" concept

Both reference freeze:
- GIT-WORKFLUX §5: "Merge a main = freeze del cambio"
- SDD-CYCLE-GOVERNANCE §3: "Merge PR = freeze del cambio"

Same concept, stated in both places. Not a conflict, but redundant. Should be defined once and cross-referenced.

### What Is Being "Left Out" in Practice

Based on document content analysis (not speculation), these rules are structurally invisible to agents following only one document:

1. **`wip:` commit type** — invisible if you only read GIT-WORKFLUX
2. **Verify-report contract** — invisible if you only read GIT-WORKFLUX
3. **PR creation timing for SDD changes** — undefined in both
4. **Branch naming for SDD changes** — undefined in both
5. **SDD-CYCLE-GOVERNANCE existence** — invisible if you only read GIT-WORKFLUX
6. **GitHub doc archival requirement** — invisible if you only read GIT-WORKFLUX
7. **Self-merge exception for urgency** — defined in GIT-WORKFLUX but SDD-CYCLE-GOVERNANCE's archive step doesn't acknowledge it

### Recommendation for Exploration A

**Both documents need updates.** Specifically:

1. **GIT-WORKFLUX** needs:
   - Add `wip` to valid commit types (§2) with "local-only, see SDD-CYCLE-GOVERNANCE"
   - Add cross-reference to SDD-CYCLE-GOVERNANCE in §5 and §8
   - Add branch naming for SDD changes (§3)
   - Connect verify requirements to SDD-CYCLE-GOVERNANCE verify-report contract
   - Add PR description requirements for SDD changes

2. **SDD-CYCLE-GOVERNANCE** needs:
   - Specify PR creation timing (when in the apply→verify→archive flow)
   - Specify merge strategy explicitly
   - Specify branch naming convention (or reference GIT-WORKFLUX's)
   - Acknowledge the self-merge exception from GIT-WORKFLUX

3. **Neither document** should be made to duplicate the other. They should cross-reference explicitly and define a clear boundary: GIT-WORKFLUX owns git conventions; SDD-CYCLE-GOVERNANCE owns SDD lifecycle mechanics.

---

## Exploration B — Review Framework Evaluation

### Analysis of Existing Review Concepts in Current Documents

The review/audit concept ALREADY EXISTS across multiple documents:

| Document | Review concept | Scope |
|----------|---------------|-------|
| Constitution A8 | "Cross-verification is mandatory" — audits must verify contracts, dependencies, boundaries, drift | Universal principle |
| Constitution §6 | "Forbidden patterns prohibited unless explicitly approved through architectural review" | Gate for exceptions |
| Operations Manual §3.3 | 6-type integration review (functional, architectural, installation, dependency, operational, boundary) | Integration-specific |
| Operations Manual §5.3 | Audit protocol: doctrinal adherence, drift, complexity, ownership, boundaries, observability, dependencies | General audit |
| SDD-CYCLE-GOVERNANCE §3,§6 | Verify phase with strict contract: hash, tool output, findings, verdict | SDD implementation verification |

**Key finding**: The system already has review concepts in THREE documents. There is no SINGLE place that defines:
- A taxonomy of review types
- When each review applies
- Who/what conducts each review
- Exit criteria for reviews
- How reviews relate to each other

### Challenging the Proposal

Before recommending structure, I need to challenge assumptions in the request:

#### Challenge 1: "We discovered we repeatedly use different kinds of review agents"

This is stated as observed from Trady.AI Phase 4. But Portable OS is meant to be GENERIC. The question is: is this a PATTERN that generalizes, or a Trady.AI-specific complexity?

**Assessment**: The Operations Manual §5.3 already defines a general audit protocol. The SDD-CYCLE-GOVERNANCE defines verify. The integration doctrine (§3.3) defines integration review. These are THREE review types already generalized. The proposal to add more types (Security, Performance, etc.) may be premature — Constitution A6 (Governance Minimalism) and A7 (Validate Uncertainty Before Scaling Complexity) apply here.

**Verdict**: The METACONCEPT (different reviews for different concerns) is valid and already present. Adding a full taxonomy of reviewer types may be over-engineering before evidence shows it's needed across multiple projects.

#### Challenge 2: "New document vs integration"

The request asks whether this should be a new document or integrated into SDD-CYCLE-GOVERNANCE.

**Against integrating into SDD-CYCLE-GOVERNANCE**:
- SDD-CYCLE-GOVERNANCE is specifically about commit/push/verify mechanics
- Review framework is broader than SDD — it applies to integrations, architecture, operational readiness
- Stuffing review taxonomy into SDD-CYCLE-GOVERNANCE would bloat it beyond its scope

**Against a new standalone document**:
- Constitution A6: "Governance growth is operational cost"
- Constitution §6.7: "Governance about governance about governance is forbidden"
- A review framework document is literally governance about how to govern reviews
- The Operations Manual ALREADY has review/audit sections (§3.3, §5.3)

**The real option being missed**: Extend the Operations Manual's existing audit protocol (§5.3) with a review taxonomy. This is where audit/review procedures BELONG — it's the "adaptable procedures" document.

#### Challenge 3: Reviewer taxonomy scope

The request lists: "Architectural, Operational Readiness, Security, Performance, etc."

**Problem**: This is an open-ended list. "Etc." means the taxonomy is undefined. Constitution A3 (Boundary Discipline) says every component must define what it owns, what it exposes, what it NEVER does. A taxonomy with "etc." violates this.

**Recommendation**: Start with exactly the review types that have EVIDENCE of being needed:
1. **Implementation verification** (already exists in SDD-CYCLE-GOVERNANCE)
2. **Integration review** (already exists in Operations Manual §3.3)
3. **Architectural audit** (already exists in Operations Manual §5.3)

Any additional types (Security, Performance, etc.) should be added ONLY when a project demonstrates need, not anticipated abstractly. This is A6 (Governance Minimalism) and A7 (Validate Uncertainty Before Scaling Complexity) in practice.

#### Challenge 4: "Conditions to prevent endless review loops"

This is a real concern but the solution already exists:
- SDD-CYCLE-GOVERNANCE §3: Verify has a PASS/FAIL verdict. FAIL loops to triage, then re-verify. The loop is bounded by the triage process (findings go to backlog).
- Constitution B1 (Freeze Discipline): At some point, architecture must stop moving.
- Constitution B4 (Stabilization Progression): Mutation should become increasingly constrained after freezes and audits.

The anti-loop mechanism is: **evidence-based exit criteria + freeze discipline**. A separate document to "prevent endless review loops" is governance-about-governance unless it adds concrete mechanisms beyond what already exists.

### Recommendation for Exploration B

**Do NOT create a new standalone document.** Instead:

1. **Extend Operations Manual §5 (Stabilization Protocol)** with a new section §5.5 "Review Taxonomy" that:
   - Defines the review types already scattered across documents (implementation verification, integration review, architectural audit)
   - Provides a framework for adding new review types when projects demonstrate need
   - Defines common review mechanics: inputs, outputs, exit criteria, traffic-light reporting
   - Cross-references SDD-CYCLE-GOVERNANCE for implementation verification specifics
   - Cross-references §3.3 for integration review specifics

2. **Update SDD-CYCLE-GOVERNANCE** to reference Operations Manual §5.5 for the general review framework, while keeping its specific verify-report contract in place.

3. **Do NOT pre-define reviewer types** like Security, Performance, etc. at the Portable OS level. Let them emerge from project-specific needs. The framework should provide the MECHANISM for defining new review types, not the TYPES themselves.

**Rationale**:
- Follows A6 (Governance Minimalism): extends existing document instead of creating new one
- Follows A3 (Boundary Discipline): Operations Manual is where procedures go
- Follows B5 (Operational Progress): starts with what exists, extends incrementally
- Avoids §6.7 (Governance Recursion): doesn't create a meta-document about reviews
- Allows evolution: new review types can be added to §5.5 as projects demonstrate need

### Proposed Structure for Operations Manual §5.5

```markdown
## 5.5 Review Taxonomy

*Built upon: A8 (Evidence Before Complexity), B1 (Freeze Discipline), B4 (Stabilization Progression)*

### Purpose
Define the common mechanics for all review activities within Portable OS projects.

### Review Types (defined elsewhere, referenced here)
| Type | Defined in | Scope |
|------|-----------|-------|
| Implementation Verification | SDD-CYCLE-GOVERNANCE §6 | SDD apply→verify gate |
| Integration Review | §3.3 of this Manual | New dependency/tool/service adoption |
| Architectural Audit | §5.3 of this Manual | Drift, boundary, complexity analysis |

### Common Review Mechanics
- Every review MUST define: scope, inputs, exit criteria, verdict format
- Every review MUST produce evidence (not opinions)
- Traffic-light reporting: PASS / CONDITIONAL / FAIL
- Reviews are bounded: maximum iterations before escalation
- Review types may be added per-project when evidence demonstrates need

### Adding New Review Types
Before adding a review type to a project:
1. Evidence that the review catches issues other reviews miss
2. The review has clear scope (what it covers AND what it doesn't)
3. The review has defined exit criteria (no open-ended reviews)
4. The review's operational cost is justified by what it prevents
```

---

## Synthesis — How Both Explorations Relate

### Common Root Cause

Both explorations reveal the SAME structural problem: **documents that should cross-reference each other don't, creating invisible rules and duplicated concepts.**

- Exploration A: GIT-WORKFLUX and SDD-CYCLE-GOVERNANCE don't cross-reference properly
- Exploration B: Review concepts are scattered across 3 documents with no unified reference point

### The Deeper Pattern

The Portable OS governance system has:
1. **Good bones**: The authority hierarchy is well-defined (Constitution → Operations Manual → domain documents)
2. **Cross-referencing debt**: Documents were written sequentially and not all bilateral references were added
3. **Scattered concerns**: Related concepts (verification, review, audit) live in different documents without a connecting thread

### No Contradictions Between Explorations

Both explorations point toward the same solution: **improve cross-references and add connecting structure without creating new top-level documents.**

- Exploration A says: connect GIT-WORKFLUX ↔ SDD-CYCLE-GOVERNANCE with explicit cross-references
- Exploration B says: connect review concepts via Operations Manual §5.5, cross-referencing SDD-CYCLE-GOVERNANCE

### Recommended Next Steps

1. **Immediate**: Create a proposal to update GIT-WORKFLUX and SDD-CYCLE-GOVERNANCE with mutual cross-references and missing rules (from Exploration A). This is a bounded, well-defined change.

2. **Then**: Create a proposal to extend Operations Manual §5 with §5.5 Review Taxonomy (from Exploration B). This starts small and evolves.

3. **Do NOT**: Create a standalone "Portable OS Review Framework" document at this time. The evidence doesn't justify it (A6, A7, §6.7).

4. **Challenge for the user**: The request to "create the initial draft that we will gradually evolve" is reasonable — but the draft should live INSIDE the Operations Manual, not as a new top-level document. If it grows beyond the Operations Manual's scope in the future, THAT is when to consider extraction.

---

## Ready for Proposal

**Yes, with conditions.**

Two proposals can be created:

1. **Proposal: "Cross-reference alignment"** — Update GIT-WORKFLUX and SDD-CYCLE-GOVERNANCE to add mutual cross-references, define `wip:` in GIT-WORKFLUX, specify PR timing and branch naming for SDD changes. Bounded, low-risk, clearly needed.

2. **Proposal: "Review taxonomy extension"** — Extend Operations Manual §5 with §5.5 Review Taxonomy. Starts with existing review types, provides mechanism for adding new ones. Exploratory, expected to evolve.

The orchestrator should tell the user:
- The audit found real, specific gaps that explain why rules are being left out
- The Review Framework idea has merit but should NOT be a new document — it belongs in the Operations Manual
- The user's instinct about review types evolving is correct, but the starting point should be smaller than proposed (3 types with evidence, not an open-ended taxonomy)
- Constitution A6 is the governing constraint: governance growth is operational cost
