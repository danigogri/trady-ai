from datetime import datetime
from decimal import Decimal

import pytest

from trady_ai.config.runtime_config import RuntimeConfig
from trady_ai.config.settings import Settings
from trady_ai.core.models import MarketInput


@pytest.fixture
def tmp_settings(tmp_path):
    """Settings con db_path en directorio temporal."""
    return Settings(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def tmp_db(tmp_settings):
    """Database initialized in tmp_path."""
    from trady_ai.db.database import init_db

    return init_db(tmp_settings.db_path)


@pytest.fixture
def sample_runtime_config():
    """RuntimeConfig with default values."""
    return RuntimeConfig()


@pytest.fixture
def sample_market_input():
    """Sample MarketInput for testing."""
    return MarketInput(
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        market_id="btc-usd",
        price=Decimal("50000.00"),
        volume=Decimal("100.50"),
        source="csv",
    )


@pytest.fixture
def tmp_event_store_db(tmp_path):
    """Database with event_store table initialized."""
    import sqlite3

    import sqlite_utils

    from trady_ai.core.persistence import init_event_store

    conn = sqlite3.connect(str(tmp_path / "event_store_test.db"), check_same_thread=False)
    db = sqlite_utils.Database(conn)
    init_event_store(db)
    return db
