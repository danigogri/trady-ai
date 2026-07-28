# BACKLOG PROTOCOL v1

## Propósito
Establecer un sistema estricto de control de bugs, mejoras y deuda técnica durante el desarrollo de proyectos, evitando desviaciones de alcance, complejidad emergente y pérdida de control del sistema.


---

## 1. Principio Fundamental

> Ningún problema detectado fuera del alcance actual se resuelve inmediatamente.

Todo hallazgo se registra. Solo se trabaja lo explícitamente solicitado.

---

## 2. Alcance Estricto

Claude debe:

- Trabajar únicamente en el objetivo definido en el prompt activo
- Evitar cualquier modificación fuera de ese alcance

Antes de realizar cualquier cambio:

- Validar si pertenece al scope actual
- Si no pertenece → PROHIBIDO modificar

---

## 3. Detección de Hallazgos

Se consideran hallazgos:

- Bugs
- Inconsistencias
- Deuda técnica
- Problemas de arquitectura
- Oportunidades de mejora estructural

Regla:

- NO solucionar
- NO modificar código relacionado
- SOLO registrar en backlog

---

## 4. Estructura de BACKLOG.md

El archivo debe mantener este orden:

1. Título
2. Sección de items (ordenados por ID ascendente)
3. Sección final: ## 🧠 NOTAS

Reglas:

- Los items NO se agrupan por tipo o severidad
- NO reordenar manualmente
- NO eliminar items históricos
- Los IDs son permanentes
---

## 5. Registrar en D:\dev\Trady.AI

Formato obligatorio (una línea por item):


[BL-XXX] | tipo | severidad | módulo | descripción corta | estado


### Tipos válidos:
- bug
- mejora
- deuda

### Severidad:
- crítica → rompe flujo principal
- alta → degrada funcionalidad clave
- media → problema funcional no crítico
- baja → UX / optimización

---

## 5.1 Estados válidos

Cada item del backlog debe incluir un estado operativo.

Estados válidos:

- abierto
- en_progreso
- bloqueado
- resuelto
- descartado

Reglas:

- Todo hallazgo nuevo inicia como `abierto`
- Solo el trabajo activo puede marcarse `en_progreso`
- `bloqueado` requiere dependencia externa o impedimento crítico
- `resuelto` implica fix implementado y validado
- `descartado` implica decisión explícita de no implementación

---

## 6. Ejemplos de Registro


[BL-001] | bug | crítica | websocket_handler.py | conexión se cierra antes de completar streaming | abierto
[BL-002] | deuda | alta | launcher/index.js | stop() no garantiza cierre completo de procesos | resuelto
[BL-003] | mejora | media | frontend/settings | ruta no implementada (404) | descartado


---

## 7. Control de Cambios

Antes de modificar cualquier archivo:

1. ¿Este cambio fue solicitado explícitamente?
   - Sí → permitido
   - No → prohibido

2. Si el cambio surge de un hallazgo:
   - Registrar en backlog
   - NO implementar

---

## 8. Reporte Obligatorio

Al finalizar cada tarea, debe entregar:

- Cambios realizados
- Archivos modificados
- Nuevos items en backlog (si aplica)
- Confirmación explícita:


Sin cambios fuera de alcance


---

## 9. Prohibiciones

Queda estrictamente prohibido:

- Refactors no solicitados
- Fixes oportunistas
- Mejoras implícitas
- Optimizaciones fuera de scope
- Cambios preventivos

---

## 10. Activación del Protocolo


El BACKLOG-PROTOCOL se activa en dos modos:

1. ACTIVACIÓN AUTOMÁTICA (por auditor o implementator chat/agente)
el DEBE activar el protocolo sin intervención del usuario cuando detecte:

- Errores runtime (exceptions, crashes, loops)
- Bugs de integración (frontend ↔ backend, WS, timeouts)
- Comportamientos inconsistentes
- Fallos reproducibles reportados por el usuario
- Features incompletas o endpoints faltantes (ej: 404)

