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
        self.assertIsInstance(config["winner_pattern"], re.Pattern)
        self.assertEqual(len(config["reject_patterns"]), len(_mod._DEFAULT_REJECT_PATTERNS))

    def test_custom_leagues_from_env(self):
        env = {"TRADY_AI_FOOTBALL_LEAGUES": "mls, epl , arg"}
        config = _mod._load_discovery_config(env)
        self.assertEqual(config["leagues"], ["mls", "epl", "arg"])

    def test_custom_winner_pattern_from_env(self):
        env = {"TRADY_AI_WINNER_PATTERN": r"^Will .+ win$"}
        config = _mod._load_discovery_config(env)
        self.assertIsInstance(config["winner_pattern"], re.Pattern)
        # Test it actually works
        self.assertTrue(config["winner_pattern"].match("Will Aston Villa win"))
        self.assertFalse(config["winner_pattern"].match("Will Aston Villa win on 2026-07-21?"))

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


class TestIsWinnerMarket(unittest.TestCase):
    """Tests for the regex-based winner market detection."""

    @classmethod
    def setUpClass(cls):
        # Use a known config for these tests
        cls.winner = re.compile(_mod._DEFAULT_WINNER_PATTERN)
        cls.rejects = [re.compile(p, re.IGNORECASE) for p in _mod._DEFAULT_REJECT_PATTERNS]

    def test_positive_strict_match(self):
        market = {"question": "Will Aston Villa win on 2026-07-21?"}
        self.assertTrue(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_positive_without_question_mark(self):
        market = {"question": "Will Pumas win on 2026-08-01"}
        self.assertTrue(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_draw_market(self):
        market = {"question": "Will Aston Villa vs. BSC Young Boys end in a draw?"}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_over_under(self):
        market = {"question": "Team A vs. Team B: O/U 1.5"}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_total_goals(self):
        market = {"question": "Total goals in match: 2.5"}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_both_teams_to_score(self):
        market = {"question": "Will both teams to score in Liverpool vs Arsenal?"}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_handicap(self):
        market = {"question": "Will Lakers win with -3.5 handicap?"}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_spread(self):
        market = {"question": "Will Chiefs cover the spread?"}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_wrong_format(self):
        market = {"question": "Aston Villa to win on 2026-07-21"}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_empty_question(self):
        market = {"question": ""}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))

    def test_negative_missing_question(self):
        market = {}
        self.assertFalse(_mod._is_winner_market(market, self.winner, self.rejects))


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
