"""Integration tests for ``scripts/ensure_active_market.py``.

Scenarios:
(a) All Condition IDs active → exit 0, no mutation
(b) One expired → rotates, exits 0
(c) All expired, no candidates → exits 1
(d) .env mutation produces valid next-session read
"""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import ANY, patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_env():
    """Create a temporary .env file and return its path.

    Cleans up after the test. Changes CWD to the temp dir so the guard
    script finds our .env.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            yield os.path.join(tmpdir, ".env")
        finally:
            os.chdir(cwd)


def _write_env(env_path: str, content: str) -> None:
    """Write content to the .env file."""
    with open(env_path, "w") as f:
        f.write(content)


def _read_env(env_path: str) -> dict[str, str]:
    """Read .env into a dict."""
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


def _make_market(
    condition_id: str,
    closed: bool = False,
    active: bool = True,
    tags: list[str] | None = None,
) -> dict:
    """Build a mock market response dict."""
    return {
        "condition_id": condition_id,
        "id": condition_id,
        "closed": closed,
        "active": active,
        "tags": tags or ["football", "winner"],
    }


# ── Scenarios ────────────────────────────────────────────────────────────────


class TestGuardActiveMarkets:
    """Scenario (a): All Condition IDs active → exit 0, no mutation."""

    @patch("urllib.request.urlopen")
    def test_all_active_no_mutation(self, mock_urlopen, temp_env):
        """All markets active → exit 0, .env unchanged."""
        from scripts.ensure_active_market import main

        # Set up .env with active markets
        _write_env(
            temp_env,
            "TRADY_AI_ACTIVE_MARKETS=0xABC,0xDEF\nOTHER_VAR=hello\n",
        )

        # Mock API responses for both markets (both active)
        def mock_response(*args, **kwargs):
            request = args[0]
            class Resp:
                def __init__(self, data):
                    self._data = data

                def read(self):
                    return json.dumps(self._data).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            url = request.full_url
            if "0xABC" in url:
                return Resp(_make_market("0xABC"))
            if "0xDEF" in url:
                return Resp(_make_market("0xDEF"))
            return Resp({"data": []})

        mock_urlopen.side_effect = mock_response

        result = main()
        assert result == 0, f"Expected exit 0, got {result}"

        # .env should be unchanged
        env = _read_env(temp_env)
        assert env["TRADY_AI_ACTIVE_MARKETS"] == "0xABC,0xDEF"
        assert env["OTHER_VAR"] == "hello"


class TestGuardRotation:
    """Scenario (b): One expired → rotates, exits 0."""

    @patch("urllib.request.urlopen")
    def test_expired_rotates(self, mock_urlopen, temp_env):
        """One expired market → rotates to replacement, exits 0."""
        from scripts.ensure_active_market import main

        _write_env(
            temp_env,
            "TRADY_AI_ACTIVE_MARKETS=0xABC,0xDEF\n",
        )

        call_count = 0

        def mock_response(*args, **kwargs):
            request = args[0]
            class Resp:
                def __init__(self, data):
                    self._data = data

                def read(self):
                    return json.dumps(self._data).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            nonlocal call_count
            call_count += 1
            url = request.full_url

            # First two calls check existing markets
            if "0xABC" in url:
                return Resp(_make_market("0xABC", closed=True))  # expired
            if "0xDEF" in url:
                return Resp(_make_market("0xDEF", closed=True))  # expired

            # Third call: GET /markets to find replacements
            return Resp([
                _make_market("0xNEW1", tags=["football", "winner"]),
                _make_market("0xNEW2", tags=["football", "winner"]),
            ])

        mock_urlopen.side_effect = mock_response

        result = main()
        assert result == 0, f"Expected exit 0, got {result}"

        # .env should contain the replacement (first eligible)
        env = _read_env(temp_env)
        assert "0xNEW1" in env.get("TRADY_AI_ACTIVE_MARKETS", "")


class TestGuardNoCandidates:
    """Scenario (c): All expired, no candidates → exits 1."""

    @patch("urllib.request.urlopen")
    def test_all_expired_no_candidates(self, mock_urlopen, temp_env):
        """All expired, no eligible replacements → exit 1."""
        from scripts.ensure_active_market import main

        _write_env(
            temp_env,
            "TRADY_AI_ACTIVE_MARKETS=0xABC\n",
        )

        def mock_response(*args, **kwargs):
            request = args[0]
            class Resp:
                def __init__(self, data):
                    self._data = data

                def read(self):
                    return json.dumps(self._data).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            url = request.full_url
            if "0xABC" in url:
                return Resp(_make_market("0xABC", closed=True))

            # GET /markets — return no eligible markets
            return Resp([
                _make_market("0xOTHER", active=False),  # not active
                _make_market("0xOTHER2", tags=["baseball"]),  # wrong tags
            ])

        mock_urlopen.side_effect = mock_response

        result = main()
        assert result == 1, f"Expected exit 1, got {result}"


class TestGuardEnvMutation:
    """Scenario (d): .env mutation produces valid next-session read."""

    @patch("urllib.request.urlopen")
    def test_env_mutation_readable_by_settings(self, mock_urlopen, temp_env):
        """.env written by guard is readable by Settings.get_active_market_ids()."""
        from scripts.ensure_active_market import main

        # Start with all expired
        _write_env(
            temp_env,
            "TRADY_AI_ACTIVE_MARKETS=0xEXPIRED\n",
        )

        def mock_response(*args, **kwargs):
            request = args[0]
            class Resp:
                def __init__(self, data):
                    self._data = data

                def read(self):
                    return json.dumps(self._data).encode()

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

            url = request.full_url
            if "0xEXPIRED" in url:
                return Resp(_make_market("0xEXPIRED", closed=True))

            # Available replacement markets
            return Resp([
                _make_market("0xREPLACEMENT", tags=["football", "winner"]),
            ])

        mock_urlopen.side_effect = mock_response

        result = main()
        assert result == 0

        # Verify .env was updated
        env = _read_env(temp_env)
        written_value = env.get("TRADY_AI_ACTIVE_MARKETS", "")
        assert written_value == "0xREPLACEMENT"

        # Simulate what Settings.get_active_market_ids() does
        parsed = [m.strip() for m in written_value.split(",") if m.strip()]
        assert parsed == ["0xREPLACEMENT"]
