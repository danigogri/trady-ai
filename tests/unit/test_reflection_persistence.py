"""Tests for reflection persistence layer.

Verifies table creation and indexes for:
  - reflection_reports
  - drift_events
  - proposals
  - reflection_config
"""
from __future__ import annotations


def _table_info(db, table: str) -> list[dict]:
    """Return PRAGMA table_info for a given table."""
    return list(db.query(f"PRAGMA table_info({table})"))


def _index_list(db, table: str) -> list[dict]:
    """Return PRAGMA index_list for a given table."""
    return list(db.query(f"PRAGMA index_list({table})"))


class TestReflectionTablesExist:
    """Verify all 4 reflection tables are created after init_core_tables()."""

    def test_reflection_reports_table_exists(self, tmp_db) -> None:
        """reflection_reports table exists after init."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        tables = [row["name"] for row in tmp_db.query("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "reflection_reports" in tables

    def test_drift_events_table_exists(self, tmp_db) -> None:
        """drift_events table exists after init."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        tables = [row["name"] for row in tmp_db.query("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "drift_events" in tables

    def test_proposals_table_exists(self, tmp_db) -> None:
        """proposals table exists after init."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        tables = [row["name"] for row in tmp_db.query("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "proposals" in tables

    def test_reflection_config_table_exists(self, tmp_db) -> None:
        """reflection_config table exists after init."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        tables = [row["name"] for row in tmp_db.query("SELECT name FROM sqlite_master WHERE type='table'")]
        assert "reflection_config" in tables


class TestReflectionReportsSchema:
    def test_columns(self, tmp_db) -> None:
        """reflection_reports has correct columns."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        info = _table_info(tmp_db, "reflection_reports")
        cols = {row["name"]: row for row in info}

        assert cols["id"]["type"] == "INTEGER"
        assert cols["id"]["pk"] == 1
        assert cols["scope"]["type"] == "TEXT"
        assert cols["scope"]["notnull"] == 1
        assert cols["domain"]["type"] == "TEXT"
        assert cols["domain"]["notnull"] == 1
        assert cols["mode"]["type"] == "TEXT"
        assert cols["mode"]["notnull"] == 1
        assert cols["period_start"]["type"] == "TEXT"
        assert cols["period_start"]["notnull"] == 1
        assert cols["period_end"]["type"] == "TEXT"
        assert cols["period_end"]["notnull"] == 1
        assert cols["report_data"]["type"] == "TEXT"
        assert cols["report_data"]["notnull"] == 1
        assert cols["created_at"]["type"] == "TEXT"
        assert cols["created_at"]["notnull"] == 1

    def test_has_index_on_period(self, tmp_db) -> None:
        """idx_reflection_reports_period index exists."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        indexes = _index_list(tmp_db, "reflection_reports")
        names = [idx["name"] for idx in indexes]
        assert "idx_reflection_reports_period" in names


class TestDriftEventsSchema:
    def test_columns(self, tmp_db) -> None:
        """drift_events has correct columns."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        info = _table_info(tmp_db, "drift_events")
        cols = {row["name"]: row for row in info}

        assert cols["id"]["type"] == "INTEGER"
        assert cols["id"]["pk"] == 1
        assert cols["strategy_id"]["type"] == "TEXT"
        assert cols["strategy_id"]["notnull"] == 1
        assert cols["domain"]["type"] == "TEXT"
        assert cols["domain"]["notnull"] == 1
        assert cols["metric"]["type"] == "TEXT"
        assert cols["metric"]["notnull"] == 1
        assert cols["previous_value"]["type"] == "REAL"
        assert cols["current_value"]["type"] == "REAL"
        assert cols["threshold"]["type"] == "REAL"
        assert cols["deviation_pct"]["type"] == "REAL"
        assert cols["detected_at"]["type"] == "TEXT"
        assert cols["acknowledged"]["type"] == "INTEGER"

    def test_has_index_on_strategy_domain(self, tmp_db) -> None:
        """idx_drift_events_strategy_domain index exists."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        indexes = _index_list(tmp_db, "drift_events")
        names = [idx["name"] for idx in indexes]
        assert "idx_drift_events_strategy_domain" in names


