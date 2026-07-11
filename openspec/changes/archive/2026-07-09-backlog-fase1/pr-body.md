## Resumen

Resolución completa del backlog de Fase 1 (Deterministic Core) de Trady.AI.

Se resolvieron **8 items** (BL-001 a BL-008) que totalizaban **30 errores de mypy** en 8 archivos del core. La Fase 1 queda oficialmente limpia: tipado estricto sin `Any` desnudos y sin supresiones más allá de las 5 necesarias para `sqlite_utils` (`# type: ignore[union-attr]`).

BL-008 fue un **hallazgo colateral** detectado durante el fix de BL-002: al parametrizar tipos genéricos (`list` → `list[Signal]`, etc.) en `ExecutionResult`, mypy expuso un quirk de inference por reuso de nombres de variables de loop en `verify_replay`. Sin este fix, BL-002 habría introducido 6 errores nuevos en un archivo que estaba limpio.

## Cambios por BL

| BL | Tipo | Archivo(s) | Cambio |
|----|------|------------|--------|
| BL-005 | bug | `state.py`, `risk.py` | `cast(Literal[...])` para `MarketState.state` y `ExecutionDecision.action` — `str` → `Literal` |
| BL-006 | deuda | `observability.py` | Extrae lista `pnls` tipada para narrowear `Decimal` (mypy no propaga `is not None` por list-comprehensions) |
| BL-004 | deuda | `persistence.py` | `# type: ignore[union-attr]` en 5 llamadas `db["..."].insert()` (`Table | View`) |
| BL-001 | deuda | `models.py` | `**data: Any -> None` en `__init__` de `Signal`, `Position`, `Trade` |
| BL-003 | deuda | — | **Auto-resuelto por BL-001** (calls tipados a constructores en `markov_strategy.py`, `position_manager.py`, `engine.py`) |
| BL-002 | deuda | `engine.py` | `list[X]` / `dict[str, Any]` parametrizados en `ExecutionResult` dataclass |
| BL-007 | deuda | `position_manager.py` | `-> None` en `PositionManager.__init__` |
| BL-008 | deuda | `replay.py` | Renombra vars de loop `a/b` → `dec_a/dec_b`, `sig_a/sig_b`, `trd_a/trd_b` para mypy narrowing (colateral de BL-002) |

## Verification gates

| Gate | Resultado |
|------|-----------|
| `mypy src/` | `Success: no issues found in 27 source files` |
| `ruff check src/` | `All checks passed!` |
| `pytest` | `117 passed in 13.96s` |
| Coverage | `97%` (559 statements, 17 missing) |

## Do-not-change respetado

- [x] No se modificó la lógica de negocio ni algoritmos
- [x] No se cambió la estructura de datos (modelos Pydantic)
- [x] No se renombraron funciones, clases o módulos
- [x] No se modificaron tests existentes
- [x] No se cambió `pyproject.toml` ni configuraciones de herramientas
- [x] No se tocó `openspec/` (el spec de Fase 2 sigue sin commitear en otra rama)
- [x] No se modificó el spec de Fase 2 (`003-polymarket-integration-spec.md`)

## Notas

- Cambios triviales (annotations, casts, type:ignore, renombres de vars locales) aplicados en rama única `deuda/backlog-fase1`. No se usaron branches aisladas por BL porque 3 archivos están tocados por BLs que dependen entre sí (`risk.py`, `engine.py`, `observability.py`); branches aisladas habrían generado conflictos de merge.
- Diferencia neta: `+40 / -35` líneas, sin nuevo código ni lógica.