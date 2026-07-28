# Proposal: Cross-Reference Alignment

## Intent

Exploration A found 6 gaps between GIT-WORKFLUX.md and SDD-CYCLE-GOVERNANCE.md causing agents reading one document to miss the other's rules. Fix with missing conventions + bidirectional cross-references.

**Authority**: Constitution A3 + A6 + A8. Adds refs, not rules — zero duplication.

## Scope

### In Scope
- GIT-WORKFLUX §2: add `wip:` commit type, cross-ref SDD-CYCLE-GOVERNANCE
- GIT-WORKFLUX §3: add `sdd/<change-name>` branch pattern
- Both docs: define PR creation timing (Archive phase, after squash)
- GIT-WORKFLUX §5+§8 → SDD-CYCLE-GOVERNANCE cross-refs
- SDD-CYCLE-GOVERNANCE §3+§6 → GIT-WORKFLUX cross-refs
- SDD-CYCLE-GOVERNANCE §3: define merge strategy (squash-and-merge)
- Cross-ref verify-report between GIT-WORKFLUX §5 and SDD-CYCLE-GOVERNANCE §6

### Out of Scope
Hotfix procedure, tag/release, CI/CD, PR templates, GitHub archival rule.

## Capabilities

### New Capabilities
None — this is pure document alignment, no new behavioral specs.

### Modified Capabilities
None — no existing `openspec/specs/` exist for these documents.

## Approach

1. Edit GIT-WORKFLUX.md: add `wip:` to §2, add `sdd/<change-name>` branch pattern to §3, add PR-timing cross-ref to §3 flow note, add SDD-CYCLE-GOVERNANCE link to §5 and §8
2. Edit SDD-CYCLE-GOVERNANCE.md: add PR creation timing (Archive step) to §3, define merge strategy explicitly, add GIT-WORKFLUX cross-refs, connect verify-report to GIT-WORKFLUX §5

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `GIT-WORKFLUX.md` | Modified | §2 (add wip: type), §3 (branch naming, PR timing ref), §5 (cross-ref), §8 (cross-ref) |
| `SDD-CYCLE-GOVERNANCE.md` | Modified | §3 (PR timing, merge strategy, cross-ref), §4 (wip: ref to GIT-WORKFLUX), §6 (verify-report cross-ref) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cross-refs get out of sync | Low | Same session, reviewed together |
| Contradictory instructions | Low | Changes are additive, not conflicting |

## Rollback Plan

Revert the two edited files from git or from backup/ directory. Changes are isolated to two files with no downstream dependencies.

## Dependencies

None — standalone document edits.

## Success Criteria

- [ ] GIT-WORKFLUX §2 lists `wip:` as valid type with SDD-CYCLE-GOVERNANCE cross-ref
- [ ] SDD-CYCLE-GOVERNANCE §3 states PR timing (create at Archive, after squash)
- [ ] Branch naming `sdd/<change-name>` defined in GIT-WORKFLUX §3
- [ ] GIT-WORKFLUX §5+§8 link to SDD-CYCLE-GOVERNANCE; SDD-CYCLE-GOVERNANCE §3 links back
- [ ] Merge strategy for SDD changes stated in SDD-CYCLE-GOVERNANCE §3
- [ ] Verify-report cross-referenced between GIT-WORKFLUX §5 and SDD-CYCLE-GOVERNANCE §6
