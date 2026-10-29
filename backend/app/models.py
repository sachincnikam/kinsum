"""Household tables: members, accounts and who owns which account.

Money is stored as integer cents. Balances are from the household's point of view:
what you have is positive, what you owe (credit cards, loans) is negative.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

ROLES = ("adult", "teen", "child")
# "household": sees and manages everything. "own": sees only accounts they own (alone or shared).
ACCESS = ("household", "own")
ACCOUNT_TYPES = ("checking", "savings", "credit_card", "brokerage", "retirement", "loan")
LIABILITY_TYPES = ("credit_card", "loan")

# Member colours: distinct from each other and readable on white.
MEMBER_COLOURS = ("#2563EB", "#059669", "#D97706", "#DB2777", "#7C3AED", "#0891B2", "#DC2626", "#4B5563")


def _now() -> datetime:
    return datetime.now(UTC)


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    colour: Mapped[str] = mapped_column(String(7))
    role: Mapped[str] = mapped_column(String(10), default="adult")
    access: Mapped[str] = mapped_column(String(10), default="household")
    # The member's passcode slot in vault.json. Set = this member can sign in.
    slot_id: Mapped[str | None] = mapped_column(String(16), unique=True, default=None)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    @property
    def can_sign_in(self) -> bool:
        return self.slot_id is not None


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))  # the bank's name for it, e.g. "Total Checking"
    institution: Mapped[str] = mapped_column(String(80))
    nickname: Mapped[str | None] = mapped_column(String(60), default=None)
    last4: Mapped[str | None] = mapped_column(String(4), default=None)  # never the full number
    type: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    opening_balance_cents: Mapped[int] = mapped_column(Integer, default=0)
    opening_date: Mapped[date | None] = mapped_column(Date, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    owners: Mapped[list[AccountOwner]] = relationship(
        back_populates="account", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def owner_ids(self) -> list[int]:
        return sorted(o.member_id for o in self.owners)

    @property
    def display_name(self) -> str:
        return self.nickname or f"{self.institution} {self.name}"


class AccountOwner(Base):
    __tablename__ = "account_owners"

    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), primary_key=True)

    account: Mapped[Account] = relationship(back_populates="owners")


CATEGORY_KINDS = ("income", "expense", "investment", "transfer")

# Category colours: dark enough that the icon reads on its own lightly tinted tile.
CATEGORY_COLOURS = (
    "#7C3AED",  # violet
    "#2563EB",  # blue
    "#0E7490",  # cyan
    "#0F766E",  # teal
    "#047857",  # green
    "#4D7C0F",  # lime
    "#B45309",  # amber
    "#C2410C",  # orange
    "#DC2626",  # red
    "#DB2777",  # pink
    "#4F46E5",  # indigo
    "#475569",  # slate
)


class Category(Base):
    """Two levels: groups (no parent) and their subcategories, which share the group's kind.

    No row means "Uncategorized" (category_id is null wherever categories are used).
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), default=None)
    kind: Mapped[str] = mapped_column(String(12))
    icon: Mapped[str] = mapped_column(String(40))  # a Lucide icon name, e.g. "shopping-cart"
    colour: Mapped[str] = mapped_column(String(7))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
