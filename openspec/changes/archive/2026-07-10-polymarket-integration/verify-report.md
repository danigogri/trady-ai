## Verification Report

**Change**: 003 — Polymarket Integration (Fase 2)
**Version**: Spec 1.0
**Mode**: Standard
**Commit**: `eee2999` — "wip: apply polymarket-integration Fase 2, unverified"
**Date**: 2026-07-09

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 14 |
| Tasks complete | 14 (all marked [x]) |
| Tasks incomplete | 0 |

### Build & Tests Execution

**mypy**: ❌ Failed — 19 errors
```text
src/trady_ai/core/persistence.py:215: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/core/persistence.py:305: error: Returning Any from function declared to return "int"  [no-any-return]
src/trady_ai/adapters/polymarket.py:72: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:84: error: Returning Any from function declared to return "list[dict[Any, Any]]"  [no-any-return]
src/trady_ai/adapters/polymarket.py:86: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:104: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/trady_ai/adapters/polymarket.py:106: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:124: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/trady_ai/adapters/polymarket.py:128: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:166: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/trady_ai/adapters/polymarket.py:168: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:185: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
src/trady_ai/adapters/polymarket.py:187: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:205: error: Returning Any from function declared to return "list[dict[Any, Any]]"  [no-any-return]
src/trady_ai/adapters/polymarket.py:209: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:231: error: Missing type arguments for generic type "Queue"  [type-arg]
src/trady_ai/adapters/polymarket.py:294: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:320: error: Missing type arguments for generic type "dict"  [type-arg]
src/trady_ai/adapters/polymarket.py:439: error: Missing type arguments for generic type "dict"  [type-arg]
Found 19 errors in 2 files (checked 28 source files)
```

**ruff**: ✅ Passed — 0 errors
```text
All checks passed!
```

**Tests**: ✅ 195 passed, 0 failed, 0 skipped
```text
195 passed in 18.61s
```

**Coverage**: 89% / threshold (tasks.md): ≥80% → ✅ Above threshold
```
Name                                    Stmts   Miss  Cover
----------------------------------------------------------
src/trady_ai/adapters/polymarket.py       203     38    81%
src/trady_ai/cli/main.py                  147     39    73%
src/trady_ai/core/engine.py                63      3    95%
src/trady_ai/core/persistence.py           50      2    96%
... (all others ≥ 80%)
----------------------------------------------------------
TOTAL                                     882     94    89%
```

### Spec Compliance Matrix

#### Del Proposal (success criteria)
| Criterion | Test | Result |
|-----------|------|--------|
| Mismo evento → mismo registro (reproducible) | `test_capture_dedup`, `test_persistence_append_dedup` | ✅ COMPLIANT |
| Dedup: event_id duplicado → UNIQUE constraint, retorna None | `test_capture_dedup`, `test_persistence_append_dedup` | ✅ COMPLIANT |
| WS reconexión: REST gap fill desde último timestamp | `_handle_reconnect` implemented; no covering test | ❌ UNTESTED |
| dry_run: pipeline corre sin firmar, secrets vacíos OK | `test_validate_secrets_dry_run` (secrets.py), `test_runtime_config_execution_mode` | ✅ COMPLIANT |
| N mercados configurables sin tocar código | `test_settings_get_active_market_ids_parses_comma_separated` | ✅ COMPLIANT |

#### De la Spec (additional requirements)
| Requirement | Implementation Evidence | Result |
|-------------|------------------------|--------|
| PolymarketAdapter 100% stateless — no mutable state attributes | Class has no mutable state; all methods are translations | ✅ COMPLIANT |
| EventCapture aísla async (WS thread) del core sync | `threading.Thread` with daemon flag, `_run_loop` in thread | ✅ COMPLIANT |
| event_store append-only — no UPDATE, solo INSERT OR IGNORE | `append_event` uses `INSERT OR IGNORE` | ✅ COMPLIANT |
| `run_from_store` delegates to `run()` — core pipeline unchanged | engine.py: `self.run(inputs, strategy)` | ✅ COMPLIANT |
| Core module NO importa de adapters — isolation boundary | engine.py imports only core.*, config.*, db.* | ✅ COMPLIANT |
| `validate_secrets` solo se invoca cuando execution_mode == "live" | `validate_polymarket_secrets` checks mode — but NEVER CALLED from CLI | ⚠️ PARTIAL |
| Secrets nunca en logs, status output, o error messages | status command does not output any secret field; no leak in code | ✅ COMPLIANT |
| `websockets>=13.0` agregado a pyproject.toml | pyproject.toml line 16 | ✅ COMPLIANT |
| CLI `capture` command starts WS, persists to event_store | main.py: capture command implemented | ✅ COMPLIANT |
| CLI `capture --reset` drops event_store (dev only) | main.py: `capture_obj.reset()` on --reset flag | ✅ COMPLIANT |
| CLI `run --market X` consumes from event_store | main.py: run command → `engine.run_from_store(...)` | ✅ COMPLIANT |
| CLI `status` shows event_store stats + capture state | Shows event_count and max_seq; missing capture state & execution mode | ⚠️ PARTIAL |
| Todos los tests unitarios pasan (≥ 29 nuevos) | ~66 new test methods across 7 new test files; all pass | ✅ COMPLIANT |
| Todos los tests de integración pasan (≥ 6 nuevos) | 4 in integration file + 2 CLI scenario tests = 6; `test_reconnect_gap_fill` missing from spec list | ⚠️ PARTIAL |
| `ruff check .` sin errores | 0 errors | ✅ COMPLIANT |
| `mypy src/` sin errores en código nuevo | 19 errors in new/modified code | ❌ FAILING |

