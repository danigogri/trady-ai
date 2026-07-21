# SDD Cycle Governance v1

**Status:** ACTIVE
**Authority Level:** Architecture (binding for SDD phases)
**Derives Authority From:** PORTABLE-OS-CONSTITUTION.md, GIT-WORKFLUX.md (parental), BACKLOG-PROTOCOL.md

> **Nota de jerarquía**: Este documento es una **extensión de GIT-WORKFLUX.md**. GIT-WORKFLUX.md es el documento **parental** de este. No existe jerarquía en conflicto: este documento extiende el workflux git con reglas específicas para el ciclo SDD, sin contradecir ni reemplazar las convenciones de commit, branch y PR definidas en el parental. En caso de discrepancia interpretativa, GIT-WORKFLUX.md prima para git-ops generales; este documento prima para el flujo específico apply→verify→archive.

---

## 1. Propósito

Gobernar el ciclo SDD (proposal → spec → design → tasks → apply → verify → archive)
con dos invariantes:

1. **Commit pushed a GitHub = estado verificado** (filosofía original del proyecto)
2. **Working tree nunca es la única copia del trabajo en progreso** (patch de robustez)

---

## 2. Invariante de Commit

Un commit pusheado a GitHub representa un estado verificado.
Nunca se pushea código no verificado.

**Corolario**: los commits locales WIP (no pushed) NO violan este invariante —
son snapshots privados, desechables, y squasheables antes del push final.

---

## 3. Ciclo Refinado

```
1. Apply
   ├── Implementa código + tests
   ├── Genera artifacts: design.md, tasks.md, apply-progress.md
   └── ⚡ COMMIT LOCAL: "wip: apply <change>, unverified" (NO pushear)

2. Verify #1
   ├── Corre contra hash local (reproducible)
   ├── Reporte referencia: "verify contra commit <hash>"
   └── Hallazgos → registrados en verify-report

3. Triage de hallazgos → Backlog (BL-XXX) → fixes en working tree
   └── ⚡ AMEND del commit local (sigue local-only)

4. Verify #2 (contra nuevo hash)
   ├── Si verde → pasar a 5
   └── Si rojo → loop 2–4

5. Archive
   ├── Archiva pr-body.md y assessment-report.md (o cualquier documento generado
   │   para el ecosistema GitHub) en openspec/changes/archive/{cambio}/
   │   — GitHub es una dependencia externa, no la única copia (Constitución B2)
    ├── Squash commits WIP en UN commit limpio: "feat: <change>"
    ├── Crear PR (`gh pr create --fill`) — merge vía squash-and-merge
    ├── Push final a GitHub
    └── Merge PR = freeze del cambio
```

> **Branch naming**: Para la convención `sdd/<change-name>`, ver GIT-WORKFLUX.md §3.

---

## 4. Reglas del Commit Local WIP

| Regla | Razón |
|-------|-------|
| Prefijo `wip:` | Distingue de commits finales `feat:`/`fix:`/`deuda:` |
| Nunca pushear | El remoto solo recibe estados verificados |
| Amend libre entre verifies | Es desechable hasta archive |
| Squash en archive | El history remoto ve un solo commit limpio |
| Mensaje incluye cambio + fase | "wip: apply polymarket-integration Fase 2" |

> **Nota**: El tipo `wip:` está reconocido como tipo válido en GIT-WORKFLUX.md §2.

---

## 5. Evidencia de Decisiones

El commit local WIP sirve como evidencia de:

- Qué decisiones de implementación se tomaron (diff)
- Por qué se tomaron (mensaje + apply-progress.md)
- Qué hallazgos hubo en verify #1 (verify-report.md)
- Cómo se arreglaron (diff entre WIP y WIP-amend)
- Qué se verificó y contra qué hash (verify-report.md)
- Qué documentación acompañó al cambio (pr-body.md, assessment-report.md,
  y cualquier documento generado para GitHub)

Todo sobrevive en `.git/objects` hasta el archive.
Post-archive, el squash consolida el relato final en un commit pusheado.

Los documentos generados para el ecosistema GitHub (PR bodies, assessment reports,
etc.) DEBEN archivarse localmente en openspec/changes/archive/{cambio}/ antes del
squash. GitHub es una dependencia externa (Constitución B2 — Integration Hostility)
y no debe ser la única copia de documentación crítica del proyecto.

---

## 6. Verify-Report Contract

Todo verify-report DEBE incluir:

- Hash del commit local que se verificó
- Salida completa de: mypy, ruff, pytest (con coverage)
- Hallazgos clasificados: CRITICAL / WARNING / SUGGESTION
- Status del apply-progress: consistente / inconsistente
- Veredicto: PASS (archive-ready) / FAIL (loop a triage)

El verify-report es el artefacto de evidencia que conecta el ciclo SDD con el workflow git — ver GIT-WORKFLUX.md §5.

