"""Categories: two levels (groups and subcategories), each with a kind, an icon and a colour.

Everyone signed in can read them; changing them needs whole-household access, because the
whole household shares one category list. Categories are archived, not deleted, except when
merged into another one, which first points everything that used them at the other one.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .db import Base
from .lock import get_db, require_household, require_me
from .models import CATEGORY_COLOURS, CATEGORY_KINDS, Category, Member

router = APIRouter(prefix="/api/categories", tags=["categories"])

ICON_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    parent_id: int | None = None
    kind: str | None = None  # needed for a group; a subcategory takes its group's kind
    icon: str
    colour: str | None = None  # a subcategory defaults to its group's colour


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    parent_id: int | None = None  # send null to turn a subcategory into a group
    kind: str | None = None
    icon: str | None = None
    colour: str | None = None
    is_archived: bool | None = None


class MergeIn(BaseModel):
    into_id: int


def category_out(c: Category) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "parent_id": c.parent_id,
        "kind": c.kind,
        "icon": c.icon,
        "colour": c.colour,
        "is_archived": c.is_archived,
    }


# ---- checks -------------------------------------------------------------------
def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _get(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


def _children(db: Session, category: Category) -> list[Category]:
    return list(db.scalars(select(Category).where(Category.parent_id == category.id)))


def _check_icon(icon: str) -> str:
    # Any Lucide-style name is stored; the screen shows a plain tag icon for names it does not know.
    if len(icon) > 40 or not ICON_NAME.fullmatch(icon):
        raise _bad("Unknown icon.")
    return icon


def _check_colour(colour: str) -> str:
    if colour not in CATEGORY_COLOURS:
        raise _bad(f"Unknown colour: {colour}.")
    return colour


def _check_kind(kind: str | None) -> str:
    if kind not in CATEGORY_KINDS:
        raise _bad("Choose whether this is income, spending, investment or transfer.")
    return kind


def _group(db: Session, parent_id: int) -> Category:
    parent = db.get(Category, parent_id)
    if parent is None or parent.is_archived:
        raise _bad("That group does not exist.")
    if parent.parent_id is not None:
        raise _bad("Subcategories cannot have their own subcategories.")
    return parent


def _check_name_free(db: Session, name: str, parent_id: int | None, except_id: int | None = None) -> str:
    name = name.strip()
    if not name:
        raise _bad("Please enter a name.")
    query = select(Category).where(
        func.lower(Category.name) == name.lower(),
        Category.is_archived.is_(False),
        Category.parent_id.is_(None) if parent_id is None else Category.parent_id == parent_id,
    )
    clash = db.scalar(query)
    if clash is not None and clash.id != except_id:
        where = "a group" if parent_id is None else "a subcategory in this group"
        raise _bad(f"There is already {where} called {clash.name}.")
    return name


def _point_references(db: Session, source_id: int, target_id: int) -> None:
    """Move everything that uses source over to target: any column, in any table, that points
    at categories (transactions, rules, budgets... as they are added), except the hierarchy."""
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            if fk.column.table.name == "categories" and fk.parent is not Category.__table__.c.parent_id:
                db.execute(update(table).where(fk.parent == source_id).values({fk.parent.name: target_id}))


# ---- routes -------------------------------------------------------------------
@router.get("")
def list_categories(
    include_archived: bool = False, db: Session = Depends(get_db), me: Member = Depends(require_me)
) -> list[dict]:
    """Groups in their order, each followed by its subcategories A to Z."""
    everything = db.scalars(select(Category)).all()
    shown = [c for c in everything if include_archived or not c.is_archived]
    groups = sorted((c for c in shown if c.parent_id is None), key=lambda c: (c.sort_order, c.name.lower()))
    result = []
    for group in groups:
        result.append(category_out(group))
        kids = sorted((c for c in shown if c.parent_id == group.id), key=lambda c: c.name.lower())
        result.extend(category_out(c) for c in kids)
    return result


@router.post("", status_code=201)
def create_category(body: CategoryIn, db: Session = Depends(get_db), me: Member = Depends(require_household)) -> dict:
    icon = _check_icon(body.icon)
    if body.parent_id is None:
        kind = _check_kind(body.kind)
        if body.colour is None:
            raise _bad("Choose a colour.")
        colour = _check_colour(body.colour)
        last = db.scalar(select(func.max(Category.sort_order)).where(Category.parent_id.is_(None))) or 0
        sort_order = last + 10
    else:
        parent = _group(db, body.parent_id)
        kind = parent.kind
        colour = _check_colour(body.colour) if body.colour else parent.colour
        sort_order = 0
    category = Category(
        name=_check_name_free(db, body.name, body.parent_id),
        parent_id=body.parent_id,
        kind=kind,
        icon=icon,
        colour=colour,
        sort_order=sort_order,
    )
    db.add(category)
    db.commit()
    return category_out(category)


@router.patch("/{category_id}")
def update_category(
    category_id: int, body: CategoryPatch, db: Session = Depends(get_db), me: Member = Depends(require_household)
) -> dict:
    category = _get(db, category_id)
    fields = body.model_fields_set
    children = _children(db, category)

    if "parent_id" in fields and body.parent_id != category.parent_id:
        if body.parent_id is None:  # a subcategory becomes a group, keeping its kind
            category.sort_order = (
                db.scalar(select(func.max(Category.sort_order)).where(Category.parent_id.is_(None))) or 0
            ) + 10
        else:
            if children:
                raise _bad("Move or merge this group's subcategories first.")
            if body.parent_id == category.id:
                raise _bad("A category cannot be inside itself.")
            parent = _group(db, body.parent_id)
            category.kind = parent.kind
        category.parent_id = body.parent_id

    if body.name is not None or "parent_id" in fields:
        category.name = _check_name_free(db, body.name or category.name, category.parent_id, category.id)
    if body.icon is not None:
        category.icon = _check_icon(body.icon)
    if body.colour is not None:
        category.colour = _check_colour(body.colour)
    if body.kind is not None and body.kind != category.kind:
        if category.parent_id is not None:
            raise _bad("A subcategory always has its group's kind. Change the group instead.")
        category.kind = _check_kind(body.kind)
        for child in children:
            child.kind = category.kind

    if body.is_archived is not None and body.is_archived != category.is_archived:
        if not body.is_archived and category.parent_id is not None:
            parent = db.get(Category, category.parent_id)
            if parent.is_archived:
                raise _bad(f"Restore the {parent.name} group first.")
        if not body.is_archived:
            _check_name_free(db, category.name, category.parent_id, category.id)
        category.is_archived = body.is_archived
        for child in children:  # a group takes its subcategories with it, both ways
            child.is_archived = body.is_archived

    db.commit()
    return category_out(category)


@router.post("/{category_id}/merge")
def merge_category(
    category_id: int, body: MergeIn, db: Session = Depends(get_db), me: Member = Depends(require_household)
) -> dict:
    """Fold one category into another. Its subcategories move across (same names are merged
    too), everything that used it now uses the other one, and it is removed."""
    source, target = _get(db, category_id), _get(db, body.into_id)
    if source.id == target.id:
        raise _bad("Choose a different category to merge into.")
    if target.is_archived:
        raise _bad("You cannot merge into an archived category.")
    if target.parent_id == source.id:
        raise _bad("You cannot merge a group into one of its own subcategories.")
    if source.kind != target.kind:
        raise _bad("Both categories must be the same kind (income, spending, investment or transfer).")

    children = _children(db, source)
    if children and target.parent_id is not None:
        raise _bad("A group with subcategories can only be merged into another group.")
    for child in children:
        twin = db.scalar(
            select(Category).where(
                Category.parent_id == target.id,
                func.lower(Category.name) == child.name.lower(),
                Category.id != child.id,
            )
        )
        if twin is not None:
            _point_references(db, child.id, twin.id)
            db.delete(child)
        else:
            child.parent_id = target.id

    _point_references(db, source.id, target.id)
    db.flush()
    db.delete(source)
    db.commit()
    return category_out(target)
