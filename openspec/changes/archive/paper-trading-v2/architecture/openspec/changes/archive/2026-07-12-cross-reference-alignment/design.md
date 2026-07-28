# Design: Cross-Reference Alignment

## Technical Approach

Precise additive edits to two markdown governance documents: add missing conventions (`wip:` commit type, `sdd/<change-name>` branch pattern, PR timing, merge strategy) and establish bidirectional cross-references between them. Zero structural changes, zero new files.

**Authority chain**: Constitution A3 (Boundary Discipline) → A6 (Governance Minimalism) → A8 (Evidence Before Complexity).

## Architecture Decisions

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Rewrite sections vs. precise edits | Rewrite risks drift; precise edits preserve existing content | Precise insertions only |
| Cross-ref style | Inline disrupts flow; footnotes add indirection; blockquotes are visually distinct and match existing `> **Nota:**` pattern in SDD-CYCLE-GOVERNANCE | Blockquote notes (`> **Nota:**`) |
| `wip:` position in types table | Alphabetical vs. grouped with `spec` (both SDD-related) | After `spec` — keeps SDD types together |

## Impact Analysis

**Files affected**: 2 existing markdown files, 0 new, 0 deleted. Edits are independent between files — no ordering dependency. Each change targets a single § with no cascading effects on downstream documents.

## File Changes

### GIT-WORKFLUX.md — 6 insertions

| Location | Operation | Content |
|----------|-----------|---------|
| §2, after `spec` row in types table | Insert row | `\| wip \| Commits locales WIP durante el ciclo SDD (apply→verify) \| \`wip: apply <change>, unverified\` \|` |
| §2, after types table | Insert blockquote | `> **Nota**: Para semántica completa del tipo \`wip:\` (amend, squash, push prohibition), ver SDD-CYCLE-GOVERNANCE.md §4.` |
| §3 Branch Structure, after `feat/<nombre-fase>` | Insert pattern | `sdd/<change-name>       → un cambio del ciclo SDD (proposal→archive)` |
| §3 Flujo, after flow code block | Insert blockquote | `> **SDD**: Para cambios SDD, el PR se crea en la fase Archive (post-squash), no al pushear el branch. Ver SDD-CYCLE-GOVERNANCE.md §3.` |
| §5 Freeze por fase, after checklist | Insert sentence | `Para el contrato completo del verify-report (formato, contenido, veredicto), ver SDD-CYCLE-GOVERNANCE.md §6.` |
| §8 Referencias, after last entry | Insert ref | `- SDD-CYCLE-GOVERNANCE.md — ciclo SDD, WIP semantics, verify-report contract` |

### SDD-CYCLE-GOVERNANCE.md — 4 insertions

| Location | Operation | Content |
|----------|-----------|---------|
| §3 step 5, after `├── Squash` line | Insert line | `   ├── Crear PR (\`gh pr create --fill\`) — merge vía squash-and-merge` |
| §3, after cycle diagram code block | Insert blockquote | `> **Branch naming**: Para la convención \`sdd/<change-name>\`, ver GIT-WORKFLUX.md §3.` |
| §4, after WIP rules table | Insert blockquote | `> **Nota**: El tipo \`wip:\` está reconocido como tipo válido en GIT-WORKFLUX.md §2.` |
| §6, after verify-report requirements | Insert sentence | `El verify-report es el artefacto de evidencia que conecta el ciclo SDD con el workflow git — ver GIT-WORKFLUX.md §5.` |

## Bidirectional Cross-Reference Map

| GIT-WORKFLUX § | → SDD-CYCLE-GOVERNANCE § | ← Back-ref |
|----------------|--------------------------|------------|
| §2 (wip: type) | §4 (WIP semantics) | §4 → §2 |
| §3 (branch + PR timing) | §3 (Archive step 5) | §3 → §3 |
| §5 (verify-report) | §6 (verify-report contract) | §6 → §5 |
| §8 (references) | entire doc | implicit through hierarchy note |

Zero orphan references — every forward ref has a matching back-ref.

## Testing Strategy

N/A — no executable code. Verification is manual diff review of the two files after edits, confirming each table and note matches the spec scenarios.

## Migration / Rollout

No migration required. Apply as a single atomic change (both files in one branch/PR).

## Open Questions

None.
