import os
import sqlite3

import pytest

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
    assert meta(db, "schema_version") == "1"
    db.close()
