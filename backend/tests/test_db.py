import os
import sqlite3

import pytest
from sqlalchemy import text

from app.db import AppMeta, Database, WrongKey


def meta(db: Database, key: str) -> str:
    with db._sessions() as s:
        return s.get(AppMeta, key).value


def test_database_file_is_encrypted(tmp_path):
    path = tmp_path / "kinsum.db"
    db = Database(path, os.urandom(32))
    with db._sessions.begin() as s:
        s.add(AppMeta(key="marker", value="family-secret-marker"))
    db.close()

    raw = path.read_bytes()
    assert not raw.startswith(b"SQLite format 3")
    assert b"family-secret-marker" not in raw
    plain = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            plain.execute("SELECT * FROM app_meta").fetchall()
    finally:
        plain.close()


def test_wrong_key_is_refused(tmp_path):
    path = tmp_path / "kinsum.db"
    Database(path, os.urandom(32)).close()
    with pytest.raises(WrongKey):
        Database(path, os.urandom(32))


def test_data_survives_reopening(tmp_path):
    path, key = tmp_path / "kinsum.db", os.urandom(32)
    db = Database(path, key)
    created = meta(db, "created_at")
    db.close()

    db = Database(path, key)
    assert meta(db, "created_at") == created
    with db.engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0003"
    db.close()


def test_step_2_database_is_upgraded(tmp_path):
    """Databases made before migrations existed have app_meta but no alembic_version."""
    path, key = tmp_path / "kinsum.db", os.urandom(32)
    db = Database(path, key)
    with db.engine.begin() as conn:
        conn.execute(text("DROP TABLE categories"))
        conn.execute(text("DROP TABLE account_owners"))
        conn.execute(text("DROP TABLE accounts"))
        conn.execute(text("DROP TABLE members"))
        conn.execute(text("DROP TABLE alembic_version"))
        conn.execute(text("INSERT INTO app_meta VALUES ('schema_version', '1')"))
    db.close()

    db = Database(path, key)
    with db.engine.connect() as conn:
        tables = {r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))}
    assert {"app_meta", "members", "accounts", "account_owners", "categories"} <= tables
    assert meta(db, "schema_version") == "1"  # old rows are kept
    db.close()


def test_uses_a_normal_connection_pool(tmp_path):
    from sqlalchemy.pool import QueuePool

    db = Database(tmp_path / "kinsum.db", os.urandom(32))
    assert isinstance(db.engine.pool, QueuePool)
    db.close()
