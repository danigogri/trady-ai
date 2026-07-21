#!/usr/bin/env python3
"""Discovery Clock guard — deterministic pre-session market rotation.

Reads ``TRADY_AI_ACTIVE_MARKETS`` from ``.env``, queries platform API per
Condition ID, applies frozen eligibility rules, takes the first valid market,
and updates ``.env`` if rotation is needed.

Exit codes:
    0 — at least one active market found (env updated if rotated).
    1 — no active markets found (session blocked).

This script is STANDALONE. It must NOT import from ``trady_ai``.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import urllib.request
import urllib.error
import json

# ── Frozen eligibility rules (set before Day 0, per AC-4 / AD-4) ────────
# These are deterministic boolean conditions. No ranking, no AI, no scoring.
_DOMAIN = "FOOTBALL-WINNER"
_PLATFORM_REST_URL = "https://clob.polymarket.com"
_REQUIRED_TAGS = {"football", "winner"}

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ensure_active_market")


# ── Helpers ──────────────────────────────────────────────────────────────


def _load_env(env_path: str = ".env") -> dict[str, str]:
    """Load ``.env`` file into a dict (simple parser, no ``python-dotenv``).

    Args:
        env_path: Path to ``.env`` file. Defaults to ``".env"`` in CWD.

    Returns:
        dict of env var name → value.
    """
    env: dict[str, str] = {}
    if not os.path.isfile(env_path):
        return env
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()
    return env


def _write_env(env_path: str = ".env", updates: dict[str, str] | None = None) -> None:
    """Write key=value updates into ``.env``, preserving comments and order.

    Idempotent: only replaces or adds the specified keys. Other lines
    (comments, unrelated vars) are preserved in their original positions.

    Args:
        env_path: Path to ``.env`` file.
        updates: Dict of key → value to upsert.
    """
    if not updates:
        return

    # Read existing lines
    lines: list[str] = []
    if os.path.isfile(env_path):
        with open(env_path) as f:
            lines = f.readlines()

    # Build a set of keys we want to update
    update_keys = set(updates.keys())
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.partition("=")[0].strip()
        if key in update_keys:
            new_lines.append(f"{key}={updates[key]}\n")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    # Append any keys that weren't found in the file
    for key in update_keys - updated_keys:
        new_lines.append(f"{key}={updates[key]}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


def _query_market(market_id: str) -> dict | None:
    """Query ``GET /markets/{id}`` and return parsed JSON, or ``None`` on error.

    Args:
        market_id: Polymarket Condition ID.

    Returns:
        Market JSON dict, or ``None`` if the market is not found (404) or
        the request fails.
    """
    url = f"{_PLATFORM_REST_URL}/markets/{market_id}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.info("market_not_found", market_id=market_id)
            return None
        logger.warning("market_query_error", market_id=market_id, status=e.code)
        return None
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logger.warning("market_query_failed", market_id=market_id, error=str(e))
        return None


def _is_market_expired(market: dict | None) -> bool:
    """Check if a market response indicates expiration.

    A market is expired if:
    - The API returns ``None`` (404).
    - The response has ``closed=True``.

    Args:
        market: Market JSON dict, or ``None`` (from 404).

    Returns:
        ``True`` if the market is expired.
    """
    if market is None:
        return True
    return bool(market.get("closed", False))


def _query_all_markets() -> list[dict]:
    """Query ``GET /markets`` and return all active markets.

    Returns:
        List of market JSON dicts. Empty on error.
    """
    url = f"{_PLATFORM_REST_URL}/markets"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("data", data.get("markets", []))
            return []
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logger.error("markets_query_failed", error=str(e))
        return []


def _check_eligibility(market: dict) -> bool:
    """Apply frozen eligibility rules to a market.

    A market is eligible if:
    - ``active`` is ``True``.
    - ``closed`` is ``False``.
    - ``tags`` contain ALL required tags (``football``, ``winner``).

    Args:
        market: Market JSON dict.

    Returns:
        ``True`` if the market passes all frozen rules.
    """
    if not market.get("active", False):
        return False
    if market.get("closed", False):
        return False

    tags = market.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip().lower() for t in tags.split(",")]
    if isinstance(tags, list):
        tags = [str(t).strip().lower() for t in tags]

    return _REQUIRED_TAGS.issubset(set(tags))


def _get_market_id(market: dict) -> str:
    """Extract the Condition ID from a market response.

    Tries ``condition_id``, ``id``, or ``market_id`` fields.
    """
    return str(
        market.get("condition_id")
        or market.get("id")
        or market.get("market_id", "")
    )


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    """Execute the guard logic.

    Returns:
        0 if at least one active market exists.
        1 if no active markets found.
    """
    env = _load_env()
    raw = env.get("TRADY_AI_ACTIVE_MARKETS", "").strip()
    current_ids = [
        m.strip() for m in raw.split(",") if m.strip()
    ] if raw else []

    if not current_ids:
        logger.info("no_markets_configured_attempting_discovery")

    # ── Phase 1: Check current markets ───────────────────────────────────
    expired_ids: list[str] = []
    active_ids: list[str] = []

    for mid in current_ids:
        market = _query_market(mid)
        if _is_market_expired(market):
            expired_ids.append(mid)
            logger.info("market_expired", market_id=mid)
        else:
            active_ids.append(mid)
            logger.info("market_active", market_id=mid)

    # ── Phase 2: Rotation if needed ──────────────────────────────────────
    if expired_ids and not active_ids:
        logger.info("all_markets_expired_attempting_rotation")
        all_markets = _query_all_markets()
        candidates = [m for m in all_markets if _check_eligibility(m)]

        if not candidates:
            logger.error("no_eligible_markets_found")
            return 1

        # Take the FIRST valid market (deterministic, no ranking)
        replacement = candidates[0]
        new_id = _get_market_id(replacement)
        logger.info(
            "ROTATION",
            extra={
                "expired": ",".join(expired_ids),
                "new_market": new_id,
            },
        )
        logger.info(
            "market_rotated %s -> %s",
            expired_ids[0] if expired_ids else "(none)",
            new_id,
        )

        _write_env(
            ".env",
            {"TRADY_AI_ACTIVE_MARKETS": new_id},
        )

        logger.info(
            "env_updated",
            extra={"active_markets": new_id},
        )
        return 0

    # ── Phase 3: At least one active market remains ──────────────────────
    if active_ids:
        logger.info(
            "active_markets_found",
            extra={"count": len(active_ids), "markets": active_ids},
        )
        return 0

    # ── No markets configured and no discovery possible ───────────────────
    if not current_ids:
        # Try initial discovery
        all_markets = _query_all_markets()
        candidates = [m for m in all_markets if _check_eligibility(m)]
        if candidates:
            new_id = _get_market_id(candidates[0])
            _write_env(".env", {"TRADY_AI_ACTIVE_MARKETS": new_id})
            logger.info("initial_market_discovered", market_id=new_id)
            return 0
        logger.error("no_markets_available_for_discovery")
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
