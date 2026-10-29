"""App meta table (created without migrations in Phase 1 step 2, so only if missing).

Revision ID: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    if "app_meta" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "app_meta",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(256), nullable=False),
    )
