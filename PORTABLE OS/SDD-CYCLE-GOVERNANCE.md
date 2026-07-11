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
   ├── Squash commits WIP en UN commit limpio: "feat: <change>"
   ├── Push final a GitHub
   └── Merge PR = freeze del cambio
```

---

## 4. Reglas del Commit Local WIP

| Regla | Razón |
|-------|-------|
| Prefijo `wip:` | Distingue de commits finales `feat:`/`fix:`/`deuda:` |
| Nunca pushear | El remoto solo recibe estados verificados |
| Amend libre entre verifies | Es desechable hasta archive |
| Squash en archive | El history remoto ve un solo commit limpio |
| Mensaje incluye cambio + fase | "wip: apply polymarket-integration Fase 2" |

---

## 5. Evidencia de Decisiones

El commit local WIP sirve como evidencia de:

- Qué decisiones de implementación se tomaron (diff)
- Por qué se tomaron (mensaje + apply-progress.md)
- Qué hallazgos hubo en verify #1 (verify-report.md)
- Cómo se arreglaron (diff entre WIP y WIP-amend)
- Qué se verificó y contra qué hash (verify-report.md)

Todo sobrevive en `.git/objects` hasta el archive.
Post-archive, el squash consolida el relato final en un commit pusheado.

---

## 6. Verify-Report Contract

Todo verify-report DEBE incluir:

- Hash del commit local que se verificó
- Salida completa de: mypy, ruff, pytest (con coverage)
- Hallazgos clasificados: CRITICAL / WARNING / SUGGESTION
- Status del apply-progress: consistente / inconsistente
- Veredicto: PASS (archive-ready) / FAIL (loop a triage)

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

## 9. Historia de Refinamiento

| Fecha | Refinamiento | Razón |
|-------|--------------|-------|
| 2026-07-09 | v1 inicial | Working tree solo entre apply y archive = riesgo de pérdida. Commits locales WIP + squash en archive cierran el gap sin romper "push = verified". |