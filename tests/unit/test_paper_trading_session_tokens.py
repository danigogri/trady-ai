"""Tests for PaperTradingSession._resolve_token_ids.

Regression test for the conditionId → token_id translation bug that
caused the WS subscription to silently fail (no events captured).
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from trady_ai.paper_trading.session import PaperTradingSession


def _make_session(adapter_mock: MagicMock) -> PaperTradingSession:
    """Build a minimal PaperTradingSession for unit testing."""
    db = MagicMock()
    return PaperTradingSession(db=db, adapter=adapter_mock)


class TestResolveTokenIds:
    """Tests for condition_id → token_id translation."""

    def test_resolves_single_market_two_tokens(self):
        """A market with Yes/No tokens returns both token_ids."""
        adapter = MagicMock()
        adapter.get_market_data.return_value = {
            "condition_id": "0xcond1",
            "tokens": [
                {"token_id": "0xtok1", "outcome": "Yes"},
                {"token_id": "0xtok2", "outcome": "No"},
            ],
        }
        session = _make_session(adapter)

        result = session._resolve_token_ids(["0xcond1"])

        assert result == ["0xtok1", "0xtok2"]
        adapter.get_market_data.assert_called_once_with("0xcond1")

    def test_resolves_multiple_markets(self):
        """Multiple condition_ids return all tokens in order."""
        adapter = MagicMock()
        adapter.get_market_data.side_effect = [
            {
                "tokens": [
                    {"token_id": "0xtok1A", "outcome": "Yes"},
                    {"token_id": "0xtok1B", "outcome": "No"},
                ]
            },
            {
                "tokens": [
                    {"token_id": "0xtok2A", "outcome": "Yes"},
                    {"token_id": "0xtok2B", "outcome": "No"},
                ]
            },
        ]
        session = _make_session(adapter)

        result = session._resolve_token_ids(["0xcond1", "0xcond2"])

        assert result == ["0xtok1A", "0xtok1B", "0xtok2A", "0xtok2B"]
        assert adapter.get_market_data.call_count == 2

    def test_skips_failed_resolution(self):
        """A market that fails to resolve is skipped, others continue."""
        adapter = MagicMock()
        adapter.get_market_data.side_effect = [
            Exception("404 Not Found"),
            {
                "tokens": [
                    {"token_id": "0xtok2A", "outcome": "Yes"},
                ]
            },
        ]
        session = _make_session(adapter)

        result = session._resolve_token_ids(["0xbad", "0xcond2"])

        assert result == ["0xtok2A"]

    def test_skips_market_with_no_tokens(self):
        """A market with empty/missing tokens field contributes nothing."""
        adapter = MagicMock()
        adapter.get_market_data.return_value = {
            "condition_id": "0xcond1",
            # no "tokens" key
        }
        session = _make_session(adapter)

        result = session._resolve_token_ids(["0xcond1"])

        assert result == []

    def test_empty_input(self):
        """Empty condition_ids list returns empty token_ids list."""
        adapter = MagicMock()
        session = _make_session(adapter)

        result = session._resolve_token_ids([])

        assert result == []
        adapter.get_market_data.assert_not_called()

    def test_skips_tokens_with_empty_token_id(self):
        """Tokens with empty token_id are filtered out."""
        adapter = MagicMock()
        adapter.get_market_data.return_value = {
            "tokens": [
                {"token_id": "", "outcome": "Yes"},  # empty
                {"token_id": "0xtok1", "outcome": "No"},
                {"outcome": "Yes"},  # missing token_id key
            ]
        }
        session = _make_session(adapter)

        result = session._resolve_token_ids(["0xcond1"])

        assert result == ["0xtok1"]


if __name__ == "__main__":
    unittest.main(verbosity=2)
