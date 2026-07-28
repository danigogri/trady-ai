import csv
from datetime import UTC, datetime, timedelta

from click.testing import CliRunner

from trady_ai.cli.main import cli
from trady_ai.config import get_settings


def test_status_command():
    """Verifica que 'trady-ai status' muestra environment y dry_run."""
    get_settings.cache_clear()
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "dry_run" in result.output or "Dry run" in result.output
    assert "environment" in result.output or "Environment" in result.output


def test_status_no_secrets_leaked():
    """Verifica que 'trady-ai status' NO muestra secrets_api_key."""
    get_settings.cache_clear()
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert "secrets_api_key" not in result.output
    assert "secret" not in result.output.lower()


class TestBacktest:
    def test_backtest_command(self, tmp_path, monkeypatch):
        """CSV temporal → backtest output contiene summary stats."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        csv_file = tmp_path / "test_data.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "market_id", "price", "volume"])
            base_ts = datetime(2024, 1, 1, 12, 0, 0)
            for i in range(100):
                ts = base_ts + timedelta(seconds=i * 60)
                cycle = (i // 10) % 4
                if cycle == 0:
                    price = "102.00"
                elif cycle == 1:
                    price = "100.00"
                elif cycle == 2:
                    price = "98.00"
                else:
                    price = "101.00"
                writer.writerow([ts.isoformat(), "btc-usd", price, "100.00"])

        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["backtest", "--input", str(csv_file)])
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert "Backtest Results" in result.output
        assert "Total signals" in result.output
        assert "Win rate" in result.output

    def test_backtest_missing_file(self):
        """Archivo inexistente → error."""
        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["backtest", "--input", "/nonexistent/file.csv"])
        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "not found" in result.output.lower()


class TestAnalyze:
    def test_analyze_with_data(self, tmp_path, monkeypatch):
        """Persist señales → analyze muestra datos."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        # Pre-populate DB with a signal
        from trady_ai.core.models import Signal
        from trady_ai.core.persistence import init_core_tables, persist_signal
        from trady_ai.db.database import init_db

        db = init_db(db_path)
        init_core_tables(db)
        signal = Signal(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            market_id="btc-usd",
            direction="LONG",
            confidence=0.85,
            strategy_name="markov_persistence",
        )
        persist_signal(db, signal)

        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--market", "btc-usd"])
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
        assert "btc-usd" in result.output
        assert "LONG" in result.output
        assert "markov_persistence" in result.output

    def test_analyze_no_data(self):
        """analyze con mercado sin datos → mensaje informativo."""
        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "--market", "unknown-market"])
        assert result.exit_code == 0
        assert "No signals found" in result.output


class TestRun:
    def test_run_command_no_events(self):
        """run sin eventos → mensaje 'No events'."""
        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--market", "btc-usd"])
        assert result.exit_code == 0
        assert "No events" in result.output


class TestCapture:
    def test_capture_command_no_markets(self):
        """capture sin --markets ni active_markets → mensaje informativo."""
        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["capture"])
        assert result.exit_code == 0
        assert "No markets" in result.output


# ── Paper Trading CLI Tests (T-011) ─────────────────────────────────────────────


