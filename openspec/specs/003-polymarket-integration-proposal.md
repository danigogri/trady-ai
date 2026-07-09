# Proposal: Polymarket Integration (Fase 2)

**Roadmap Phase**: 2 | **Motivado por**: RFC-002, RFC-000

## Core Principles

Idénticos a 002: Deterministic Execution, Replayability, Auditability, Fail Fast & Fail Loud, Low Coupling. Adapters traducen estructura, nunca son dueños de significado (RFC-002).

## Intent

Ejecutar órdenes GTC Limit en Polymarket via Event Store. Toda interacción externa → SQLite append-only antes de llegar al core. Aislamiento total de volatilidad externa.

## Scope

### ✅ In Scope
- Event Store: tabla `event_store`, append-only, dedup `event_id UNIQUE`, REST gap fill
- PolymarketAdapter + EventCapture en `adapters/polymarket.py`
- HTTPX directo REST+WS (sin SDKs)
- WS en `threading.Thread`, core sync, async aislado en boundary
- N mercados configurables (start: 1). Solo GTC Limit
- 2 iteraciones: dry_run → live, misma arquitectura

### ❌ Out of Scope
- Otras plataformas (Fase 3+). Stop/take profit desde adapter.

### 🚫 Non Goals
- Market making. Smart contracts. Multi-platform.

## Capabilities

### New
- `polymarket-adapter`: PolymarketAdapter traduce APIs externas → contratos internos. EventCapture orquesta capture → persist → reply.
- `event-store`: SQLite `event_store` (event_id UNIQUE, seq PK AUTOINCREMENT, event_type, payload, status, error_info). Append-only.

### Modified
- `002-deterministic-core`: Core expone contracts. Pipeline determinístico NO cambia.

## Approach

```
Polymarket → HTTPX → EventCapture → event_store (SQLite) → core contracts → Engine
```

WS en thread separado. Event loop contenido en adapter. Core recibe datos sincrónicos. Reconnect: REST gap fill desde último `seq`. Dedup: `event_id UNIQUE`. **dry_run**: pipeline corre sin firmar.

## Affected Areas

| Area | Impact |
|------|--------|
| `adapters/polymarket.py` | New |
| `core/persistence.py` | +event_store table |
| `pyproject.toml` | +`websockets>=13.0` |
| `config/settings.py` | +Polymarket secrets, WS config, markets list |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| WS disconnect | Medium | REST gap fill desde último seq |
| API contract change | Low | Adapter aísla. Core intacto |

## Rollback

1. Detener WS thread.
2. Eliminar `adapters/polymarket.py`.
3. Revertir persistence.py, settings.py, pyproject.toml.
4. Verificar `status` y `backtest` funcionan.

## Dependencies

- `websockets>=13.0` (nuevo)
- Bootstrap 001 + Core 002 completados

## Success Criteria

- [ ] Mismo evento → mismo registro en event_store (reproducible)
- [ ] Dedup: event_id duplicado → UNIQUE lo rechaza
- [ ] WS reconexión: REST gap fill desde último seq
- [ ] dry_run: pipeline corre sin firmar
- [ ] N mercados configurables sin tocar código
