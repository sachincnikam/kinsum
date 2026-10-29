"""Household members and accounts.

Everyone signed in can see the member list (names are needed to show account owners).
Adults with "own" access see only accounts they own, alone or shared, and may add or edit
those; changing members, sign-ins and access needs whole-household access. There is always
at least one adult who can sign in with whole-household access.
"""

from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .lock import COOKIE, PasscodeIn, get_db, get_manager, get_me, require_household, require_me
from .models import ACCESS, ACCOUNT_TYPES, LIABILITY_TYPES, MEMBER_COLOURS, ROLES, Account, AccountOwner, Member
from .vault import VaultError

router = APIRouter(prefix="/api", tags=["household"])


# ---- shapes -------------------------------------------------------------------
class MemberIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    role: str = "adult"
    colour: str | None = None
    access: str = "household"


class MemberPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    role: str | None = None
    colour: str | None = None
    access: str | None = None
    is_archived: bool | None = None


class MeIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    institution: str = Field(min_length=1, max_length=80)
    nickname: str | None = Field(default=None, max_length=60)
    last4: str | None = None
    type: str
    opening_balance_cents: int = 0
    opening_date: date | None = None
    owner_ids: list[int] = Field(min_length=1)


class AccountPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    institution: str | None = Field(default=None, min_length=1, max_length=80)
    nickname: str | None = Field(default=None, max_length=60)
    last4: str | None = None
    type: str | None = None
    opening_balance_cents: int | None = None
    opening_date: date | None = None
    owner_ids: list[int] | None = Field(default=None, min_length=1)
    is_active: bool | None = None


def member_out(m: Member, me: Member | None, account_count: int = 0) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "colour": m.colour,
        "role": m.role,
        "access": m.access,
        "can_sign_in": m.can_sign_in,
        "is_archived": m.is_archived,
        "is_me": me is not None and m.id == me.id,
        "account_count": account_count,
    }


def account_out(a: Account) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "institution": a.institution,
        "nickname": a.nickname,
        "display_name": a.display_name,
        "last4": a.last4,
        "type": a.type,
        "is_liability": a.type in LIABILITY_TYPES,
        "currency": a.currency,
        "opening_balance_cents": a.opening_balance_cents,
        "opening_date": a.opening_date.isoformat() if a.opening_date else None,
        "is_active": a.is_active,
        "owner_ids": a.owner_ids,
    }


# ---- checks -------------------------------------------------------------------
def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def _check_choice(value: str, allowed: tuple[str, ...], what: str) -> None:
    if value not in allowed:
        raise _bad(f"Unknown {what}: {value}.")


def _clean(text: str, what: str) -> str:
    text = text.strip()
    if not text:
        raise _bad(f"Please enter a {what}.")
    return text


def _clean_last4(value: str | None) -> str | None:
    """Only the last 4 digits are ever stored. A longer number is refused, not trimmed,
    so a full account number never reaches the database."""
    value = (value or "").strip()
    if not value:
        return None
    if not re.fullmatch(r"\d{4}", value):
        raise _bad("Enter only the last 4 digits of the account number, never the full number.")
    return value


def _next_colour(db: Session) -> str:
    used = set(db.scalars(select(Member.colour).where(Member.is_archived.is_(False))))
    return next((c for c in MEMBER_COLOURS if c not in used), MEMBER_COLOURS[0])


def _ensure_an_admin_remains(db: Session) -> None:
    db.flush()
    admins = db.scalar(
        select(func.count()).select_from(Member).where(
            Member.slot_id.is_not(None),
            Member.is_archived.is_(False),
            Member.role == "adult",
            Member.access == "household",
        )
    )
    if not admins:
        raise _bad("At least one adult who can sign in must keep whole-household access.")


def _get_member(db: Session, member_id: int) -> Member:
    member = db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    return member


def _visible(account: Account, me: Member) -> bool:
    return me.access == "household" or me.id in account.owner_ids


def _set_owners(db: Session, account: Account, owner_ids: list[int], me: Member) -> None:
    owner_ids = sorted(set(owner_ids))
    found = db.scalars(select(Member).where(Member.id.in_(owner_ids), Member.is_archived.is_(False))).all()
    if len(found) != len(owner_ids):
        raise _bad("Every owner must be a current household member.")
    if me.access != "household" and me.id not in owner_ids:
        raise _bad("You must stay an owner of accounts you manage.")
    account.owners = [AccountOwner(member_id=i) for i in owner_ids]


# ---- me -----------------------------------------------------------------------
@router.get("/me")
def read_me(me: Member | None = Depends(get_me)) -> dict:
    return {"member": member_out(me, me) if me else None}


@router.post("/me", status_code=201)
def create_me(body: MeIn, request: Request, db: Session = Depends(get_db), me: Member | None = Depends(get_me)) -> dict:
    """For a passcode set up before members existed: say who you are, once."""
    if me is not None:
        raise HTTPException(status_code=409, detail="You are already in the household.")
    slot = get_manager(request).slot_of(request.cookies.get(COOKIE))
    member = Member(name=_clean(body.name, "name"), colour=_next_colour(db), role="adult",
                    access="household", slot_id=slot)
    db.add(member)
    db.commit()
    return {"member": member_out(member, member)}


# ---- members ------------------------------------------------------------------
@router.get("/members")
def list_members(
    include_archived: bool = False, db: Session = Depends(get_db), me: Member = Depends(require_me)
) -> list[dict]:
    query = select(Member).order_by(Member.is_archived, Member.id)
    if not include_archived:
        query = query.where(Member.is_archived.is_(False))
    counts = dict(
        db.execute(
            select(AccountOwner.member_id, func.count())
            .join(Account)
            .where(Account.is_active.is_(True))
            .group_by(AccountOwner.member_id)
        ).all()
    )
    return [member_out(m, me, counts.get(m.id, 0)) for m in db.scalars(query)]


