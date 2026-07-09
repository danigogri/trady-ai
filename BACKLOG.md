# BACKLOG — TRADY.AI

> Generado desde BACKLOG-PROTOCOL v1
> Auditoría inicial: 2026-07-09
> Última actualización: 2026-07-09

---

[BL-001] | deuda | media | models.py | `__init__` en Signal, Position, Trade sin type annotations (3 ocurrencias) | ✅ resuelto
[BL-002] | deuda | media | engine.py, observability.py, risk.py | Tipos genéricos sin argumentos: `list`, `dict` sin parámetros de tipo (7 ocurrencias) | ✅ resuelto
[BL-003] | deuda | media | markov_strategy.py, position_manager.py, engine.py | Llamadas a constructores no tipados (Signal, Position, Trade, PositionManager) que mypy no puede verificar (7 ocurrencias) | ✅ resuelto (desbloqueado por BL-001)
[BL-004] | deuda | alta | persistence.py | `sqlite_utils.Database.__getitem__` retorna `Table | View`, mypy no reconoce `.insert()` en tipos unión (5 ocurrencias) | ✅ resuelto (# type: ignore[union-attr])
[BL-005] | bug | alta | state.py, risk.py | Argumento `str` pasado donde se espera `Literal['UP','DOWN','NEUTRAL']` (state.py:50) y `Literal['OPEN_LONG','OPEN_SHORT','CLOSE','HOLD','REJECT']` (risk.py:109) | ✅ resuelto (cast explícito)
[BL-006] | deuda | alta | observability.py | Operaciones no seguras con `Decimal | None`: suma, comparación, conversión a `float` sin manejar el caso `None` (4 errores) | ✅ resuelto (filtro + type narrowing)
[BL-007] | deuda | baja | position_manager.py | `__init__` sin return type annotation (línea 16) | ✅ resuelto
[BL-008] | deuda | baja | replay.py | Errores colaterales de BL-002: variables de loop `a/b` reusadas entre tipos incompatibles (6 ocurrencias) | ✅ resuelto (renombrado a dec_a/dec_b, sig_a/sig_b, trd_a/trd_b)

---

## 🧠 NOTAS

- **Estado actual**: Fase 1 limpia. mypy: 0 errores (27 archivos). pytest: 117 pass. Coverage: 97%. Ruff: clean.
- **Próximo paso**: SDD cycle Fase 2 — Design → Tasks → Apply → Verify.
- **Lección aprendida**: cambios con riesgo de impacto colateral requieren Assessment Report + Documento Contrato antes de aplicar. Cambios triviales (renombres locales, annotations) pueden aplicarse directo con nota en commit.