class TestPaperTradeCLI:
    """Paper trading CLI commands — S8, S9, S10, S11."""

    def test_paper_trade_group_exists(self):
        """paper-trade group is registered on the CLI."""
        runner = CliRunner()
        result = runner.invoke(cli, ["paper-trade", "--help"])
        assert result.exit_code == 0
        assert "Paper Trading" in result.output or "paper" in result.output.lower()

    def test_session_command_help(self):
        """paper-trade session --help shows options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["paper-trade", "session", "--help"])
        assert result.exit_code == 0
        assert "--domain" in result.output
        assert "--scope" in result.output
        assert "--markets" in result.output
        assert "--non-interactive" in result.output

    def test_session_missing_domain_errors(self):
        """paper-trade session without --domain fails."""
        runner = CliRunner()
        result = runner.invoke(cli, ["paper-trade", "session"])
        assert result.exit_code != 0
        assert "domain" in result.output.lower()

    def test_status_shows_day_progress(self, tmp_path, monkeypatch):
        """paper-trade status shows day N/30 with reflection report count."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        # Seed some reflection reports
        from trady_ai.core.persistence import init_core_tables
        from trady_ai.db.database import init_db

        db = init_db(db_path)
        init_core_tables(db)
        now = datetime.now(UTC).isoformat()
        for i in range(3):
            db.execute(
                """INSERT INTO reflection_reports
                   (scope, domain, mode, period_start, period_end, report_data, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ["daily", "PM-5M", "dry_run", now, now, "{}", now],
            )

        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["paper-trade", "status"])
        assert result.exit_code == 0
        assert "Day" in result.output or "day" in result.output
        assert "3" in result.output or "30" in result.output

    def test_bundle_complete_day(self, tmp_path, monkeypatch):
        """bundle --day N for completed day generates manifest.json."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        from trady_ai.core.persistence import init_core_tables
        from trady_ai.db.database import init_db

        db = init_db(db_path)
        init_core_tables(db)

        now = datetime.now(UTC).isoformat()
        # Seed a reflection report
        db.execute(
            """INSERT INTO reflection_reports
               (scope, domain, mode, period_start, period_end, report_data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ["daily", "PM-5M", "dry_run", now, now, "{}", now],
        )
        # Seed events
        db.execute(
            """INSERT INTO event_store
               (event_id, market_id, price, volume, timestamp, event_type, raw_payload, captured_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ["evt-1", "0x123", "100.0", "10.0", now, "tick", "{}", now],
        )
        # Seed trades
        db["trades"].insert({
            "id": "t-1", "signal_id": "s-1",
            "position_id": "p-1", "action": "OPEN",
            "price": "100.0", "size": "1.0",
            "timestamp": now, "dry_run": 1,
        })

        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["paper-trade", "bundle", "--day", "1"])
        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        assert "manifest" in result.output.lower() or "bundle" in result.output.lower()

    def test_bundle_incomplete_day_fails(self, tmp_path, monkeypatch):
        """bundle --day N for incomplete day exits with error."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("TRADY_AI_DB_PATH", str(db_path))
        get_settings.cache_clear()

        from trady_ai.core.persistence import init_core_tables
        from trady_ai.db.database import init_db

        db = init_db(db_path)
        init_core_tables(db)

        get_settings.cache_clear()
        runner = CliRunner()
        result = runner.invoke(cli, ["paper-trade", "bundle", "--day", "99"])
        assert result.exit_code != 0

    # ── BINANCE-SPOT domain tests (REQ-CLI-001 through REQ-CLI-004) ──────────

    def test_domain_binance_spot_accepted(self, monkeypatch):
        """REQ-CLI-001: --domain BINANCE-SPOT accepted."""
        monkeypatch.setenv("TRADY_AI_ACTIVE_SYMBOLS", "BTCUSDT")
        monkeypatch.setenv("TRADY_AI_DRY_RUN", "true")
        get_settings.cache_clear()

        from unittest.mock import patch

        with patch("trady_ai.paper_trading.session.PaperTradingSession") as mock_pts:
            mock_session = mock_pts.return_value
            mock_report = mock_session.run_session.return_value
            mock_report.event_count = 0
            mock_report.trade_count = 0
            mock_report.stage_timestamps = {}
            mock_report.market_ids = []
            mock_report.reflection_report_id = None
            mock_report.calibration_state = "not_ready"
            mock_report.contract_results = []

            runner = CliRunner()
            result = runner.invoke(cli, [
                "paper-trade", "session",
                "--domain", "BINANCE-SPOT",
                "--markets", "BTCUSDT",
                "--non-interactive",
                "--duration", "1",
            ])

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"

    def test_domain_unknown_rejected_with_message(self, monkeypatch):
        """REQ-CLI-003: Unknown domain prints valid options and exits 1."""
        monkeypatch.setenv("TRADY_AI_ACTIVE_MARKETS", "0x123")
        monkeypatch.setenv("TRADY_AI_DRY_RUN", "true")
        get_settings.cache_clear()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "paper-trade", "session",
            "--domain", "NONSENSE",
            "--markets", "0xabc",
        ])

        assert result.exit_code == 1
        assert "Unknown domain" in result.output
        assert "NONSENSE" in result.output
        assert "BINANCE-SPOT" in result.output

    def test_binance_adapter_selection(self, monkeypatch):
        """REQ-CLI-002: BINANCE-SPOT → BinanceAdapter with ws/rest URLs."""
        monkeypatch.setenv("TRADY_AI_ACTIVE_SYMBOLS", "BTCUSDT")
        monkeypatch.setenv("TRADY_AI_DRY_RUN", "true")
        get_settings.cache_clear()

        from unittest.mock import patch

        with patch("trady_ai.adapters.binance.BinanceAdapter") as mock_ba:
            with patch("trady_ai.paper_trading.session.PaperTradingSession") as mock_pts:
                mock_session = mock_pts.return_value
                mock_report = mock_session.run_session.return_value
                mock_report.event_count = 0
                mock_report.trade_count = 0
                mock_report.stage_timestamps = {}
                mock_report.market_ids = []
                mock_report.reflection_report_id = None
                mock_report.calibration_state = "not_ready"
                mock_report.contract_results = []

                runner = CliRunner()
                result = runner.invoke(cli, [
                    "paper-trade", "session",
                    "--domain", "BINANCE-SPOT",
                    "--markets", "BTCUSDT",
                    "--non-interactive",
                    "--duration", "1",
                ])

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        mock_ba.assert_called_once()
        args, kwargs = mock_ba.call_args
        assert "ws_url" in kwargs or "wss://testnet" in str(args)
        assert "rest_url" in kwargs or "https://testnet" in str(args)

    def test_binance_symbols_lowercased(self, monkeypatch):
        """REQ-CLI-004: Symbols lowercased before passing to adapter."""
        monkeypatch.setenv("TRADY_AI_ACTIVE_SYMBOLS", "BTCUSDT,ETHUSDT")
        monkeypatch.setenv("TRADY_AI_DRY_RUN", "true")
        get_settings.cache_clear()

        from unittest.mock import patch

        with patch("trady_ai.adapters.binance.BinanceAdapter"):
            with patch("trady_ai.paper_trading.session.PaperTradingSession") as mock_pts:
                mock_session = mock_pts.return_value
                mock_report = mock_session.run_session.return_value
                mock_report.event_count = 0
                mock_report.trade_count = 0
                mock_report.stage_timestamps = {}
                mock_report.market_ids = ["btcusdt", "ethusdt"]
                mock_report.reflection_report_id = None
                mock_report.calibration_state = "not_ready"
                mock_report.contract_results = []

                runner = CliRunner()
                result = runner.invoke(cli, [
                    "paper-trade", "session",
                    "--domain", "BINANCE-SPOT",
                    "--non-interactive",
                    "--duration", "1",
                ])

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
        # Verify market_ids passed to run_session are lowercased
        mock_session.run_session.assert_called_once()
        call_kwargs = mock_session.run_session.call_args[1]
        assert call_kwargs["market_ids"] == ["btcusdt", "ethusdt"]

    def test_binance_empty_symbols_exits_1(self, monkeypatch):
        """REQ-CLI-004: No symbols configured → exit 1."""
        monkeypatch.setenv("TRADY_AI_ACTIVE_SYMBOLS", "")
        monkeypatch.setenv("TRADY_AI_DRY_RUN", "true")
        get_settings.cache_clear()

        runner = CliRunner()
        result = runner.invoke(cli, [
            "paper-trade", "session",
            "--domain", "BINANCE-SPOT",
            "--non-interactive",
        ])

        assert result.exit_code == 1
        assert "No symbols" in result.output or "symbols" in result.output.lower()
