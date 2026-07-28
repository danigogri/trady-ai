# Design: Review Methodology (§5.5) + Review Gates (SDD Cycle Governance)

## Technical Approach

Two additive markdown sections into existing governance documents, zero modifications to existing content. Both sections share the same core insight — there is one universal 12-step review methodology applied to all artifacts, not specialized review types. §5.5 defines the methodology. Review Gates define when it runs across the SDD cycle.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|---|---|---|---|
| §5.5 insertion point | After §5.4 vs. as §6.x | After §5.4 keeps Stabilization Protocol (§5) coherent; as §6.x breaks logical grouping | After §5.4, before §6 (Discovery Protocol) |
| Review Gates insertion | Between §8 and §9 vs. as new §2 | Before history preserves reading order; as §2 requires renumbering all sections | Between §8 and §9 — additive, no renumbering |
| Step numbering style | `### Step 1 —` vs. `#### 5.5.1` | `###` follows Operations Manual subsection pattern; `####` adds unnecessary depth | `### Step N — Title` — consistent with §5.3 subsections |
| Phase grouping format | `#### Phase I` headings vs. prose annotation | Headings create implicit sub-entry points (violates universal sequence rule) | Prose annotation only — phases are presentational |

## Authority & Derivation

```
A3 (Boundary Discipline)   → all 12 steps always, never subsets
A6 (Governance Minimalism) → one methodology, not 4+ review types
A7 (Optional Doctrine)     → gates as SHOULD at OS, MUST after adoption
A8 (Evidence Before Complexity) → methodology is HOW to reach evidence-based conclusions
A2 (Architecture Before)   → gates enforce phase prerequisites
A4 (Fail-Fast)             → FAIL semantics, anti-loop escalation
B6 (Structured Work Cycle) → 7 gates align with SDD cycle phases
```

## Section Architecture

### Operations Manual §5.5 "Review Methodology"

**Insert after** line 287 (`---` after §5.4 end), before line 289 (`# 6. DISCOVERY PROTOCOL`).

```
## 5.5 Review Methodology
*Built upon: A3, A6, A8, B6*

### Definition
{Universal 12-step methodology, one sequence, always in order}

### Phase Structure
{4 phases as prose annotations — Context Reconstruction [S1–2],
Consistency Analysis [S3–5], Architectural Integrity [S6–8],
Quality Validation [S9–12]}

### Step 1 — Identify Authority
### Step 2 — Reconstruct Context
### Step 3 — Detect Contradictions
### Step 4 — Detect Missing Information
### Step 5 — Detect Duplication
### Step 6 — Analyze Responsibility Allocation
### Step 7 — Analyze Dependencies
### Step 8 — Evaluate Evolution
### Step 9 — Verify Terminology
### Step 10 — Compare Against Foundational Principles
### Step 11 — Operational Risk Review
### Step 12 — Future Technical Debt Review

### Cross-Reference: Audit Protocol (§5.3)
{Steps 3–6 cross-ref §5.3 for WHAT criteria; §5.5 defines HOW}

### Anti-Loop Safeguards
{3 FAILs → escalate per §5.3 path}

### Extension Mechanism
{New steps require §6 Discovery Protocol}
```

Each step: 1–2 paragraphs (purpose + guidance). Cross-refs to §5.3 in steps 3–6 using `(see §5.3 — [specific criteria])`.

### SDD Cycle Governance "Review Gates"

**Insert between** line 122 (end of §8 `---`) and line 125 (`## 9. Historia de Refinamiento`).

```
## Review Gates

### Authority Level
{SHOULD at OS level, MUST after explicit adoption — mirrors A7}

### The 7 Gates

| Gate | Artifact | Gates → |
|------|----------|---------|
| G0 | Exploration | → Proposal |
| G1 | Proposal | → Spec |
| G2 | Spec | → Design |
| G3 | Design | → Tasks |
| G4 | Tasks | → Apply |
| G5 | Verify-report | → Archive |
| G6 | Archive artifacts | → Close |

### Verdict Semantics
{PASS / WARN / FAIL — table per spec §3}

### Gate-Specific FAIL Triggers
{Table per spec §4 — one row per gate with typical CRITICAL findings}

### Anti-Loop
{References §5.5 anti-loop — 3 FAILs → escalation}

### Cross-Reference
{§5.5 defines methodology; this section defines lifecycle placement only}
```

## Cross-Reference Map

```
§5.5 ──→ §5.3 (Audit Protocol): steps 3–6 use §5.3 criteria
§5.5 ──→ Review Gates: "applied at each SDD phase transition"
Review Gates ──→ §5.5: "methodology defined in Operations Manual §5.5"
Review Gates ──→ §6 (SDD Verify-Report): G5 reviews verify-report contract
```

## Data Flow Diagram

```
[S1–2: Context Reconstruction]
    ↓
[S3–5: Consistency Analysis] ←── §5.3 Audit criteria (steps 3–6)
    ↓
[S6–8: Architectural Integrity]
    ↓
[S9–12: Quality Validation] ──→ Findings (PASS/WARN/FAIL)
    ↓
    ⊕ 3 FAILs? → Escalate (§5.3 escalation path)
    ↓
    Verdict → feeds next gate in SDD cycle


SDD Cycle with Gates:

Exploration ──→ G0 ──→ Proposal ──→ G1 ──→ Spec ──→ G2 ──→ Design
                        ↑              ↑              ↑
                        └─── ALL use §5.5 12-step methodology

Design ──→ G3 ──→ Tasks ──→ G4 ──→ Apply ──→ G5 ──→ Archive ──→ G6 ──→ Close
```

## Impact Analysis

| File | Action | Insertion Point |
|---|---|---|
| `PORTABLE-OS-OPERATIONS-MANUAL.md` | Modify — add §5.5 | After §5.4 line 287, before §6 line 289 |
| `SDD-CYCLE-GOVERNANCE.md` | Modify — add Review Gates | After §8 line 122, before §9 line 125 |

No other files affected. No existing content modified.

## Key Design Rules Applied

- **A6 (Governance Minimalism)**: One methodology, no type-specific review sections. Cross-refs avoid duplicating §5.3.
- **Universal sequence**: Phases are cosmetic grouping only — not entry points. Stated explicitly in §5.5.
- **Bidirectional refs**: Both sections can be read independently with clear pointers to the other.
- **Extension mechanism**: Uses existing §6 Discovery Protocol rather than creating new process.

## Open Questions

- [ ] Should the Review Gates section in SDD-CYCLE-GOVERNANCE.md be bilingual (Spanish header + English content) or match the document's existing Spanish?
- [ ] Should G5 (verify-report gate) explicitly define how it interacts with the existing §6 Verify-Report Contract's PASS semantics?