2. ACTIVACIÓN MANUAL (por el usuario)
El usuario puede forzar activación con:

BACKLOG-PROTOCOL — ACTIVAR

Una vez activado, el auditor o implementator chat/agente debe registrar el bug antes de proponer o ejecutar cualquier solución.

---

## 11. Relación con source of truth and roadmaps.md

Este protocolo:

- Complementa
- No reemplaza reglas existentes
- Introduce control de ejecución y disciplina técnica

---

## 12. Objetivo Operativo

- Maximizar velocidad de desarrollo
- Evitar deriva técnica
- Mantener trazabilidad completa
- Permitir priorización inteligente
- Reducir regresiones

---

## 13. Control de Duplicados

Antes de registrar un nuevo item, el auditor o implementator chat/agente debe:

1. Revisar BACKLOG.md
2. Verificar si el problema ya existe

Si existe:

- NO crear un nuevo ID
- Opcional: enriquecer descripción existente (si es necesario)

Si no existe:

- Crear nuevo [BL-XXX]

Duplicados están prohibidos.

---

## 14. Sección NOTAS en BACKLOG.md

El archivo BACKLOG.md puede contener una sección adicional:

## 🧠 NOTAS

Propósito:
- Definir prioridades globales
- Establecer restricciones de enfoque
- Dar contexto estratégico al sistema

Reglas:

- NO son items de backlog
- NO usan formato [BL-XXX]
- NO se deben ejecutar como tareas
- NO generan cambios de código directamente

Claude debe:

- Usarlas como guía de priorización
- NO registrarlas como bugs/mejoras
- NO ignorarlas si afectan decisiones de ejecución

En caso de conflicto:
- Las NOTAS tienen prioridad sobre decisiones implícitas de Claude
- Pero NO sobre instrucciones explícitas del usuario

---

## 15. Manejo de Severidad Crítica

Si se detecta un item con severidad "crítica":

- Evaluar si bloquea el objetivo actual
- Si NO bloquea → registrar y continuar
- Si SÍ bloquea → detener ejecución y reportar inmediatamente

No asumir bloqueo sin validación explícita.
---

## 16. Archivado de Items Resueltos

El archivo `BACKLOG.md` representa únicamente el backlog operativo activo del sistema.

Los items con estado:

- resuelto
- descartado

deben ser movidos periódicamente a:

D:\dev\Trady.AI\archive\BACKLOG-YYYY-QX.md

Convención obligatoria de nombre:

- YYYY → año actual
- QX → trimestre actual del año

Ejemplos:
- BACKLOG-2026-Q1.md  → enero-marzo 2026
- BACKLOG-2026-Q2.md  → abril-junio 2026
- BACKLOG-2026-Q3.md  → julio-septiembre 2026
- BACKLOG-2026-Q4.md  → octubre-diciembre 2026

Regla:
El nombre del archivo debe representar el período en el que los items fueron archivados, no cuando fueron creados originalmente.

Reglas:

- NO eliminar historial de bugs
- Mantener trazabilidad completa
- El backlog principal debe permanecer compacto y operativo
- Los items archivados conservan su ID original

Claude NO debe archivar items automáticamente salvo instrucción explícita del usuario.

El archivado existe para:
- reducir ruido operativo
- minimizar consumo de contexto
- mantener foco en problemas activos
- preservar historial técnico del sistema

## Regla operacional:

Los items pueden permanecer temporalmente como `resuelto`
dentro de `BACKLOG.md` hasta que el usuario solicite archivado.

Esto permite validar estabilidad post-fix antes de moverlos al histórico.

---

## 17. Nota Final

Este protocolo no busca ralentizar el desarrollo, sino hacerlo controlado, predecible y escalable.

La disciplina en su uso es obligatoria para mantener la estabilidad del sistema Pythy.