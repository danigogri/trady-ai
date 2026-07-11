## Resumen

Archivo local de documentación GitHub-specific + actualización del SDD Cycle Governance.

## Qué cambió

### 1. Documentación GitHub archivada localmente

Los PR bodies y assessment reports que antes vivían solo en `.github/` (y dependían de GitHub como única copia) se movieron a `openspec/changes/archive/`, junto al resto de artifacts de cada cambio:

- `openspec/changes/archive/2026-07-10-polymarket-integration/assessment-report.md`
- `openspec/changes/archive/2026-07-10-polymarket-integration/pr-body.md`
- `openspec/changes/archive/2026-07-09-backlog-fase1/pr-body.md`

### 2. SDD-CYCLE-GOVERNANCE.md actualizado

Dos cambios en el governance para que futuros ciclos no pierdan documentación:

- **§3 paso 5 (Archive)**: ahora dice explícitamente que `pr-body.md`, `assessment-report.md` y cualquier documento generado para GitHub deben archivarse en `openspec/changes/archive/{cambio}/` **antes del squash**
- **§5 (Evidencia de Decisiones)**: los PR docs se listan como evidencia de decisiones + se agrega la regla DEBEN archivarse localmente

### 3. Working tree limpiado

Se descartaron ~7,570 líneas de CRLF noise (line endings) que habían quedado en el working tree después del archive de Fase 2.

## Por qué

GitHub es una dependencia externa (Constitución B2 — Integration Hostility). Si GitHub desaparece, pierde el acceso a los PR bodies y assessment reports. La copia local en `openspec/changes/archive/` es permanente e independiente del ecosistema GitHub.

El governance ahora lo exige explícitamente para que ningún agente futuro tenga que redescubrir este problema.

## Verification gates

| Gate | Resultado |
|------|-----------|
| mypy | 0 errores (sin cambios en código) |
| ruff | 0 errores (sin cambios en código) |
| pytest | 199 passed (sin cambios en tests) |
| Working tree | Limpio |

## Do-not-change respetado

- [x] No se modificó código fuente
- [x] No se modificaron tests
- [x] No se modificó `pyproject.toml`
- [x] No se modificaron specs de Fase 2 ni Fase 1
- [x] Solo docs de proceso + archivo de artifacts existentes

## Próximo paso

Fase 3 del roadmap. Base técnica firme: 199 tests, 91% coverage, 0 mypy, governance actualizado, working tree limpio.