class TestProposalsSchema:
    def test_columns(self, tmp_db) -> None:
        """proposals has correct columns."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        info = _table_info(tmp_db, "proposals")
        cols = {row["name"]: row for row in info}

        assert cols["id"]["type"] == "INTEGER"
        assert cols["id"]["pk"] == 1
        assert cols["strategy_id"]["type"] == "TEXT"
        assert cols["strategy_id"]["notnull"] == 1
        assert cols["parameter_name"]["type"] == "TEXT"
        assert cols["parameter_name"]["notnull"] == 1
        assert cols["current_value"]["type"] == "REAL"
        assert cols["proposed_value"]["type"] == "REAL"
        assert cols["range_min"]["type"] == "REAL"
        assert cols["range_max"]["type"] == "REAL"
        assert cols["justification"]["type"] == "TEXT"
        assert cols["justification"]["notnull"] == 1
        assert cols["status"]["type"] == "TEXT"
        assert cols["status"]["notnull"] == 1
        assert cols["created_at"]["type"] == "TEXT"
        assert cols["created_at"]["notnull"] == 1

    def test_has_index_on_strategy_id(self, tmp_db) -> None:
        """idx_proposals_strategy_id index exists."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        indexes = _index_list(tmp_db, "proposals")
        names = [idx["name"] for idx in indexes]
        assert "idx_proposals_strategy_id" in names


class TestReflectionConfigSchema:
    def test_columns_with_composite_pk(self, tmp_db) -> None:
        """reflection_config has correct columns with composite PK."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        info = _table_info(tmp_db, "reflection_config")
        cols = {row["name"]: row for row in info}

        assert cols["domain"]["type"] == "TEXT"
        assert cols["domain"]["notnull"] == 1
        assert cols["domain"]["pk"] == 1  # Part of composite PK
        assert cols["key"]["type"] == "TEXT"
        assert cols["key"]["notnull"] == 1
        assert cols["key"]["pk"] == 2  # Part of composite PK
        assert cols["value"]["type"] == "TEXT"
        assert cols["value"]["notnull"] == 1
        assert cols["updated_at"]["type"] == "TEXT"
        assert cols["updated_at"]["notnull"] == 1

    def test_has_index_on_domain(self, tmp_db) -> None:
        """idx_reflection_config_domain index exists."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        indexes = _index_list(tmp_db, "reflection_config")
        names = [idx["name"] for idx in indexes]
        assert "idx_reflection_config_domain" in names


class TestInitIdempotence:
    """Verify init_core_tables() can be called multiple times."""

    def test_init_core_tables_is_idempotent(self, tmp_db) -> None:
        """Calling init_core_tables twice does not error."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)
        init_core_tables(tmp_db)  # Second call — should not raise

        # Tables still usable
        tmp_db.execute("INSERT INTO reflection_reports (scope, domain, mode, period_start, period_end, report_data) "
                       "VALUES ('session', 'PM-5M', 'dry_run', '2026-07-10', '2026-07-10', '{}')")
        row = tmp_db.execute("SELECT COUNT(*) as cnt FROM reflection_reports").fetchone()
        assert row[0] == 1

    def test_can_insert_into_all_tables(self, tmp_db) -> None:
        """All 4 tables accept inserts after init."""
        from trady_ai.core.persistence import init_core_tables

        init_core_tables(tmp_db)

        # reflection_reports
        tmp_db.execute(
            "INSERT INTO reflection_reports (scope, domain, mode, period_start, period_end, report_data) "
            "VALUES ('session', 'PM-5M', 'dry_run', '2026-07-10', '2026-07-10', '{}')"
        )

        # drift_events
        tmp_db.execute(
            "INSERT INTO drift_events (strategy_id, domain, metric, previous_value, current_value, "
            "threshold, deviation_pct, detected_at) "
            "VALUES ('markov', 'PM-5M', 'transition_UP_UP', 0.6, 0.42, 0.15, 30.0, '2026-07-10')"
        )

        # proposals
        tmp_db.execute(
            "INSERT INTO proposals (strategy_id, parameter_name, current_value, proposed_value, "
            "range_min, range_max, justification) "
            "VALUES ('markov', 'warmup_ticks', 50.0, 75.0, 10.0, 200.0, 'Improved win rate')"
        )

        # reflection_config
        tmp_db.execute(
            "INSERT INTO reflection_config (domain, key, value) "
            "VALUES ('PM-5M', 'min_sessions', '30')"
        )

        counts = [
            tmp_db.execute("SELECT COUNT(*) FROM reflection_reports").fetchone()[0],
            tmp_db.execute("SELECT COUNT(*) FROM drift_events").fetchone()[0],
            tmp_db.execute("SELECT COUNT(*) FROM proposals").fetchone()[0],
            tmp_db.execute("SELECT COUNT(*) FROM reflection_config").fetchone()[0],
        ]
        assert counts == [1, 1, 1, 1]
