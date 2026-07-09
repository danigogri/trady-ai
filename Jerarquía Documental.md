# Jerarquía Documental del Sistema Operacional

## NIVEL 0 — FILOSOFÍA / IDENTIDAD DEL SISTEMA

### Máxima autoridad conceptual

### Cambia muy poco

### Define cómo piensa el sistema

* PROJECT-SYSTEM-OPERATING.md
* SOURCE-OF-TRUTH.md

Definen:

* filosofía operacional
* principios rectores
* metodología
* governance global
* modelo mental del sistema
* reglas madre

---

# NIVEL 1 — DIRECCIÓN ESTRATÉGICA

### Define qué se construye

### Alto nivel

### Cambia lentamente

* ROADMAP.md
* MASTER ROADMAPS
* EXECUTION STRATEGY docs

Definen:

* fases
* checkpoints
* dependencias
* secuencia de ejecución
* visión macro del proyecto

---

# NIVEL 2 — ARQUITECTURA Y DOCTRINA

### Define cómo debe estructurarse el sistema

### Arquitectura conceptual

### Gobernanza estructural

* RFC-*.md

Definen:

* contratos conceptuales
* responsabilidades
* ownership
* límites entre capas
* invariantes arquitectónicos
* restricciones doctrinales
* vocabulario oficial

NO definen implementación exacta.

---

# NIVEL 3 — DISEÑO TÉCNICO

### Define cómo implementar exactamente

### Mucho más técnico

### Más mutable que RFC

* SDD-*.md
* TECHNICAL-DESIGN docs

Definen:

* pseudocódigo
* algoritmos
* métodos
* contratos exactos
* taxonomías
* output contracts
* lifecycle transitions
* estructuras internas

Aquí ya vive la implementación teórica.

---

# NIVEL 4 — GOBERNANZA OPERACIONAL

### Sincroniza realidad vs doctrina

### Mantiene coherencia histórica

* GOVERNANCE-SYNC-*.md
* HANDOFF-RECONCILIATION-*.md
* DRIFT-REVIEWS
* RECONCILIATION docs

Definen:

* correcciones doctrinales
* reconciliación entre documentos
* neutralización de drift
* sincronización entre fases
* aclaraciones append-only
* continuidad operacional

---

# NIVEL 5 — VALIDACIÓN Y EVIDENCIA

### Realidad empírica del sistema

### Evidence-bound

### Observacional

* VALIDATION reports
* PARSER-VALIDATION-REPORT-*.md
* EMPIRICAL ANALYSIS docs
* STRUCTURE ANALYSIS docs

Definen:

* hallazgos reales
* evidencia empírica
* riesgos observados
* anomalías
* límites de validación
* viabilidad estructural

NO son implementación.
NO son doctrina congelada todavía.

---

# NIVEL 6 — IMPLEMENTACIÓN OPERACIONAL

### Continuidad viva de ejecución

### Muy mutable

### Orientado a chats y ciclos de trabajo

* IMPLEMENTATION-SNAPSHOT-*.md
* EXECUTION-NOTES
* STABILIZATION PATCH docs
* CYCLE reports
* IMPLEMENTATION PLANS

Definen:

* continuidad de implementación
* reasoning comprimido
* estado operacional
* riesgos activos
* handoffs
* contexto quirúrgico para nuevos chats

---

# NIVEL 7 — ESTADO HISTÓRICO CONGELADO

### Fuente histórica validada

### Muy estable

### Auditado

* FREEZE-*.md
* CLOSURE-AUDITS
* FINAL-AUDITS
* RELEASE snapshots

Definen:

* estado oficialmente validado
* baseline histórico
* cierre de fases
* freeze-grade verification
* auditoría final
* autorización de continuidad

---

# NIVEL 8 — BITÁCORA OPERACIONAL

### Tracking histórico vivo

### Alta frecuencia de actualización

* EXECUTION-LEDGER.md
* DAILY LOGS
* SESSION LOGS
* CHANGE TRACKERS

Definen:

* cronología operacional
* decisiones tomadas
* lineage de implementación
* milestones
* commits históricos
* transición entre fases

---

# RESUMEN RÁPIDO

| Nivel | Documento                          | Rol                        |
| ----- | ---------------------------------- | -------------------------- |
| 0     | Operating System / Source of Truth | Filosofía madre            |
| 1     | Roadmap                            | Qué construir              |
| 2     | RFC                                | Cómo debe estructurarse    |
| 3     | SDD                                | Cómo implementarlo         |
| 4     | Governance / Reconciliation        | Mantener coherencia        |
| 5     | Validation Reports                 | Validar realidad           |
| 6     | Snapshots / STB                    | Continuidad operacional    |
| 7     | Freeze Audits                      | Estado histórico congelado |
| 8     | Execution Ledger                   | Bitácora viva              |

---

# REGLA OPERACIONAL IMPORTANTE

Mientras más arriba está un documento:

* más abstracto
* más estable
* menos frecuente su modificación
* mayor autoridad conceptual tiene

Mientras más abajo:

* más operativo
* más específico
* más mutable
* más cercano al trabajo diario

---

# PRINCIPIO CENTRAL

La implementación NO debe gobernar la arquitectura.

La arquitectura debe gobernar la implementación.

Y la evidencia empírica debe validar
si la arquitectura realmente sobrevive contacto con realidad.
