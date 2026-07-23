#!/usr/bin/env python3
r"""Discovery Clock guard — deterministic pre-session market rotation.

For football-winner markets, queries Polymarket's sports pages to discover
active games, then uses gamma-api to get the event with its markets.

Algorithm (per ARCHITECTURE-CONTRACT OC-2):
  1. Read TRADY_AI_ACTIVE_MARKETS from .env
  2. For each Condition ID:
     a. Query clob.polymarket.com/markets/{id}
     b. If closed == true OR not active -> mark as EXPIRED
  3. If ALL markets are EXPIRED:
     a. For each candidate league (mex, mls, epl, ...):
        - Fetch polymarket.com/sports/{league}/games
        - Extract slugs from HTML
        - For each slug, query gamma-api/events?slug={slug}
        - Take first "Will X win" market with active=True, closed=False
     b. If found -> write conditionId to .env, exit 0
     c. If not found -> exit 1 (fail-fast)
  4. If at least one market is still active -> exit 0 (no action)

DEVIATION FROM CONTRACT (documented 2026-07-22):
  Original contract assumed markets endpoint returns tags like ["football", "winner"].
  Reality: clob.polymarket.com/markets returns tags=["All"] (uninformative).
  Gamma-api /events does NOT filter by sport param. Sports markets only reachable
  via polymarket.com/sports/{league}/games (HTML) + gamma-api/events?slug={slug}.
  New eligibility filter: question matches "^Will .+ win on YYYY-MM-DD?$".

This script is STANDALONE. It must NOT import from trady_ai.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, cast

# ── Frozen eligibility rules (set before Day 0, per AC-4 / AD-4) ────────
# Deterministic boolean conditions. No ranking, no AI, no scoring.
_DOMAIN = "FOOTBALL-WINNER"
_USER_AGENT_API = "Mozilla/5.0 (compatible; trady-ai-discovery/1.0)"
_USER_AGENT_WEB = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Candidate leagues to try in order. Per /sports endpoint there are 30+
# leagues with soccer markets (mex, mls, epl, arg, bra, ucl, uel, etc.).
# Order matters: first league with an eligible market wins (no ranking).
#
# These are DEFAULTS — used when TRADY_AI_FOOTBALL_LEAGUES is not set in .env.
# Operator can override the list at review windows without code deploy (AD-5).
_DEFAULT_LEAGUES = [
    "mex",   # Liga MX
    "mls",   # Major League Soccer
    "epl",   # English Premier League
    "arg",   # Argentine Primera
    "bra",   # Brasileirão
    "ucl",   # UEFA Champions League
    "uel",   # UEFA Europa League
    "copa",  # Copa America
]

# "Will X win on YYYY-MM-DD?" — strict pattern for match-winner markets.
# Default; overridable via TRADY_AI_WINNER_PATTERN in .env.
_DEFAULT_WINNER_PATTERN = r"^Will .+ win on \d{4}-\d{2}-\d{2}\??$"
# Negative patterns (markets we DO NOT want).
# Defaults; overridable via TRADY_AI_REJECT_PATTERNS in .env (comma-separated).
_DEFAULT_REJECT_PATTERNS = [
    "end in a draw",
    "O/U",
    "over/under",
    "both teams to score",
    "handicap",
    "spread",
]

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ensure_active_market")


# ── HTTP helpers ─────────────────────────────────────────────────────────


def _http_get_json(url: str, timeout: int = 15) -> dict[str, Any] | list[Any] | None:
    """GET request returning parsed JSON, or None on error."""
    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT_API,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return cast(dict[str, Any] | list[Any], json.loads(resp.read().decode()))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logger.warning("http_get_failed", extra={"url": url, "error": str(e)})
        return None


def _http_get_html(url: str, timeout: int = 30) -> str | None:
    """GET request returning HTML text, or None on error."""
    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT_WEB,
        "Accept": "text/html",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return cast(str, resp.read().decode("utf-8", errors="ignore"))
    except (urllib.error.URLError, OSError) as e:
        logger.warning("http_get_failed", extra={"url": url, "error": str(e)})
        return None


# ── .env helpers ─────────────────────────────────────────────────────────


def _load_env(env_path: str = ".env") -> dict[str, str]:
    """Load .env file into a dict (simple parser, no python-dotenv)."""
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


def _write_env(env_path: str, updates: dict[str, str]) -> None:
    """Write key=value updates into .env, preserving comments and order."""
    if not updates:
        return

    lines: list[str] = []
    if os.path.isfile(env_path):
        with open(env_path) as f:
            lines = f.readlines()

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

    for key in update_keys - updated_keys:
        new_lines.append(f"{key}={updates[key]}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


# ── Discovery config (externalized per BL-029, AD-5) ─────────────────────


def _load_discovery_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Load discovery rules from .env, falling back to frozen defaults.

    Implements BL-029: externalize hardcoded discovery config to .env so the
    operator can adjust frozen rules at review windows without code deploy
    (per Architecture Contract AD-5).

    Args:
        env: Optional pre-loaded env dict. If None, calls _load_env().

    Returns:
        dict with keys:
          - leagues: list[str]            (TRADY_AI_FOOTBALL_LEAGUES)
          - winner_pattern: re.Pattern[str]  (TRADY_AI_WINNER_PATTERN)
          - reject_patterns: list[re.Pattern[str]]  (TRADY_AI_REJECT_PATTERNS)

    Raises:
        re.error: If TRADY_AI_WINNER_PATTERN is set but invalid regex.
    """
    if env is None:
        env = _load_env()

    # ── Leagues ──
    leagues_str = env.get("TRADY_AI_FOOTBALL_LEAGUES", "").strip()
    if leagues_str:
        leagues = [s.strip() for s in leagues_str.split(",") if s.strip()]
    else:
        leagues = list(_DEFAULT_LEAGUES)

    # ── Winner pattern ──
    winner_str = env.get("TRADY_AI_WINNER_PATTERN", "").strip()
    if not winner_str:
        winner_str = _DEFAULT_WINNER_PATTERN
    winner_pattern = re.compile(winner_str)

    # ── Reject patterns ──
    reject_str = env.get("TRADY_AI_REJECT_PATTERNS", "").strip()
    if reject_str:
        reject_raw = [s.strip() for s in reject_str.split(",") if s.strip()]
    else:
        reject_raw = list(_DEFAULT_REJECT_PATTERNS)
    reject_patterns: list[re.Pattern[str]] = [
        re.compile(p, re.IGNORECASE) for p in reject_raw
    ]

    return {
        "leagues": leagues,
        "winner_pattern": winner_pattern,
        "reject_patterns": reject_patterns,
    }


