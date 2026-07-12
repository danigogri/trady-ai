"""Fixtures for Markov strategy persistence tests."""

import sqlite3

import pytest
import sqlite_utils

from trady_ai.core.persistence import init_strategy_tables


@pytest.fixture
def tmp_strategy_db(tmp_path):
    """Database with strategy_snapshots table initialized."""
    conn = sqlite3.connect(str(tmp_path / "strategy_test.db"), check_same_thread=False)
    db = sqlite_utils.Database(conn)
    init_strategy_tables(db)
    return db
