# Tasks: Review Methodology (§5.5) + Review Gates (SDD Cycle Governance)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~200-300 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Operations Manual §5.5 "Review Methodology"

- [x] 1.1 Insert `## 5.5 Review Methodology` after §5.4 — define methodology, 4-phase prose annotation
- [x] 1.2 Write Step 1 (Identify Authority) and Step 2 (Reconstruct Context) with guidance
- [x] 1.3 Write Step 3 (Contradictions), Step 4 (Missing Info), Step 5 (Duplication) — cross-ref §5.3
- [x] 1.4 Write Step 6 (Responsibility), Step 7 (Dependencies), Step 8 (Evolution) — cross-ref §5.3
- [x] 1.5 Write Step 9 (Terminology), Step 10 (Principles), Step 11 (Risk), Step 12 (Debt)
- [x] 1.6 Write Cross-Reference (§5.3), Anti-Loop (3 FAILs → escalation), Extension Mechanism subsections

## Phase 2: SDD Cycle Governance "Review Gates"

- [x] 2.1 Insert "Review Gates" section after §8 — Authority Level (SHOULD/MUST per A7)
- [x] 2.2 Write The 7 Gates table (G0–G6: artifact, transition) with descriptions
- [x] 2.3 Write Verdict Semantics table (PASS/WARN/FAIL with meaning and effect)
- [x] 2.4 Write Gate-Specific FAIL Triggers table (one row per gate, typical CRITICAL findings)
- [x] 2.5 Write Anti-Loop (ref §5.5) and Cross-Reference (ref §5.5 methodology) subsections

## Phase 3: Cross-Reference & Format Verification

- [x] 3.1 Verify bidirectional cross-refs: §5.5 → Review Gates and Review Gates → §5.5
- [x] 3.2 Verify §5.5 steps 3–6 cross-ref §5.3 Audit Protocol instead of duplicating it
- [x] 3.3 Verify markdown heading levels match existing patterns (`## 5.5`, `### Step N`)
- [x] 3.4 Verify all spec scenarios covered: 12 steps execute always, phases cosmetic only, gate verdict semantics, anti-loop escalation