#### Invariantes Arquitectónicos (RFC-002, RFC-000)
| Invariant | Evidence | Result |
|-----------|----------|--------|
| Adapters traducen estructura, NUNCA poseen significado | PolymarketAdapter methods are pure translations | ✅ COMPLIANT |
| Core NO depende de adapters — inversión via persistence | engine.py imports from core.persistence, not adapters | ✅ COMPLIANT |
| No hidden retries en adapter — fail-fast propagated | Methods call `raise_for_status()` directly; no retry in adapter | ✅ COMPLIANT |
| No silent normalization — adapter maps structure, not semantics | `market_to_input` maps fields explicitly | ✅ COMPLIANT |
| Async aislado en infrastructure boundary (WS thread) | WS in daemon thread with dedicated asyncio loop | ✅ COMPLIANT |
| Core pipeline remains 100% sync and deterministic | `run()` and `run_from_store()` are sync | ✅ COMPLIANT |
| Secrets governance: no leakage | No secret fields in status/log output | ✅ COMPLIANT |
| Blast radius: adapter failure does not corrupt core tables | Adapter uses separate db connection, no core table writes | ✅ COMPLIANT |
| Rollback: eliminar adapters/ + revertir persistence/settings/pyproject | All changes are self-contained in listed files | ✅ COMPLIANT |

**Compliance summary**: 16/22 ✅ COMPLIANT, 3/22 ⚠️ PARTIAL, 2/22 ❌ UNTESTED/FAILING, 1/22 ❌ FAILING

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|-------------|--------|-------|
| PolymarketAdapter — REST methods | ✅ Implemented | 6 methods with httpx.Client sync |
| PolymarketAdapter — WS subscribe_websocket | ✅ Implemented | Async bridge via new_event_loop + asyncio.Queue |
| PolymarketAdapter — market_to_input | ✅ Implemented | Pure function, KeyError on missing keys |
| PolymarketAdapter — order_to_trade | ✅ Implemented | Pure function, OPEN/CLOSE mapping |
| EventCapture — start/stop lifecycle | ✅ Implemented | Daemon thread with flag + join |
| EventCapture — _capture_one | ✅ Implemented | Translates, generates event_id, dedup via append_event |
| EventCapture — _handle_reconnect | ⚠️ Partial | Simplified: fetches current market data, not historical gap fill per spec |
| EventCapture — reset() dev guard | ✅ Implemented | Checks environment != "development" |
| EventStore — schema + 6 functions | ✅ Implemented | All 6 functions present in persistence.py |
| Engine — run_from_store | ✅ Implemented | Delegates to run() |
| Settings — 6 Polymarket fields + get_active_market_ids | ✅ Implemented | All fields present |
| RuntimeConfig — execution_mode + default_order_type | ✅ Implemented | Both fields with Literal types |
| CLI — capture command | ✅ Implemented | --markets, --reset flags |
| CLI — run command | ✅ Implemented | --market, --since-seq flags; uses run_from_store |
| CLI — status command | ⚠️ Partial | Missing "Capture: running/stopped" and "Execution mode" |
| validate_secrets (existing in security/secrets.py) | ✅ Unchanged | Still takes single `settings` param |
| validate_polymarket_secrets (new in cli/main.py) | ⚠️ Partial | Function exists but NEVER CALLED from capture/run commands |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| WS library: `websockets` | ✅ Yes | Used in subscribe_websocket |
| HTTPX: sync Client for REST, async for WS | ✅ Yes | Sync httpx.Client, async websockets in new_event_loop |
| WS thread: threading.Thread (isolates async) | ✅ Yes | Daemon thread |
| Dedup: INSERT OR IGNORE | ✅ Yes | Used in append_event |
| raw_payload: TEXT (nullable) | ⚠️ Deviation | Design says `TEXT NOT NULL`; implementation has `raw_payload TEXT` (nullable) |
| Reconnect cursor: MAX(seq) → timestamp | ⚠️ Partial | Uses MAX(seq) but gap fill fetches current data, not historical since timestamp |
| EventCapture error property | ✅ Yes | `_error` attribute with property accessor |
| dev-only reset guard | ✅ Yes | Checks settings.environment |
| run_from_store delegates to run() | ✅ Yes | engine.py line 168-169 |
| Core does NOT import adapters | ✅ Yes | Verified |
| Async isolated in thread boundary | ✅ Yes | Daemon thread with own event loop |
| structlog for all logging | ✅ Yes | logger calls throughout |