---

## 7. Excepciones

- Para cambios triviales (protocolo Assessment de 2 niveles):
  commit local WIP opcional, directo a commit final si el área es <=1 archivo
  de tipo annotation/import.
- Para solo-docs: no requiere WIP, directo a commit final.

---

## 8. Relación con Documentos Existentes

- **GIT-WORKFLUX.md (parental)**: este documento extiende la commit convention del parental con el tipo `wip:`. No la reemplaza. La branch strategy del parental se mantiene. El PR final va post-archive (squash).
- **BACKLOG-PROTOCOL.md**: hallazgos de verify entran al backlog como BL-XXX.
- **CONSTITUTION.md A1**: Deterministic-First preserved — verify sigue siendo el gate.

---

## Review Gates

*Built upon: A2 (Architecture Before Implementation), A4 (Fail-Fast), A7 (Optional Doctrine), A8 (Evidence Before Complexity), B6 (Structured Work Cycle)*

### Authority Level

Review gates are defined as **SHOULD** at Portable OS level. A project that explicitly adopts review gates (by referencing this section in its own SDD Cycle Governance or Operations Manual extension) MUST treat them as **MUST**. This mirrors the Optional Doctrine pattern (Constitution A7).

Until explicit adoption, review gates are recommended but not required. Projects operating without gates may still benefit from applying the methodology defined in Operations Manual §5.5 informally.

### The 7 Gates

Each gate applies the universal 12-step Review Methodology (Operations Manual §5.5) to that phase's artifact. The gated phase MUST NOT begin until the gate produces at least WARN.

| Gate | Artifact Reviewed | Gates Transition To |
|------|-------------------|---------------------|
| G0 | Exploration | → Proposal |
| G1 | Proposal | → Spec |
| G2 | Spec | → Design |
| G3 | Design | → Tasks |
| G4 | Tasks | → Apply |
| G5 | Verify-report | → Archive |
| G6 | Archive artifacts | → Close |

The methodology for each gate is defined in Operations Manual §5.5. This section defines only which artifact to review at which transition.

### Verdict Semantics

Each gate produces a traffic-light verdict by applying the universal methodology:

| Verdict | Meaning | Effect |
|---------|---------|--------|
| PASS | No CRITICAL findings, methodology complete | Phase transition permitted |
| WARN | Non-blocking concerns documented (SHOULD fix before next gate) | Phase transition permitted; caveats recorded for next gate |
| FAIL | CRITICAL finding(s) unresolved | Phase transition BLOCKED; artifact must be revised and re-reviewed |

A gate verdict of PASS or WARN permits the next phase to begin. A FAIL verdict blocks the transition until the CRITICAL findings are resolved and a subsequent review produces at least WARN.

### Gate-Specific FAIL Triggers

Each gate's verdict derives from applying the universal methodology to its specific artifact. Below are typical CRITICAL findings that trigger FAIL for each gate — these are illustrative, not exhaustive:

| Gate | Typical CRITICAL Findings (FAIL Triggers) |
|------|-------------------------------------------|
| G0 | Exploration scope misaligned with radar; missing alternatives; no clear recommendation |
| G1 | Proposal intent unclear; scope boundaries missing; no rollback plan; authority not identified |
| G2 | Requirements not using RFC 2119; scenarios missing edge cases; spec contradicts higher authority |
| G3 | Design introduces architectural drift; missing responsibility ownership; dependencies unresolved |
| G4 | Tasks not traceable to spec/design; acceptance criteria missing; effort estimates absent |
| G5 | Verify-report missing evidence; CRITICAL findings unresolved; apply-progress inconsistent |
| G6 | Archive artifacts incomplete; change record missing; cross-document consistency violated |

These triggers are the output of applying Steps 3–6 (Consistency Analysis) of the §5.5 methodology to each phase's artifact type.

### Anti-Loop

Gate review loops are bounded by Operations Manual §5.5 anti-loop rules: 3 consecutive FAILs on the same work product trigger escalation per the §5.3 escalation path. The escalation record MUST document the recipient, complete iteration history, and the specific decision requiring higher authority.

### Cross-Reference

- **Methodology**: The 12-step methodology applied at each gate is defined in Operations Manual §5.5 (§5.5 Review Methodology). This section defines lifecycle placement only.
- **Audit criteria**: Specific validation criteria for Steps 3–6 are defined in Operations Manual §5.3 (Audit Protocol).
- **Verify-report contract**: G5 interacts with §6 (Verify-Report Contract) — the verify-report is the artifact under review at the Apply → Archive transition.

---

## 9. Historia de Refinamiento

| Fecha | Refinamiento | Razón |
|-------|--------------|-------|
| 2026-07-09 | v1 inicial | Working tree solo entre apply y archive = riesgo de pérdida. Commits locales WIP + squash en archive cierran el gap sin romper "push = verified". |