@router.post("/members", status_code=201)
def create_member(body: MemberIn, db: Session = Depends(get_db), me: Member = Depends(require_household)) -> dict:
    _check_choice(body.role, ROLES, "role")
    _check_choice(body.access, ACCESS, "access")
    if body.colour is not None:
        _check_choice(body.colour, MEMBER_COLOURS, "colour")
    member = Member(
        name=_clean(body.name, "name"),
        role=body.role,
        access=body.access,
        colour=body.colour or _next_colour(db),
    )
    db.add(member)
    db.commit()
    return member_out(member, me)


@router.patch("/members/{member_id}")
def update_member(
    member_id: int,
    body: MemberPatch,
    request: Request,
    db: Session = Depends(get_db),
    me: Member = Depends(require_household),
) -> dict:
    member = _get_member(db, member_id)
    if body.name is not None:
        member.name = _clean(body.name, "name")
    if body.colour is not None:
        _check_choice(body.colour, MEMBER_COLOURS, "colour")
        member.colour = body.colour
    if body.role is not None:
        _check_choice(body.role, ROLES, "role")
        if body.role != "adult" and member.can_sign_in:
            raise _bad("Only adults can sign in. Remove their sign-in first.")
        member.role = body.role
    if body.access is not None:
        _check_choice(body.access, ACCESS, "access")
        member.access = body.access

    slot_to_remove = None
    if body.is_archived is not None and body.is_archived != member.is_archived:
        if body.is_archived and member.id == me.id:
            raise _bad("You cannot archive yourself.")
        member.is_archived = body.is_archived
        if body.is_archived and member.slot_id:
            slot_to_remove, member.slot_id = member.slot_id, None

    _ensure_an_admin_remains(db)
    if slot_to_remove:
        get_manager(request).remove_passcode(slot_to_remove)
    db.commit()
    return member_out(member, me)


@router.post("/members/{member_id}/sign-in")
def add_sign_in(
    member_id: int,
    body: PasscodeIn,
    request: Request,
    db: Session = Depends(get_db),
    me: Member = Depends(require_household),
) -> dict:
    """Give an adult their own passcode. They should type it themselves."""
    member = _get_member(db, member_id)
    if member.is_archived or member.role != "adult":
        raise _bad("Only current adult members can sign in.")
    if member.can_sign_in:
        raise _bad(f"{member.name} can already sign in.")
    manager = get_manager(request)
    try:
        member.slot_id = manager.add_passcode(body.passcode)
    except VaultError as e:
        raise _bad(str(e)) from e
    try:
        db.commit()
    except Exception:
        manager.remove_passcode(member.slot_id)
        raise
    return member_out(member, me)


@router.delete("/members/{member_id}/sign-in")
def remove_sign_in(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    me: Member = Depends(require_household),
) -> dict:
    member = _get_member(db, member_id)
    if member.id == me.id:
        raise _bad("You cannot remove your own sign-in.")
    if not member.can_sign_in:
        return member_out(member, me)
    slot, member.slot_id = member.slot_id, None
    _ensure_an_admin_remains(db)
    get_manager(request).remove_passcode(slot)
    db.commit()
    return member_out(member, me)


# ---- accounts -----------------------------------------------------------------
@router.get("/accounts")
def list_accounts(
    include_archived: bool = False, db: Session = Depends(get_db), me: Member = Depends(require_me)
) -> list[dict]:
    query = select(Account).order_by(Account.is_active.desc(), Account.id)
    if not include_archived:
        query = query.where(Account.is_active.is_(True))
    return [account_out(a) for a in db.scalars(query) if _visible(a, me)]


@router.post("/accounts", status_code=201)
def create_account(body: AccountIn, db: Session = Depends(get_db), me: Member = Depends(require_me)) -> dict:
    _check_choice(body.type, ACCOUNT_TYPES, "account type")
    account = Account(
        name=_clean(body.name, "account name"),
        institution=_clean(body.institution, "bank or institution"),
        nickname=(body.nickname or "").strip() or None,
        last4=_clean_last4(body.last4),
        type=body.type,
        opening_balance_cents=body.opening_balance_cents,
        opening_date=body.opening_date,
    )
    _set_owners(db, account, body.owner_ids, me)
    db.add(account)
    db.commit()
    return account_out(account)


@router.patch("/accounts/{account_id}")
def update_account(
    account_id: int, body: AccountPatch, db: Session = Depends(get_db), me: Member = Depends(require_me)
) -> dict:
    account = db.get(Account, account_id)
    if account is None or not _visible(account, me):
        raise HTTPException(status_code=404, detail="Account not found.")
    fields = body.model_fields_set
    if body.name is not None:
        account.name = _clean(body.name, "account name")
    if body.institution is not None:
        account.institution = _clean(body.institution, "bank or institution")
    if "nickname" in fields:
        account.nickname = (body.nickname or "").strip() or None
    if "last4" in fields:
        account.last4 = _clean_last4(body.last4)
    if body.type is not None:
        _check_choice(body.type, ACCOUNT_TYPES, "account type")
        account.type = body.type
    if body.opening_balance_cents is not None:
        account.opening_balance_cents = body.opening_balance_cents
    if "opening_date" in fields:
        account.opening_date = body.opening_date
    if body.owner_ids is not None:
        _set_owners(db, account, body.owner_ids, me)
    if body.is_active is not None:
        account.is_active = body.is_active
    db.commit()
    return account_out(account)
