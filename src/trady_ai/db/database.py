from pathlib import Path

import sqlite_utils

from trady_ai.config import Settings


def init_db(db_path: Path) -> sqlite_utils.Database:
    """Initialize SQLite database at the given path."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(db_path)
    tbl = db["_metadata"]
    assert isinstance(tbl, sqlite_utils.db.Table)
    tbl.create(
        {"key": str, "value": str},
        pk="key",
        if_not_exists=True,
    )
    return db


def get_db(settings: Settings) -> sqlite_utils.Database:
    """Get database instance from settings."""
    return init_db(settings.db_path)
