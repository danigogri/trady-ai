# GIT WORKFLUX v1

**Status:** ACTIVE
**Authority Level:** Architecture + Execution (adaptable)
**Derives Authority From:** PORTABLE-OS-CONSTITUTION.md, BACKLOG-PROTOCOL.md

---

## 1. Propósito

Definir el flujo de control de versiones para proyectos que adoptan PORTABLE OS + SDD.

Este documento traduce los principios constitucionales (A1 — Deterministic-First, A5 — Simplicity Doctrine) a prácticas concretas de git.

---

## 2. Commit Convention

### Formato

```
<tipo>: <descripción> (<opcional: contexto>)
```

### Tipos válidos

| Tipo  | Cuándo usarlo                                      | Ejemplo                                                      |
| ----- | -------------------------------------------------- | ------------------------------------------------------------ |
| feat  | Cierre / freeze de una fase del roadmap            | `feat: Fase 1 — Deterministic Core (117 tests, 97% coverage)` |
| fix   | Corrección de un bug o error registrado en backlog | `fix: reificar Literals para state y action (BL-005)`        |
| deuda | Pago de deuda técnica registrada en backlog        | `deuda: tipar __init__ de modelos Pydantic (BL-001)`         |
| docs  | Cambios exclusivos de documentación                | `docs: agregar GIT-WORKFLUX.md`                              |
| spec  | Cambios en RFCs o SDDs                             | `spec: propuesta Polymarket Fase 2`                          |

### Reglas

- Primer commit del proyecto: `feat: bootstrap inicial de <proyecto>`
- Commits atómicos: un concepto por commit
- Sin emojis, sin Co-Authored-By, sin AI attribution
- Cuerpo del commit (opcional): describir qué y por qué, no cómo

---

## 3. Branch Strategy

### Estructura

```
main                    → línea base estable, solo merge vía PR
fix/BL-XXX              → un fix del backlog por branch
feat/<nombre-fase>      → una fase completa del roadmap
```

### Flujo

```text
git checkout main
git pull
git checkout -b fix/BL-005
  ... código, tests, verificación ...
git add .
git commit -m "fix: descripción (BL-005)"
git push -u origin fix/BL-005
  → gh pr create --fill
  → revisión, merge a main
git checkout main
git pull
```

### Reglas

- `main` siempre estable y deployable
- Branches cortas: un cambio por branch
- Una branch por concepto, no por persona
- Las branches se borran post-merge
- Sin commits directos en main local — todo cambio (código, docs, governance,
  cleanup) arranca desde un branch. Si no hay un branch, créelo primero.

---

## 4. Pull Requests

### Creación

```bash
gh pr create --fill
```

### Review

- El autor del PR no se mergea solo (salvo urgencia documentada)
- Mínimo 1 approval antes de mergear

### Merge

- `Squash and merge` para branches de fix
- `Merge commit` para fases completas (preserva el historial atómico de la fase)

---

## 5. Relación con SDD y BACKLOG-PROTOCOL

### Ciclo completo

```text
1. RFC / SDD define qué y por qué
2. BACKLOG registra hallazgos fuera de alcance
3. Branch implementa el cambio específico
4. Commit documenta qué se hizo
5. PR habilita revisión
6. Merge a main = freeze del cambio
```

### Freeze por fase

Cada vez que una fase del roadmap se completa:

```bash
git add .
git commit -m "feat: Fase N — <nombre>"
git push
gh pr create --fill
```

El PR de freeze debe incluir:
- Resumen de lo implementado
- Métricas de verificación (tests, coverage, mypy)
- Checklist de acceptance criteria

---

## 6. Seguridad

- `.env`, `*.db`, `__pycache__/`, `.venv/` están en `.gitignore`
- El email de commits usa el noreply de GitHub (`@users.noreply.github.com`)
- Repos privados hasta producción explícita
- No committear secrets, tokens, o credenciales

---

## 7. Contraindicaciones

Este workflow NO aplica para:

- Proyectos sin SDD o equivalente
- Equipos que requieren git-flow estricto (release branches, hotfix branches)
- Monorepos con múltiples proyectos independientes

---

## 8. Referencias

- PORTABLE-OS-CONSTITUTION.md — principios A1, A5
- PORTABLE-OS-OPERATIONS-MANUAL.md — integration doctrine
- BACKLOG-PROTOCOL.md — registro de hallazgos
- TRADY-AI-MASTER-ROADMAP-001.md — fases del roadmap