# ── Polymarket queries ───────────────────────────────────────────────────


def _query_market_active(condition_id: str) -> bool:
    """Check if a condition_id is active and not closed via CLOB API."""
    url = f"https://clob.polymarket.com/markets/{condition_id}"
    data = _http_get_json(url, timeout=10)
    if not isinstance(data, dict):
        return False
    if data.get("closed") is True:
        return False
    if data.get("active") is not True:
        return False
    return True


def _get_league_slugs(league: str) -> list[str]:
    """Fetch league page and extract game slugs.

    Tries two strategies in order:
      1. JSON-LD <script> blocks (cleaner)
      2. URL pattern in hrefs (fallback)
    """
    url = f"https://polymarket.com/sports/{league}/games"
    html = _http_get_html(url, timeout=30)
    if not html:
        return []

    slugs: set[str] = set()

    # Strategy 1: JSON-LD ItemList with Event items
    # Pattern: "url":"https://polymarket.com/sports/{league}/{slug}"
    pattern = re.compile(
        rf'"url":\s*"https://polymarket\.com/sports/{re.escape(league)}/([a-z0-9-]+)"'
    )
    for m in pattern.finditer(html):
        slug = m.group(1)
        # Filter out non-game slugs (like "games" itself)
        if slug and slug != "games" and re.match(rf"^{re.escape(league)}-[a-z0-9]+-\d{{4}}-\d{{2}}-\d{{2}}$", slug):
            slugs.add(slug)

    # Strategy 2: fallback — href patterns
    if not slugs:
        href_pattern = re.compile(rf'href="/sports/{re.escape(league)}/([a-z0-9-]+)"')
        for m in href_pattern.finditer(html):
            slug = m.group(1)
            if slug and slug != "games":
                slugs.add(slug)

    return sorted(slugs)


def _get_event_markets(slug: str) -> list[dict[str, Any]]:
    """Fetch event by slug via gamma-api and return its markets."""
    url = f"https://gamma-api.polymarket.com/events?slug={slug}"
    data = _http_get_json(url, timeout=15)
    if not data:
        return []
    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = data.get("data", [])
    else:
        return []
    if not events:
        return []
    return cast(list[dict[str, Any]], events[0].get("markets", []))


