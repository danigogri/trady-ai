# Tasks: Cross-Reference Alignment

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 50-80 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | All 10 insertions across both docs | Single PR | `main` base; no tests needed |

## Phase 1: GIT-WORKFLUX.md — 6 insertions

- [x] 1.1 Insert `wip:` row in §2 types table after `spec` entry
- [x] 1.2 Insert blockquote note after §2 table: `> **Nota**: ...ver SDD-CYCLE-GOVERNANCE.md §4.`
- [x] 1.3 Insert `sdd/<change-name>` pattern in §3 branch structure after `feat/<nombre-fase>`
- [x] 1.4 Insert PR timing blockquote after §3 flow code block: links to SDD-CYCLE-GOVERNANCE §3
- [x] 1.5 Insert verify-report cross-ref sentence in §5 (after checklist): links to SDD-CYCLE-GOVERNANCE §6
- [x] 1.6 Insert SDD-CYCLE-GOVERNANCE.md entry in §8 references list

## Phase 2: SDD-CYCLE-GOVERNANCE.md — 4 insertions

- [x] 2.1 Insert PR creation line in §3 step 5 after squash line: `├── Crear PR (gh pr create --fill) — merge vía squash-and-merge`
- [x] 2.2 Insert branch naming blockquote after §3 cycle diagram: `> **Branch naming**: ...ver GIT-WORKFLUX.md §3.`
- [x] 2.3 Insert `wip:` type note in §4 after WIP rules table: links GIT-WORKFLUX §2
- [x] 2.4 Insert verify-report cross-ref sentence in §6: links to GIT-WORKFLUX §5

## Phase 3: Verification

- [x] 3.1 Manual diff review: confirm all 10 insertions match design table and spec scenarios
- [x] 3.2 Bidirectional cross-ref check: every forward ref has a matching back-ref (design §4 map)
- [x] 3.3 Verify no orphan references and no existing content was modified or deleted
