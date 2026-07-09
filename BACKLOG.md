# BACKLOG — TRADY.AI

> Generado desde BACKLOG-PROTOCOL v1
> Auditoría inicial: 2026-07-09
> Última actualización: 2026-07-09

---

[BL-001] | deuda | media | models.py | `__init__` en Signal, Position, Trade sin type annotations (3 ocurrencias: líneas 44, 67, 90) | abierto
[BL-002] | deuda | media | engine.py, observability.py, risk.py | Tipos genéricos sin argumentos: `list`, `dict` sin `list[...]` / `dict[..., ...]` (7 ocurrencias) | abierto
[BL-003] | deuda | media | markov_strategy.py, position_manager.py, engine.py | Llamadas a constructores no tipados (Signal, Position, Trade, PositionManager) que mypy no puede verificar (7 ocurrencias) | abierto
[BL-004] | deuda | alta | persistence.py | `sqlite_utils.Database.__getitem__` retorna `Table | View`, mypy no reconoce `.insert()` en tipos unión (5 ocurrencias: líneas 88, 103, 120, 139, 165) | abierto
[BL-005] | bug | alta | state.py, risk.py | Argumento `str` pasado donde se espera `Literal['UP','DOWN','NEUTRAL']` (state.py:50) y `Literal['OPEN_LONG','OPEN_SHORT','CLOSE','HOLD','REJECT']` (risk.py:109) | abierto
[BL-006] | deuda | alta | observability.py | Operaciones no seguras con `Decimal | None`: suma, comparación, conversión a `float` sin manejar el caso `None` (4 errores) | abierto
[BL-007] | deuda | baja | position_manager.py | `__init__` sin return type annotation (linea 16) | abierto

---

## 🧠 NOTAS

- **Prioridad**: BL-005 y BL-006 son los más riesgosos porque pueden ocultar errores en runtime (tipos incorrectos que pasan por alto). BL-004 es molesto pero no bloqueante.
- **Relación con Fase 2**: Antes de arrancar Polymarket integration conviene resolver al menos BL-005 y BL-001, para que mypy esté limpio en código nuevo.
- **30 errores originales**: 17 son de tipado genérico (`type-arg`, `no-untyped-def`), 9 son de tipos incompatibles (`arg-type`, `operator`), 4 son de `union-attr` (sqlite_utils).
- **Resolución**: BL-001 requiere anotar `__init__` con `**data: Any` + `super().__init__(**data)`. BL-004 requiere `# type: ignore[union-attr]` o cast. BL-005 requiere casts explícitos o reificar los Literals.