def _is_winner_market(
    market: dict[str, Any],
    winner_pattern: re.Pattern[str],
    reject_patterns: list[re.Pattern[str]],
) -> bool:
    """Check if market matches the strict winner pattern and has no reject hits.

    Args:
        market: Market dict (must have 'question' key).
        winner_pattern: Compiled regex for acceptable questions.
        reject_patterns: List of compiled regexes; if any matches the question,
                         the market is rejected.
    """
    question = market.get("question", "")
    if not winner_pattern.match(question):
        return False
    for reject in reject_patterns:
        if reject.search(question):
            return False
    return True


def _find_eligible_market(
    league: str,
    winner_pattern: re.Pattern[str],
    reject_patterns: list[re.Pattern[str]],
) -> str | None:
    """Find first eligible 'Will X win' market condition_id in a league.

    Args:
        league: Polymarket league slug (e.g., "mex", "mls", "epl").
        winner_pattern: Compiled regex from config.
        reject_patterns: List of compiled reject regexes from config.
    """
    slugs = _get_league_slugs(league)
    logger.info("league_slugs_found", extra={"league": league, "count": len(slugs)})
    for slug in slugs:
        markets = _get_event_markets(slug)
        for market in markets:
            if not _is_winner_market(market, winner_pattern, reject_patterns):
                continue
            cond_id = cast(str, market.get("conditionId") or market.get("condition_id"))
            if not cond_id:
                continue
            if not market.get("active", False):
                continue
            if market.get("closed", False):
                continue
            # Double-check via CLOB (extra safety)
            if not _query_market_active(cond_id):
                continue
            return cond_id
    return None


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> int:
    """Execute the guard logic.

    Returns:
        0 if at least one active market exists.
        1 if no active markets found.
    """
    env = _load_env()
    raw = env.get("TRADY_AI_ACTIVE_MARKETS", "").strip()
    current_ids = [m.strip() for m in raw.split(",") if m.strip()] if raw else []

    # Load discovery config (externalized per BL-029)
    try:
        config = _load_discovery_config(env)
    except re.error as e:
        logger.error("invalid_winner_pattern", extra={"error": str(e)})
        return 1
    leagues: list[str] = config["leagues"]
    winner_pattern: re.Pattern[str] = config["winner_pattern"]
    reject_patterns: list[re.Pattern[str]] = config["reject_patterns"]

    if not current_ids:
        logger.info("no_markets_configured_attempting_discovery")

    # ── Phase 1: Check current markets ───────────────────────────────────
    expired_ids: list[str] = []
    active_ids: list[str] = []

    for mid in current_ids:
        if _query_market_active(mid):
            active_ids.append(mid)
            logger.info("market_active", extra={"market_id": mid})
        else:
            expired_ids.append(mid)
            logger.info("market_expired", extra={"market_id": mid})

    # ── Phase 2: Rotation if needed ──────────────────────────────────────
    if expired_ids and not active_ids:
        logger.info("all_markets_expired_attempting_rotation")
        for league in leagues:
            new_id = _find_eligible_market(league, winner_pattern, reject_patterns)
            if new_id:
                logger.info(
                    "market_rotated %s -> %s",
                    expired_ids[0] if expired_ids else "(none)",
                    new_id,
                )
                _write_env(".env", {"TRADY_AI_ACTIVE_MARKETS": new_id})
                logger.info(
                    "env_updated",
                    extra={"active_markets": new_id, "league": league},
                )
                return 0

        logger.error("no_eligible_markets_found")
        return 1

    # ── Phase 3: At least one active market remains ──────────────────────
    if active_ids:
        logger.info(
            "active_markets_found",
            extra={"count": len(active_ids), "markets": active_ids},
        )
        return 0

    # ── No markets configured and no discovery possible ───────────────────
    if not current_ids:
        for league in leagues:
            new_id = _find_eligible_market(league, winner_pattern, reject_patterns)
            if new_id:
                _write_env(".env", {"TRADY_AI_ACTIVE_MARKETS": new_id})
                logger.info(
                    "initial_market_discovered",
                    extra={"market_id": new_id, "league": league},
                )
                return 0
        logger.error("no_markets_available_for_discovery")
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
