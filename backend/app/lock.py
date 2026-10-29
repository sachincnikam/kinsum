"""App lock: passcode setup, unlock, lock, idle auto-lock and the session cookie.

While locked, the database key exists nowhere in memory and the database is closed.
Unlocking opens it and gives the browser a session cookie; every /api route except
the few in PUBLIC_PATHS needs that cookie (see LockMiddleware), so new routes are
protected by default. Locking (button, idle timeout or quitting) forgets the key and
ends every session.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from sqlalchemy import select

from .db import Database, WrongKey
from .models import MEMBER_COLOURS, Member
from .vault import Unlocked, Vault, VaultError, check_passcode

COOKIE = "kinsum_session"
PUBLIC_PATHS = {
    "/api/health",
    "/api/lock/status",
    "/api/lock/setup",
    "/api/lock/unlock",
    "/api/lock/recover",
}

# Wrong passcodes: the first few are free, then each one doubles the wait (max 15 minutes).
FREE_ATTEMPTS = 5
FIRST_DELAY = 30
MAX_DELAY = 15 * 60


class LockManager:
    def __init__(self, data_dir: Path, idle_minutes: int, clock: Callable[[], float] = time.monotonic):
        self.vault = Vault(data_dir / "vault.json")
        self.db_path = data_dir / "kinsum.db"
        self.idle_seconds = idle_minutes * 60
        self.clock = clock
        self._lock = threading.RLock()
        self._db: Database | None = None
        self._key: bytes | None = None
        self._sessions: dict[str, str] = {}  # session token -> passcode slot that opened it
        self._last_activity = 0.0
        self._failures = 0
        self._blocked_until = 0.0

    # ---- state --------------------------------------------------------------
    @property
    def is_set_up(self) -> bool:
        return self.vault.exists()

    def retry_after(self) -> int:
        return max(0, int(self._blocked_until - self.clock() + 0.999))

    def check_idle(self) -> None:
        with self._lock:
            if self._db is not None and self.clock() - self._last_activity >= self.idle_seconds:
                self.lock()

    def is_valid(self, token: str | None) -> bool:
        with self._lock:
            self.check_idle()
            return token is not None and token in self._sessions

    def slot_of(self, token: str | None) -> str | None:
        """Which passcode slot (so which member) a session belongs to."""
        with self._lock:
            return self._sessions.get(token) if token else None

    def touch(self) -> None:
        with self._lock:
            self._last_activity = self.clock()

    # ---- actions ------------------------------------------------------------
    def _open(self, unlocked: Unlocked, db: Database | None = None) -> str:
        db = db or Database(self.db_path, unlocked.key)
        with self._lock:
            if self._db is not None:
                db.close()
            else:
                self._db, self._key = db, unlocked.key
            token = secrets.token_urlsafe(32)
            self._sessions[token] = unlocked.slot_id
            self._last_activity = self.clock()
            return token

    def setup(self, name: str, passcode: str) -> tuple[str, str]:
        """First run: the first adult and their passcode. Returns a session token and the
        new recovery key (to print)."""
        with self._lock:
            if self.db_path.exists() and not self.vault.exists():
                raise VaultError(
                    "A Kinsum database already exists here but its key file (vault.json) is missing."
                )
            unlocked = self.vault.create(passcode)
            recovery_key = self.vault.set_recovery_key(unlocked.key)
            token = self._open(unlocked)
            with self.transaction() as s:
                s.add(Member(name=name, colour=MEMBER_COLOURS[0], role="adult", access="household",
                             slot_id=unlocked.slot_id))
            return token, recovery_key

    def _guess(self, attempt: Callable[[], Unlocked | None]) -> Unlocked | None:
        """Passcode and recovery-key guesses share one counter, so neither is a way around the wait."""
        if self.retry_after() > 0:
            raise TooManyAttempts(self.retry_after())
        unlocked = attempt()
        if unlocked is None:
            self._failures += 1
            if self._failures >= FREE_ATTEMPTS:
                delay = min(MAX_DELAY, FIRST_DELAY * 2 ** (self._failures - FREE_ATTEMPTS))
                self._blocked_until = self.clock() + delay
            return None
        self._failures, self._blocked_until = 0, 0.0
        return unlocked

    def unlock(self, passcode: str) -> str | None:
        """Returns a session token, or None for a wrong passcode."""
        with self._lock:
            unlocked = self._guess(lambda: self.vault.unlock(passcode))
            return None if unlocked is None else self._open(unlocked)

    def recover(
        self, recovery_key: str, new_passcode: str, member_id: int | None = None
    ) -> tuple[str, str] | None:
        """Forgotten passcode: the recovery key sets a new passcode and opens the app.

        With more than one adult signing in, member_id says whose passcode to reset; without
        it, NeedsChoice lists them. The used recovery key is replaced, since it has now been
        typed in. Returns a session token and the new recovery key, or None for a wrong key.
        """
        with self._lock:
            check_passcode(new_passcode)  # before the guess, so a typo here costs no attempt
            unlocked = self._guess(lambda: self.vault.unlock_recovery(recovery_key))
            if unlocked is None:
                return None
            db = Database(self.db_path, unlocked.key)
            try:
                slot_id = self._slot_to_reset(db, member_id)
                self._check_unique(new_passcode, slot_id)
                self.vault.change_passcode(slot_id, unlocked.key, new_passcode)
                new_key = self.vault.set_recovery_key(unlocked.key)
            except BaseException:
                db.close()
                raise
            return self._open(Unlocked(unlocked.key, slot_id), db), new_key

    def _slot_to_reset(self, db: Database, member_id: int | None) -> str:
        slots = self.vault.passcode_slot_ids()
        with db._sessions() as s:
            members = s.scalars(
                select(Member).where(Member.slot_id.is_not(None), Member.is_archived.is_(False))
            ).all()
            if member_id is not None:
                match = next((m for m in members if m.id == member_id and m.slot_id in slots), None)
                if match is None:
                    raise VaultError("That person cannot sign in.")
                return match.slot_id
            if len(slots) == 1:
                return slots[0]
            raise NeedsChoice([{"id": m.id, "name": m.name} for m in members])

    def _check_unique(self, passcode: str, own_slot: str | None) -> None:
        """Two people with the same passcode could not be told apart when unlocking."""
        other = self.vault.unlock(passcode)
        if other is not None and other.slot_id != own_slot:
            raise VaultError("Someone else already uses that passcode. Choose a different one.")

    def recovery_created(self) -> str | None:
        return self.vault.recovery_created()

    def _check_own(self, token: str | None, passcode: str) -> Unlocked:
        """The passcode must be the signed-in person's own, not just any household passcode."""
        unlocked = self.vault.unlock(passcode)
        if unlocked is None or unlocked.slot_id != self.slot_of(token):
            raise VaultError("That passcode is not right.")
        return unlocked

    def new_recovery_key(self, token: str | None, passcode: str) -> str:
        with self._lock:
            unlocked = self._check_own(token, passcode)
            return self.vault.set_recovery_key(unlocked.key)

    def change_passcode(self, token: str | None, current: str, new: str) -> None:
        with self._lock:
            check_passcode(new)
            unlocked = self._check_own(token, current)
            self._check_unique(new, unlocked.slot_id)
            self.vault.change_passcode(unlocked.slot_id, unlocked.key, new)

    def add_passcode(self, passcode: str) -> str:
        """A new passcode slot for another adult. Returns its slot id."""
        with self._lock:
            if self._key is None:
                raise VaultError("Kinsum is locked.")
            check_passcode(passcode)
            self._check_unique(passcode, None)
            return self.vault.add_slot(self._key, passcode)

    def remove_passcode(self, slot_id: str) -> None:
        """Takes away a sign-in and ends any session it has open."""
        with self._lock:
            self.vault.remove_slot(slot_id)
            for token in [t for t, s in self._sessions.items() if s == slot_id]:
                del self._sessions[token]

    def lock(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
            self._db = self._key = None
            self._sessions.clear()

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self._lock:
            db = self._db
        if db is None:
            raise HTTPException(status_code=423, detail="Kinsum is locked.")
        with db._sessions.begin() as s:
            yield s

    def session(self) -> Iterator[Session]:
        with self._lock:
            db = self._db
        if db is None:
            raise HTTPException(status_code=423, detail="Kinsum is locked.")
        yield from db.session()


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


class NeedsChoice(Exception):
    """Recovery with several adults: say whose passcode to reset."""

    def __init__(self, members: list[dict]):
        self.members = members


class LockMiddleware(BaseHTTPMiddleware):
    """Every /api route needs an unlocked session unless it is listed in PUBLIC_PATHS."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in PUBLIC_PATHS:
            manager: LockManager = request.app.state.lock
            if not manager.is_valid(request.cookies.get(COOKIE)):
                return JSONResponse({"detail": "Kinsum is locked."}, status_code=423)
            manager.touch()
        return await call_next(request)


# ---- routes -------------------------------------------------------------------
router = APIRouter(prefix="/api/lock", tags=["lock"])


class PasscodeIn(BaseModel):
    passcode: str


class SetupIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    passcode: str


class ChangePasscodeIn(BaseModel):
    current: str
    new: str


class RecoverIn(BaseModel):
    recovery_key: str
    new_passcode: str
    member_id: int | None = None  # whose passcode, when more than one adult signs in


def get_manager(request: Request) -> LockManager:
    return request.app.state.lock


def get_db(request: Request) -> Iterator[Session]:
    """Dependency for routes that read or write data."""
    yield from get_manager(request).session()


def get_me(request: Request, db: Session = Depends(get_db)) -> Member | None:
    """The member whose passcode opened this session (None for a passcode from before
    members existed, until they say who they are)."""
    slot = get_manager(request).slot_of(request.cookies.get(COOKIE))
    if slot is None:
        return None
    return db.scalar(select(Member).where(Member.slot_id == slot, Member.is_archived.is_(False)))


def require_me(me: Member | None = Depends(get_me)) -> Member:
    if me is None:
        raise HTTPException(status_code=409, detail="Tell Kinsum who you are first.")
    return me


def require_household(me: Member = Depends(require_me)) -> Member:
    """Only adults with whole-household access may change the household or the recovery key."""
    if me.access != "household":
        raise HTTPException(status_code=403, detail="Only an adult with whole-household access can do this.")
    return me


def _set_cookie(response: Response, token: str) -> None:
    # Session cookie only (gone when the browser closes), unreadable by page scripts,
    # and never sent by other websites.
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", path="/api")


@router.get("/status")
def status(request: Request, manager: LockManager = Depends(get_manager)) -> dict:
    """Checking the status does not count as activity, so polling it never delays the idle lock."""
    if not manager.is_set_up:
        state = "setup"
    elif manager.is_valid(request.cookies.get(COOKIE)):
        state = "unlocked"
    else:
        state = "locked"
    return {
        "state": state,
        "idle_lock_minutes": manager.idle_seconds // 60,
        "retry_after_seconds": manager.retry_after(),
    }


@router.post("/setup", status_code=201)
def setup(body: SetupIn, response: Response, manager: LockManager = Depends(get_manager)) -> dict:
    if manager.is_set_up:
        raise HTTPException(status_code=409, detail="Kinsum is already set up.")
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Please enter your name.")
    try:
        token, recovery_key = manager.setup(name, body.passcode)
    except VaultError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _set_cookie(response, token)
    return {"state": "unlocked", "recovery_key": recovery_key}


def _too_many(e: TooManyAttempts) -> JSONResponse:
    return JSONResponse(
        {"detail": "Too many wrong tries. Try again shortly.", "retry_after_seconds": e.retry_after},
        status_code=429,
        headers={"Retry-After": str(e.retry_after)},
    )


@router.post("/unlock")
def unlock(body: PasscodeIn, response: Response, manager: LockManager = Depends(get_manager)):
    if not manager.is_set_up:
        raise HTTPException(status_code=409, detail="Kinsum is not set up yet.")
    try:
        token = manager.unlock(body.passcode)
    except TooManyAttempts as e:
        return _too_many(e)
    except (VaultError, WrongKey) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    if token is None:
        return JSONResponse(
            {"detail": "That passcode is not right.", "retry_after_seconds": manager.retry_after()},
            status_code=401,
        )
    _set_cookie(response, token)
    return {"state": "unlocked"}


@router.post("/recover")
def recover(body: RecoverIn, response: Response, manager: LockManager = Depends(get_manager)):
    if not manager.is_set_up:
        raise HTTPException(status_code=409, detail="Kinsum is not set up yet.")
    try:
        result = manager.recover(body.recovery_key, body.new_passcode, body.member_id)
    except TooManyAttempts as e:
        return _too_many(e)
    except NeedsChoice as e:
        return JSONResponse(
            {"detail": "Whose passcode should be reset?", "choices": e.members}, status_code=409
        )
    except (VaultError, WrongKey) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if result is None:
        return JSONResponse(
            {"detail": "That recovery key is not right.", "retry_after_seconds": manager.retry_after()},
            status_code=401,
        )
    token, recovery_key = result
    _set_cookie(response, token)
    return {"state": "unlocked", "recovery_key": recovery_key}


@router.get("/recovery-key", dependencies=[Depends(require_household)])
def recovery_key_info(manager: LockManager = Depends(get_manager)) -> dict:
    """Whether a recovery key exists and when it was made. Never returns the key itself."""
    return {"created": manager.recovery_created()}


@router.post("/recovery-key", dependencies=[Depends(require_household)])
def make_recovery_key(body: PasscodeIn, request: Request, manager: LockManager = Depends(get_manager)) -> dict:
    try:
        return {"recovery_key": manager.new_recovery_key(request.cookies.get(COOKIE), body.passcode)}
    except VaultError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/lock", status_code=204)
def lock(response: Response, manager: LockManager = Depends(get_manager)) -> None:
    manager.lock()
    response.delete_cookie(COOKIE, path="/api")


@router.post("/ping", status_code=204)
def ping() -> None:
    """The screen calls this when someone is using it, to hold off the idle lock."""


@router.post("/change-passcode", status_code=204)
def change_passcode(
    body: ChangePasscodeIn, request: Request, manager: LockManager = Depends(get_manager)
) -> None:
    try:
        manager.change_passcode(request.cookies.get(COOKIE), body.current, body.new)
    except VaultError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
