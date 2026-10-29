"""Categories, with the starter set from the plan (fully editable afterwards).

Revision ID: 0003
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"

# (group, kind, icon, colour, [(subcategory, icon), ...])
STARTER = [
    ("Income", "income", "banknote", "#047857", [
        ("Salary", "briefcase"), ("Bonus", "award"), ("Interest", "percent"),
        ("Dividends", "trending-up"), ("Refunds", "rotate-ccw"), ("Other income", "circle-plus"),
    ]),
    ("Housing", "expense", "house", "#7C3AED", [
        ("Rent/Mortgage", "key-round"), ("Utilities", "zap"), ("Internet & phone", "wifi"),
        ("Maintenance", "wrench"), ("Home insurance", "shield"),
    ]),
    ("Food", "expense", "utensils", "#B45309", [
        ("Groceries", "shopping-cart"), ("Restaurants", "chef-hat"), ("Coffee", "coffee"), ("Delivery", "bike"),
    ]),
    ("Transportation", "expense", "car", "#475569", [
        ("Fuel", "fuel"), ("Car payment", "car-front"), ("Car insurance", "shield-check"),
        ("Parking & tolls", "circle-parking"), ("Rideshare", "car-taxi-front"), ("Transit", "train-front"),
    ]),
    ("Shopping", "expense", "shopping-bag", "#DB2777", [
        ("Clothing", "shirt"), ("Electronics", "smartphone"), ("Household", "sofa"),
        ("Online marketplaces", "package"),
    ]),
    ("Health", "expense", "heart-pulse", "#DC2626", [
        ("Medical", "stethoscope"), ("Pharmacy", "pill"), ("Fitness", "dumbbell"),
        ("Health insurance", "shield-plus"),
    ]),
    ("Lifestyle", "expense", "sparkles", "#2563EB", [
        ("Entertainment", "clapperboard"), ("Subscriptions", "repeat"), ("Travel", "plane"),
        ("Gifts", "gift"), ("Personal care", "scissors"),
    ]),
    ("Family & education", "expense", "users", "#0F766E", [
        ("Childcare", "baby"), ("School", "graduation-cap"), ("Pets", "paw-print"),
    ]),
    ("Financial", "expense", "landmark", "#C2410C", [
        ("Fees & interest", "receipt"), ("Taxes", "receipt-text"), ("Charity", "hand-heart"),
    ]),
    ("Investments", "investment", "chart-line", "#4F46E5", [
        ("Buy", "arrow-down-to-line"), ("Sell", "arrow-up-from-line"), ("Investment fees", "badge-percent"),
    ]),
    ("Transfers", "transfer", "arrow-left-right", "#0E7490", [
        ("Card payment", "credit-card"), ("Between accounts", "shuffle"),
        ("Investment contribution", "piggy-bank"),
    ]),
]


def upgrade() -> None:
    table = op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("categories.id")),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("icon", sa.String(40), nullable=False),
        sa.Column("colour", sa.String(7), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False),
        sa.Column("is_archived", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    now = datetime.now(UTC)
    rows, next_id = [], 1
    for order, (group, kind, icon, colour, children) in enumerate(STARTER, start=1):
        group_id = next_id
        rows.append(dict(id=group_id, name=group, parent_id=None, kind=kind, icon=icon, colour=colour,
                         sort_order=order * 10, is_archived=False, created_at=now))
        next_id += 1
        for name, child_icon in children:
            rows.append(dict(id=next_id, name=name, parent_id=group_id, kind=kind, icon=child_icon,
                             colour=colour, sort_order=0, is_archived=False, created_at=now))
            next_id += 1
    op.bulk_insert(table, rows)
