"""Members, accounts and account owners.

Revision ID: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.create_table(
        "members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("colour", sa.String(7), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("access", sa.String(10), nullable=False),
        sa.Column("slot_id", sa.String(16), unique=True),
        sa.Column("is_archived", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("institution", sa.String(80), nullable=False),
        sa.Column("nickname", sa.String(60)),
        sa.Column("last4", sa.String(4)),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("opening_balance_cents", sa.Integer, nullable=False),
        sa.Column("opening_date", sa.Date),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "account_owners",
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("member_id", sa.Integer, sa.ForeignKey("members.id"), primary_key=True),
    )
