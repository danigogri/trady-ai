# Proposal: Review Methodology (Operations Manual §5.5 + SDD Cycle Governance Gates)

## Intent

Review concepts exist across Constitution (A8), Operations Manual (§3.3, §5.3), and SDD Cycle Governance (§6). After analyzing real practice, we identified that every review is the same 12-step analytical methodology applied to different artifacts — not specialized review types. Formalize this insight: a single universal Review Methodology in Operations Manual, and artifact-specific gates in SDD Cycle Governance.

## Scope

### In Scope
- Operations Manual §5.5 "Review Methodology" — universal 12-step methodology grouped in 4 phases (Context Reconstruction, Consistency Analysis, Architectural Integrity, Quality Validation). Cross-references §5.3 (Audit Protocol) instead of duplicating it.
- SDD Cycle Governance "Review Gates" — 7 gates mapping every SDD phase transition (Exploration→Proposal→Spec→Design→Tasks→Apply→Verify→Archive→Close). Each gate applies the same methodology to that phase's artifact.
- Gates defined as SHOULD at Portable OS level → MUST for any project that explicitly adopts them (mirrors Optional Doctrine pattern).
- Cross-references both directions: §5.5 → SDD Gates and Gates → §5.5.

### Out of Scope
- Pre-defining Security Review, Performance Review etc. as separate types (deferred — universal methodology already covers them by applying the same 12 steps).
- Creating a standalone "Review Framework" document (violates A6, §6.7).
- Project-specific review implementations.

## Capabilities

None. This change adds procedural sections to existing governance documents. No new spec-level capabilities are introduced or modified.

## Approach

**Part A — Operations Manual §5.5 ("Review Methodology")**: Single universal sequence of 12 steps, always executed in order. If a step is not applicable to a specific artifact, conclude it immediately as "Not applicable." Grouped into 4 logical phases for readability and automation:

| Phase | Steps | Focus |
|---|---|---|
| Context Reconstruction | 1–2 | Authority, architectural context |
| Consistency Analysis | 3–5 | Contradictions, missing info, duplication |
| Architectural Integrity | 6–8 | Responsibility, dependencies, evolution |
| Quality Validation | 9–12 | Terminology, principles, risk, future debt |

Cross-references §5.3 (Audit Protocol) wherever steps overlap. §5.3 defines WHAT to audit; methodology defines HOW to reach conclusions.

**Part B — SDD Cycle Governance ("Review Gates")**: 7 gates, one for each SDD phase transition, each applying the universal methodology to that phase's artifact:

| Gate | Artifact reviewed | Gates transition to |
|---|---|---|
| G0 | Exploration | → Proposal |
| G1 | Proposal | → Spec |
| G2 | Spec | → Design |
| G3 | Design | → Tasks |
| G4 | Tasks | → Apply |
| G5 | Verify-report | → Archive |
| G6 | Archive artifacts | → Close |

Gates are SHOULD at Portable OS level. Projects that explicitly adopt them MUST comply (mirrors Optional Doctrine, Constitution A7).

## Authority & Derivation

- Constitution A3 (Boundary Discipline) → methodology vs lifecycle split; all 12 steps always, no subsets
- Constitution A6 (Governance Minimalism) → one universal methodology replaces 4+ specialized types
- Constitution A7 (Optional Doctrine) → gates are SHOULD at OS level, MUST after adoption
- Constitution A8 (Cross-verification) → §5.3 defines WHAT, methodology defines HOW

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `PORTABLE-OS-OPERATIONS-MANUAL.md` | Modified — add §5.5 | Universal Review Methodology |
| `SDD-CYCLE-GOVERNANCE.md` | Modified — add section | 7 Review Gates for all SDD phase transitions |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| 12 steps seen as heavy for simple artifacts | Medium | Steps conclude "Not applicable" when irrelevant; same sequence always, depth adapts |
| Overlap with §5.3 (Audit Protocol) | Low | Cross-reference, never duplicate |
| 7 gates could slow down rapid iteration | Low | Gates are SHOULD at OS level; projects opt in |

## Rollback

Revert the specific section additions in both documents. No structural changes beyond two new sections.

## Dependencies

None — additive sections, no conflicts with existing content.

## Success Criteria

- [ ] §5.5 defines a single universal 12-step methodology (not multiple types)
- [ ] §5.5 groups steps into 4 logical phases for readability
- [ ] §5.5 cross-references §5.3 (Audit Protocol) instead of duplicating
- [ ] SDD Cycle Governance defines 7 gates mapping every phase transition
- [ ] Gates are SHOULD at OS level, with adoption→MUST clause
- [ ] Cross-references connect §5.5 ↔ Review Gates (bidirectional)
- [ ] Anti-loop safeguards and extension mechanism are explicit
