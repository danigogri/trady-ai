"""Tests for strategy_snapshots persistence schema.

Covers:
- Table creation (init_strategy_tables)
- Idempotency
- Column schema
- UNIQUE constraint behavior
- init_core_tables integration
"""

from trady_ai.core.persistence import (
    init_core_tables,
    init_strategy_tables,
    persist_strategy_snapshot,
)


class TestInitStrategyTables:
    """init_strategy_tables creates the strategy_snapshots table."""

    def test_creates_strategy_snapshots_table(self, tmp_strategy_db):
        """The strategy_snapshots table exists after init."""
        assert "strategy_snapshots" in tmp_strategy_db.table_names()

    def test_idempotent(self, tmp_strategy_db):
        """Calling init_strategy_tables twice does not fail."""
        init_strategy_tables(tmp_strategy_db)  # Second call — no error

    def test_has_correct_columns(self, tmp_strategy_db):
        """Table has the required 9 columns."""
        cols = {c.name for c in tmp_strategy_db["strategy_snapshots"].columns}
        expected = {
            "id",
            "strategy_name",
            "domain",
            "tick_number",
            "transition_counts",
            "state_counts",
            "warmup_ticks",
            "threshold_pct",
            "snapshot_at",
        }
        missing = expected - cols
        assert not missing, f"Missing columns: {missing}"

    def test_init_core_tables_includes_strategy_snapshots(self):
        """init_core_tables creates strategy_snapshots alongside existing tables."""
        import sqlite3

        import sqlite_utils

        db = sqlite_utils.Database(sqlite3.connect(":memory:"))
        init_core_tables(db)
        assert "strategy_snapshots" in db.table_names()


class TestUniqueConstraint:
    """UNIQUE(strategy_name, domain, tick_number) behavior."""

    def test_same_key_replaces(self, tmp_strategy_db):
        """Duplicate (name, domain, tick) replaces (INSERT OR REPLACE)."""
        persist_strategy_snapshot(
            tmp_strategy_db, "PM-5M", "test_strat", 1,
            [[1, 0, 0], [0, 0, 0], [0, 0, 0]], [1, 0, 0], 50, "0.001",
        )
        persist_strategy_snapshot(
            tmp_strategy_db, "PM-5M", "test_strat", 1,
            [[0, 1, 0], [0, 0, 0], [0, 0, 0]], [0, 1, 0], 50, "0.002",
        )
        assert tmp_strategy_db["strategy_snapshots"].count == 1

    def test_different_tick_numbers_separate_rows(self, tmp_strategy_db):
        """Different tick_numbers for same (name, domain) are separate rows."""
        persist_strategy_snapshot(
            tmp_strategy_db, "PM-5M", "test_strat", 1,
            [[1, 0, 0], [0, 0, 0], [0, 0, 0]], [1, 0, 0], 50, "0.001",
        )
        persist_strategy_snapshot(
            tmp_strategy_db, "PM-5M", "test_strat", 2,
            [[1, 1, 0], [0, 0, 0], [0, 0, 0]], [2, 0, 0], 50, "0.001",
        )
        assert tmp_strategy_db["strategy_snapshots"].count == 2

    def test_different_domains_separate_rows(self, tmp_strategy_db):
        """Different domains for same (name, tick) are separate rows."""
        persist_strategy_snapshot(
            tmp_strategy_db, "PM-5M", "test_strat", 1,
            [[1, 0, 0], [0, 0, 0], [0, 0, 0]], [1, 0, 0], 50, "0.001",
        )
        persist_strategy_snapshot(
            tmp_strategy_db, "OTHER", "test_strat", 1,
            [[1, 0, 0], [0, 0, 0], [0, 0, 0]], [1, 0, 0], 50, "0.001",
        )
        assert tmp_strategy_db["strategy_snapshots"].count == 2