### Issues Found

**CRITICAL**:
1. **mypy: 19 errors in new code** — `persistence.py` (2 errors) and `polymarket.py` (17 errors). All are `type-arg` and `no-any-return` on untyped generic `dict`, `list`, and `Queue` annotations. The spec acceptance criteria require "mypy src/ sin errores en código nuevo."
2. **apply-progress.md line 6 falsely claims "mypy: 0 new"** — The apply-progress reports "ruff: 0 | mypy: 0 new" when there are 19 mypy errors. This is a factual inaccuracy in the progress report that masks a known issue.
3. **`validate_polymarket_secrets()` is defined but NEVER CALLED** — The spec Module 9 Integration Points require both `trady-ai capture` and `trady-ai run` to call `validate_secrets` before executing. Neither CLI command invokes the function. In dry_run mode this is a no-op, but in live mode it would fail to enforce pre-execution validation.
4. **No tests for `validate_polymarket_secrets`** — The function has zero test coverage. The existing `test_security.py` tests the original `validate_secrets(settings)` from `security/secrets.py`, not the new polymarket-specific one.

**WARNING**:
1. **Status command incomplete** — Missing "Capture: running/stopped" and "Execution mode: dry_run/live" from output (spec Module 7 requirement).
2. **`validate_polymarket_secrets` naming** — Spec Module 9 defines `validate_secrets(settings, execution_mode)`, but implementation uses `validate_polymarket_secrets(settings: Any, execution_mode: str)` and places it in `cli/main.py` rather than a security module. Naming and placement deviate from spec.
3. **Integration test `test_reconnect_gap_fill` missing** — Spec lists this as a required integration test. The `_handle_reconnect` path is untested.
4. **REST gap fill simplified** — Design spec says "REST fetch events since last timestamp" but implementation fetches current market data only (`get_market_data`). Historical event fetching is not implemented.
5. **`raw_payload` nullable vs NOT NULL** — Design specifies `raw_payload TEXT NOT NULL`; implementation has `raw_payload TEXT` (nullable). Minor schema deviation.

**SUGGESTION**:
1. **append_event uses raw SQL** — Design.md showed `db["event_store"].insert(...)` with `sqlite_utils.db.IntegrityError` catch, but implementation uses raw `INSERT OR IGNORE` with cursor. Either approach works, but inconsistency with design.
2. **run command hardcodes dry_run=True** — Should eventually respect `config.execution_mode` for live mode; currently always runs as dry_run.
3. **WS retry uses broad `except Exception`** — In `_run_loop`, all exceptions trigger retry logic. Could be more specific (e.g., `(ConnectionError, httpx.RemoteProtocolError)` as design suggests).

### Apply-Progress Consistency Check

| Claim in apply-progress.md | Reality | Status |
|----------------------------|---------|--------|
| "Tests: 195 passed" | 195 passed ✅ | CONSISTENT |
| "Coverage: 89%" | 89% ✅ | CONSISTENT |
| "ruff: 0" | 0 errors ✅ | CONSISTENT |
| "mypy: 0 new" | 19 errors ❌ | **INCONSISTENT — FALSE** |
| "4 PRs stacked-to-main" | 1 WIP commit, no PRs; code structure matches | N/A (local apply) |
| "All 14 tasks marked complete [x]" | All [x] in tasks.md; 3 tasks have partial implementation | MOSTLY CONSISTENT |
| "12 architectural decisions honored" | 10/12 fully; 2 have minor deviations | MOSTLY CONSISTENT |
| "Deviations from Design: None" | raw_payload nullable, simplified gap fill | **INCONSISTENT** |

### Verdict

**FAIL** — fixes required before archive.

The combination of 19 mypy errors (all in new code), a false claim in apply-progress, untested `validate_polymarket_secrets` that is defined but never called, and the incomplete status command output collectively constitute a FAIL. The spec explicitly requires "mypy src/ sin errores en código nuevo" (acceptance criteria line 1222), which is not met.

The core architecture and most implementation decisions are sound — the issues are in type safety, verification accuracy, and edge case completion. These are fixable without architectural rework.

**Next**: Loop to triage — fix mypy errors, call validate_polymarket_secrets from CLI commands, add missing tests, correct apply-progress, and add capture state to status command.
