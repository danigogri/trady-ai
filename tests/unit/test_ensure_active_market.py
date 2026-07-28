"""Unit tests for scripts/ensure_active_market.py.

Tests cover:
- Env loading and writing round-trip
- Discovery config loading (defaults + env override)
- Winner market regex matching (positive + negative cases)
- Main flow exit codes (with HTTP mocked)

Per Portable OS Operations Manual §5.3 and SDD-CYCLE-GOVERNANCE §6
(verify-report contract).

These tests are STANDALONE — no fixtures, no real HTTP, no conftest.
The script is standalone, the tests should be too.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Make the script importable
SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "scripts", "ensure_active_market.py",
)
SCRIPT_PATH = os.path.normpath(SCRIPT_PATH)

# Import the module dynamically
import importlib.util
_spec = importlib.util.spec_from_file_location("ensure_active_market", SCRIPT_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class TestLoadEnv(unittest.TestCase):
    """Tests for .env file parsing."""

    def test_load_env_missing_file(self):
        result = _mod._load_env("/nonexistent/path/.env")
        self.assertEqual(result, {})

    def test_load_env_basic(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("FOO=bar\nBAZ=qux\n")
            path = f.name
        try:
            result = _mod._load_env(path)
            self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})
        finally:
            os.unlink(path)

    def test_load_env_with_comments_and_blanks(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# this is a comment\n\nFOO=bar\n# another comment\nBAZ=qux\n")
            path = f.name
        try:
            result = _mod._load_env(path)
            self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})
        finally:
            os.unlink(path)

    def test_load_env_with_spaces(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("FOO= bar \nBAZ =qux\n")
            path = f.name
        try:
            result = _mod._load_env(path)
            self.assertEqual(result, {"FOO": "bar", "BAZ": "qux"})
        finally:
            os.unlink(path)


class TestWriteEnv(unittest.TestCase):
    """Tests for .env file writing (preserves comments, replaces keys)."""

    def test_write_env_preserves_comments(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("# header comment\nFOO=old\n# inline comment\n")
            path = f.name
        try:
            _mod._write_env(path, {"FOO": "new"})
            with open(path) as f:
                content = f.read()
            self.assertIn("# header comment", content)
            self.assertIn("# inline comment", content)
            self.assertIn("FOO=new", content)
            self.assertNotIn("FOO=old", content)
        finally:
            os.unlink(path)

    def test_write_env_appends_new_keys(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("FOO=bar\n")
            path = f.name
        try:
            _mod._write_env(path, {"NEW_KEY": "value"})
            with open(path) as f:
                content = f.read()
            self.assertIn("FOO=bar", content)
            self.assertIn("NEW_KEY=value", content)
        finally:
            os.unlink(path)

    def test_write_env_empty_updates_is_noop(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("FOO=bar\n")
            path = f.name
        try:
            _mod._write_env(path, {})
            with open(path) as f:
                content = f.read()
            self.assertEqual(content, "FOO=bar\n")
        finally:
            os.unlink(path)


class TestLoadDiscoveryConfig(unittest.TestCase):
    """Tests for BL-029: externalized discovery config from .env."""

    def test_defaults_when_no_env_vars(self):
        config = _mod._load_discovery_config({})
        self.assertEqual(config["leagues"], _mod._DEFAULT_LEAGUES)
        self.assertIsInstance(config["question_pattern"], re.Pattern)
        self.assertEqual(len(config["reject_patterns"]), len(_mod._DEFAULT_REJECT_PATTERNS))

    def test_custom_leagues_from_env(self):
        env = {"TRADY_AI_FOOTBALL_LEAGUES": "mls, epl , arg"}
        config = _mod._load_discovery_config(env)
        self.assertEqual(config["leagues"], ["mls", "epl", "arg"])

    def test_custom_winner_pattern_from_env(self):
        env = {"TRADY_AI_WINNER_PATTERN": r"^Will .+ win$"}
        config = _mod._load_discovery_config(env)
        self.assertIsInstance(config["question_pattern"], re.Pattern)
        # Test it actually works
        self.assertTrue(config["question_pattern"].match("Will Aston Villa win"))
        self.assertFalse(config["question_pattern"].match("Will Aston Villa win on 2026-07-21?"))

    def test_custom_reject_patterns_from_env(self):
        env = {"TRADY_AI_REJECT_PATTERNS": "draw,O/U,prop"}
        config = _mod._load_discovery_config(env)
        self.assertEqual(len(config["reject_patterns"]), 3)
        # All should be case-insensitive
        all_ci = all(p.flags & re.IGNORECASE for p in config["reject_patterns"])
        self.assertTrue(all_ci)

    def test_invalid_winner_pattern_raises(self):
        env = {"TRADY_AI_WINNER_PATTERN": "[invalid"}
        with self.assertRaises(re.error):
            _mod._load_discovery_config(env)

    def test_empty_leagues_string_falls_back_to_defaults(self):
        env = {"TRADY_AI_FOOTBALL_LEAGUES": ""}
        config = _mod._load_discovery_config(env)
        self.assertEqual(config["leagues"], _mod._DEFAULT_LEAGUES)

    # ── Phase 1: Domain config (DC-001, DC-002, DC-003) ──────────────

    def test_domain_default_to_football(self):
        """No TRADY_AI_DOMAIN → defaults to FOOTBALL-WINNER."""
        config = _mod._load_discovery_config({})
        self.assertEqual(config["domain"], "FOOTBALL-WINNER")

    def test_domain_explicit_crypto(self):
        """TRADY_AI_DOMAIN=CRYPTO-BINARY → domain is CRYPTO-BINARY."""
        env = {"TRADY_AI_DOMAIN": "CRYPTO-BINARY", "TRADY_AI_DISCOVERY_TAG_SLUG": "crypto"}
        config = _mod._load_discovery_config(env)
        self.assertEqual(config["domain"], "CRYPTO-BINARY")

    def test_domain_invalid_exits(self):
        """TRADY_AI_DOMAIN=NONSENSE → logs error, exits 1."""
        env = {"TRADY_AI_DOMAIN": "NONSENSE"}
        with self.assertRaises(SystemExit):
            _mod._load_discovery_config(env)

    def test_tag_slug_required_for_crypto(self):
        """CRYPTO-BINARY + DISCOVERY_TAG_SLUG=crypto → tag_slug is set."""
        env = {"TRADY_AI_DOMAIN": "CRYPTO-BINARY", "TRADY_AI_DISCOVERY_TAG_SLUG": "crypto"}
        config = _mod._load_discovery_config(env)
        self.assertEqual(config["tag_slug"], "crypto")

    def test_tag_slug_absent_exits(self):
        """CRYPTO-BINARY without DISCOVERY_TAG_SLUG → exits 1."""
        env = {"TRADY_AI_DOMAIN": "CRYPTO-BINARY"}
        with self.assertRaises(SystemExit):
            _mod._load_discovery_config(env)

    def test_tag_slug_empty_exits(self):
        """CRYPTO-BINARY + DISCOVERY_TAG_SLUG='' → exits 1."""
        env = {"TRADY_AI_DOMAIN": "CRYPTO-BINARY", "TRADY_AI_DISCOVERY_TAG_SLUG": ""}
        with self.assertRaises(SystemExit):
            _mod._load_discovery_config(env)

    def test_tag_slug_ignored_for_football(self):
        """FOOTBALL-WINNER without DISCOVERY_TAG_SLUG → tag_slug is None."""
        config = _mod._load_discovery_config({})
        self.assertIsNone(config["tag_slug"])

    def test_legacy_vars_still_read(self):
        """Legacy vars read when domain unset (defaults to FOOTBALL-WINNER)."""
        env = {
            "TRADY_AI_FOOTBALL_LEAGUES": "mex,mls",
            "TRADY_AI_WINNER_PATTERN": r"^Will .+ win$",
        }
        config = _mod._load_discovery_config(env)
        self.assertEqual(config["leagues"], ["mex", "mls"])
        self.assertIsInstance(config["question_pattern"], re.Pattern)
        self.assertEqual(config["domain"], "FOOTBALL-WINNER")

    def test_deprecation_warning_logged_when_domain_unset(self):
        """Legacy vars present without explicit domain → deprecation warning."""
        env = {
            "TRADY_AI_FOOTBALL_LEAGUES": "mex",
            "TRADY_AI_WINNER_PATTERN": r"^Will .+ win$",
        }
        with self.assertLogs(_mod.logger, level="WARNING") as log_cm:
            _mod._load_discovery_config(env)
        self.assertTrue(
            any("deprecated" in msg.lower() for msg in log_cm.output),
            msg=f"Expected deprecation warning, got: {log_cm.output}",
        )


class TestIsEligibleMarket(unittest.TestCase):
    """Tests for the regex-based eligible market detection."""

    @classmethod
    def setUpClass(cls):
        # Use a known config for these tests
        cls.pattern = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        cls.rejects = [re.compile(p, re.IGNORECASE) for p in _mod._DEFAULT_REJECT_PATTERNS]

    def test_positive_strict_match(self):
        market = {"question": "Will Aston Villa win on 2026-07-21?"}
        self.assertTrue(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_positive_without_question_mark(self):
        market = {"question": "Will Pumas win on 2026-08-01"}
        self.assertTrue(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_draw_market(self):
        market = {"question": "Will Aston Villa vs. BSC Young Boys end in a draw?"}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_over_under(self):
        market = {"question": "Team A vs. Team B: O/U 1.5"}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_total_goals(self):
        market = {"question": "Total goals in match: 2.5"}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_both_teams_to_score(self):
        market = {"question": "Will both teams to score in Liverpool vs Arsenal?"}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_handicap(self):
        market = {"question": "Will Lakers win with -3.5 handicap?"}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_spread(self):
        market = {"question": "Will Chiefs cover the spread?"}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_wrong_format(self):
        market = {"question": "Aston Villa to win on 2026-07-21"}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_empty_question(self):
        market = {"question": ""}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))

    def test_negative_missing_question(self):
        market = {}
        self.assertFalse(_mod._is_eligible_market(market, self.pattern, self.rejects))


class TestMainFlow(unittest.TestCase):
    """Integration tests for main() with HTTP mocked."""

    def test_main_active_market_in_env(self):
        """If .env has an active market, exit 0 and don't write."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TRADY_AI_ACTIVE_MARKETS=0xactive\n")
            env_path = f.name
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(_mod, "_query_market_active", return_value=True):
                with patch.object(_mod, "_write_env") as mock_write:
                    with patch.object(_mod, "_load_env", return_value={"TRADY_AI_ACTIVE_MARKETS": "0xactive"}):
                        exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_write.assert_not_called()
        os.unlink(env_path)

    def test_main_expired_market_triggers_discovery(self):
        """If all markets expired, run discovery. If found, exit 0 and write."""
        with patch.object(_mod, "_query_market_active", return_value=False) as mock_qma:
            with patch.object(_mod, "_find_eligible_market", return_value="0xnew") as mock_find:
                with patch.object(_mod, "_write_env") as mock_write:
                    with patch.object(_mod, "_load_env", return_value={"TRADY_AI_ACTIVE_MARKETS": "0xold"}):
                        exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_find.assert_called()
        mock_write.assert_called_once()
        # First call arg should be the new cond_id
        args, kwargs = mock_write.call_args
        self.assertEqual(args[1], {"TRADY_AI_ACTIVE_MARKETS": "0xnew"})

    def test_main_no_eligible_market_returns_1(self):
        """If all leagues fail, exit 1 and don't write."""
        with patch.object(_mod, "_query_market_active", return_value=False):
            with patch.object(_mod, "_find_eligible_market", return_value=None):
                with patch.object(_mod, "_write_env") as mock_write:
                    with patch.object(_mod, "_load_env", return_value={"TRADY_AI_ACTIVE_MARKETS": "0xold"}):
                        exit_code = _mod.main()
        self.assertEqual(exit_code, 1)
        mock_write.assert_not_called()

    def test_main_empty_env_triggers_discovery(self):
        """If .env is empty, run discovery."""
        with patch.object(_mod, "_find_eligible_market", return_value="0xnew") as mock_find:
            with patch.object(_mod, "_write_env") as mock_write:
                with patch.object(_mod, "_load_env", return_value={}):
                    exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_find.assert_called()
        mock_write.assert_called_once()

    def test_main_invalid_pattern_returns_1(self):
        """If TRADY_AI_WINNER_PATTERN is invalid, exit 1."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_MARKETS": "0xold",
            "TRADY_AI_WINNER_PATTERN": "[invalid",
        }):
            with patch.object(_mod, "_query_market_active", return_value=False):
                exit_code = _mod.main()
        self.assertEqual(exit_code, 1)


class TestDiscoverTagBased(unittest.TestCase):
    """Tests for _discover_tag_based() tag-based discovery."""

    def _make_event(self, condition_id: str, question: str, active: bool = True, closed: bool = False) -> dict:
        return {
            "markets": [{
                "conditionId": condition_id,
                "condition_id": condition_id,
                "question": question,
                "active": active,
                "closed": closed,
            }],
        }

    def test_success_extracts_condition_id(self):
        """TD-001: API returns events → extracts first condition_id."""
        events = [
            self._make_event("0xcrypto1", "Will BTC win on 2026-07-27?"),
        ]
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        with patch.object(_mod, "_http_get_json", return_value=events):
            with patch.object(_mod, "_query_market_active", return_value=True):
                result = _mod._discover_tag_based("crypto", question_pat, [])
        self.assertEqual(result, "0xcrypto1")

    def test_filter_rejects_non_matching_question(self):
        """TD-002: Non-matching questions skipped, matching one found."""
        events = [
            self._make_event("0xskip1", "BTC price over 100k?"),
            self._make_event("0xskip2", "Will ETH and LTC end in a draw?"),
            self._make_event("0xvalid1", "Will ETH win on 2026-07-28?"),
        ]
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        with patch.object(_mod, "_http_get_json", return_value=events):
            with patch.object(_mod, "_query_market_active", return_value=True):
                result = _mod._discover_tag_based("crypto", question_pat, [])
        self.assertEqual(result, "0xvalid1")

    def test_filter_reject_pattern_excludes(self):
        """TD-002: Question matches pattern but contains reject substring → skipped."""
        events = [
            self._make_event("0xrej1", "Will BTC win on 2026-07-27 end in a draw?"),
            self._make_event("0xvalid2", "Will ETH win on 2026-07-28?"),
        ]
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        reject_pats = [re.compile("end in a draw", re.IGNORECASE)]
        with patch.object(_mod, "_http_get_json", return_value=events):
            with patch.object(_mod, "_query_market_active", return_value=True):
                result = _mod._discover_tag_based("crypto", question_pat, reject_pats)
        self.assertEqual(result, "0xvalid2")

    def test_clob_confirms_market(self):
        """TD-003: CLOB query confirms market → accepted."""
        events = [
            self._make_event("0xclob1", "Will BTC win on 2026-07-27?"),
        ]
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        with patch.object(_mod, "_http_get_json", return_value=events):
            with patch.object(_mod, "_query_market_active", return_value=True) as mock_clob:
                result = _mod._discover_tag_based("crypto", question_pat, [])
        self.assertEqual(result, "0xclob1")
        mock_clob.assert_called_once_with("0xclob1")

    def test_clob_rejects_then_finds_another(self):
        """TD-003: CLOB rejects first market → tries next."""
        events = [
            self._make_event("0xdead1", "Will BTC win on 2026-07-27?"),
            self._make_event("0xlive1", "Will ETH win on 2026-07-28?"),
        ]
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)

        def clob_side_effect(cid: str) -> bool:
            return cid == "0xlive1"

        with patch.object(_mod, "_http_get_json", return_value=events):
            with patch.object(_mod, "_query_market_active", side_effect=clob_side_effect):
                result = _mod._discover_tag_based("crypto", question_pat, [])
        self.assertEqual(result, "0xlive1")

    def test_empty_events_returns_none(self):
        """TD-004: API returns [] → returns None (no exit)."""
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        with patch.object(_mod, "_http_get_json", return_value=[]):
            result = _mod._discover_tag_based("crypto", question_pat, [])
        self.assertIsNone(result)

    def test_http_error_returns_none(self):
        """TD-004: http_get_json returns None → returns None."""
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        with patch.object(_mod, "_http_get_json", return_value=None):
            result = _mod._discover_tag_based("crypto", question_pat, [])
        self.assertIsNone(result)

    def test_no_matching_markets_returns_none(self):
        """TD-002: Events exist but no markets match → returns None."""
        events = [
            self._make_event("0xnope1", "BTC price over 100k?"),
            self._make_event("0xnope2", "ETH staking yield?"),
        ]
        question_pat = re.compile(_mod._DEFAULT_QUESTION_PATTERN)
        with patch.object(_mod, "_http_get_json", return_value=events):
            result = _mod._discover_tag_based("crypto", question_pat, [])
        self.assertIsNone(result)


class TestMainFlowRouting(unittest.TestCase):
    """Tests for domain-based discovery routing in main() [DR-001, DR-002]."""

    def test_tag_based_domain_discovers_and_writes(self):
        """DR-001: CRYPTO-BINARY domain → _discover_tag_based called, writes .env."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_MARKETS": "0xold",
            "TRADY_AI_DOMAIN": "CRYPTO-BINARY",
            "TRADY_AI_DISCOVERY_TAG_SLUG": "crypto",
        }):
            with patch.object(_mod, "_query_market_active", return_value=False):
                with patch.object(_mod, "_discover_tag_based", return_value="0xcrypto") as mock_tag:
                    with patch.object(_mod, "_write_env") as mock_write:
                        exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_tag.assert_called_once()
        mock_write.assert_called_once_with(".env", {"TRADY_AI_ACTIVE_MARKETS": "0xcrypto"})

    def test_tag_based_no_market_exits_1(self):
        """DR-002: CRYPTO-BINARY but no market found → exits 1, no write."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_MARKETS": "0xold",
            "TRADY_AI_DOMAIN": "CRYPTO-BINARY",
            "TRADY_AI_DISCOVERY_TAG_SLUG": "crypto",
        }):
            with patch.object(_mod, "_query_market_active", return_value=False):
                with patch.object(_mod, "_discover_tag_based", return_value=None):
                    with patch.object(_mod, "_write_env") as mock_write:
                        exit_code = _mod.main()
        self.assertEqual(exit_code, 1)
        mock_write.assert_not_called()

    def test_league_based_unchanged(self):
        """DR-003: FOOTBALL-WINNER domain → existing league path used."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_MARKETS": "0xold",
            "TRADY_AI_DOMAIN": "FOOTBALL-WINNER",
        }):
            with patch.object(_mod, "_query_market_active", return_value=False):
                with patch.object(_mod, "_find_eligible_market", return_value="0xnew") as mock_league:
                    with patch.object(_mod, "_write_env") as mock_write:
                        exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_league.assert_called()
        mock_write.assert_called_once_with(".env", {"TRADY_AI_ACTIVE_MARKETS": "0xnew"})

    def test_domain_unset_defaults_football(self):
        """DR-003: Domain unset → defaults to FOOTBALL-WINNER, league path used."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_MARKETS": "0xold",
        }):
            with patch.object(_mod, "_query_market_active", return_value=False):
                with patch.object(_mod, "_find_eligible_market", return_value="0xnew") as mock_league:
                    with patch.object(_mod, "_write_env") as mock_write:
                        exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_league.assert_called()
        mock_write.assert_called_once()


class TestStaticDomainPass(unittest.TestCase):
    """Tests for BINANCE-SPOT static domain branch (REQ-SD-001 through REQ-SD-005)."""

    def test_static_domain_pass(self):
        """REQ-SD-003: Valid symbols → exit 0, .env not touched."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_SYMBOLS": "BTCUSDT,ETHUSDT",
            "TRADY_AI_DOMAIN": "BINANCE-SPOT",
        }):
            with patch.object(_mod, "_write_env") as mock_write:
                exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_write.assert_not_called()

    def test_static_domain_empty(self):
        """REQ-SD-004: Empty symbols → exit 1."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_SYMBOLS": "",
            "TRADY_AI_DOMAIN": "BINANCE-SPOT",
        }):
            exit_code = _mod.main()
        self.assertEqual(exit_code, 1)

    def test_static_domain_unset(self):
        """REQ-SD-004: No TRADY_AI_ACTIVE_SYMBOLS → exit 1."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_DOMAIN": "BINANCE-SPOT",
        }):
            exit_code = _mod.main()
        self.assertEqual(exit_code, 1)

    def test_static_domain_lowercase_rejected(self):
        """REQ-SD-002: Lowercase symbols are rejected."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_SYMBOLS": "btcusdt,ethusdt",
            "TRADY_AI_DOMAIN": "BINANCE-SPOT",
        }):
            exit_code = _mod.main()
        self.assertEqual(exit_code, 1)

    def test_static_domain_invalid_chars_rejected(self):
        """REQ-SD-002: Invalid characters rejected."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_SYMBOLS": "BTC-USDT,ETH*USDT",
            "TRADY_AI_DOMAIN": "BINANCE-SPOT",
        }):
            exit_code = _mod.main()
        self.assertEqual(exit_code, 1)

    def test_static_domain_with_whitespace(self):
        """REQ-SD-002: Whitespace stripped but symbols still valid."""
        with patch.object(_mod, "_load_env", return_value={
            "TRADY_AI_ACTIVE_SYMBOLS": " BTCUSDT , ETHUSDT ",
            "TRADY_AI_DOMAIN": "BINANCE-SPOT",
        }):
            with patch.object(_mod, "_write_env") as mock_write:
                exit_code = _mod.main()
        self.assertEqual(exit_code, 0)
        mock_write.assert_not_called()

    def test_valid_domains_includes_binance_spot(self):
        """REQ-SD-005: BINANCE-SPOT is in _VALID_DOMAINS."""
        self.assertIn("BINANCE-SPOT", _mod._VALID_DOMAINS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
