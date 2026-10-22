"""The encrypted database (SQLCipher), opened only while the app is unlocked."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, String, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlcipher3 import dbapi2 as sqlcipher

SCHEMA_VERSION = 1


class Base(DeclarativeBase):
    pass


class AppMeta(Base):
    """Small key/value table: schema version, when the database was created."""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256))


class WrongKey(Exception):
    pass


class Database:
    def __init__(self, path: Path, key: bytes):
        self.path = path
        hex_key = key.hex()

        def connect():
            conn = sqlcipher.connect(str(path), check_same_thread=False)
            # Raw 256-bit key: the passcode was already stretched by the vault, so
            # SQLCipher's own key derivation is skipped.
            conn.execute(f"PRAGMA key = \"x'{hex_key}'\"")
            conn.execute("PRAGMA cipher_log_level = NONE")
            return conn

        self.engine: Engine = create_engine("sqlite://", creator=connect)
        event.listen(self.engine, "connect", _on_connect)
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT count(*) FROM sqlite_master"))
        except Exception as e:
            self.engine.dispose()
            raise WrongKey("The database could not be opened with this key.") from e

        Base.metadata.create_all(self.engine)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)
        with self._sessions.begin() as s:
            if s.get(AppMeta, "schema_version") is None:
                s.add(AppMeta(key="schema_version", value=str(SCHEMA_VERSION)))
                s.add(AppMeta(key="created_at", value=datetime.now(UTC).isoformat()))

    def session(self) -> Iterator[Session]:
        with self._sessions() as s:
            yield s

    def close(self) -> None:
        # Releases the file handles too (Windows will not delete or move an open file).
        self.engine.dispose()


def _on_connect(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA journal_mode = WAL")
    cur.close()
