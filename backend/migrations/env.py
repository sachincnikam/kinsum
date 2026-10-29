"""Alembic runs here with the already-open encrypted connection (see db.py), never a URL."""

from alembic import context

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.db import Base

connection = context.config.attributes["connection"]
context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()
