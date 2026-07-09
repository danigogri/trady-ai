from trady_ai.db.database import init_db


def test_db_creation(tmp_path):
    """Verifica que init_db crea el archivo SQLite."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    assert db_path.exists(), "El archivo .db debería existir post-init"


def test_db_metadata_table(tmp_path):
    """Verifica que la tabla _metadata existe post-init."""
    db_path = tmp_path / "test.db"
    db = init_db(db_path)
    tables = db.table_names()
    assert "_metadata" in tables, "La tabla _metadata debería existir"


def test_db_idempotent(tmp_path):
    """Verifica que llamar init_db dos veces no falla ni duplica."""
    db_path = tmp_path / "test.db"
    init_db(db_path)  # Primera llamada (idempotencia)
    db2 = init_db(db_path)  # Segunda llamada

    # Debe seguir siendo la misma tabla (sin duplicación)
    tables = db2.table_names()
    assert tables.count("_metadata") == 1

    # metadata debe tener las columnas correctas (namedtuples: index, name, type)
    cols = [c.name if hasattr(c, "name") else c[1] for c in db2["_metadata"].columns]
    assert "key" in cols
    assert "value" in cols
