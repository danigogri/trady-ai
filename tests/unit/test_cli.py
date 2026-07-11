import csv
from datetime import datetime, timedelta

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
