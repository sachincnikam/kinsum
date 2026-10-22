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
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .db import Database, WrongKey
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
        self._slot_id: str | None = None
        self._key: bytes | None = None
        self._sessions: set[str] = set()
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

    def touch(self) -> None:
        with self._lock:
            self._last_activity = self.clock()

    # ---- actions ------------------------------------------------------------
    def _open(self, unlocked: Unlocked) -> str:
        db = Database(self.db_path, unlocked.key)
        with self._lock:
            if self._db is not None:
                db.close()
            else:
                self._db, self._key, self._slot_id = db, unlocked.key, unlocked.slot_id
            token = secrets.token_urlsafe(32)
            self._sessions.add(token)
            self._last_activity = self.clock()
            return token

    def setup(self, passcode: str) -> tuple[str, str]:
        """Returns a session token and the new recovery key (to print)."""
        with self._lock:
            if self.db_path.exists() and not self.vault.exists():
                raise VaultError(
                    "A Kinsum database already exists here but its key file (vault.json) is missing."
                )
            unlocked = self.vault.create(passcode)
            recovery_key = self.vault.set_recovery_key(unlocked.key)
            return self._open(unlocked), recovery_key

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

    def recover(self, recovery_key: str, new_passcode: str) -> tuple[str, str] | None:
        """Forgotten passcode: the recovery key sets a new passcode and opens the app.

        The used recovery key is replaced, since it has now been typed in. Returns a session
        token and the new recovery key, or None for a wrong recovery key.
        """
        with self._lock:
            check_passcode(new_passcode)  # before the guess, so a typo here costs no attempt
            unlocked = self._guess(lambda: self.vault.unlock_recovery(recovery_key))
            if unlocked is None:
                return None
            slots = self.vault.passcode_slot_ids()
            if len(slots) != 1:
                # Step 3 (one passcode per adult) adds choosing whose passcode to reset.
                raise VaultError("Choosing whose passcode to reset is not available yet.")
            self.vault.change_passcode(slots[0], unlocked.key, new_passcode)
            new_key = self.vault.set_recovery_key(unlocked.key)
            return self._open(unlocked), new_key

    def recovery_created(self) -> str | None:
        return self.vault.recovery_created()

    def new_recovery_key(self, passcode: str) -> str:
        with self._lock:
            unlocked = self.vault.unlock(passcode)
            if unlocked is None:
                raise VaultError("That passcode is not right.")
            return self.vault.set_recovery_key(unlocked.key)

    def change_passcode(self, current: str, new: str) -> None:
        with self._lock:
            check_passcode(new)
            unlocked = self.vault.unlock(current)
            if unlocked is None:
                raise VaultError("Current passcode is not right.")
            self.vault.change_passcode(unlocked.slot_id, unlocked.key, new)

    def lock(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
            self._db = self._key = self._slot_id = None
            self._sessions.clear()

    def session(self) -> Iterator[Session]:
        with self._lock:
            db = self._db
        if db is None:
            raise HTTPException(status_code=423, detail="Kinsum is locked.")
        yield from db.session()


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


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


class ChangePasscodeIn(BaseModel):
    current: str
    new: str


class RecoverIn(BaseModel):
    recovery_key: str
    new_passcode: str


def get_manager(request: Request) -> LockManager:
    return request.app.state.lock


def get_db(request: Request) -> Iterator[Session]:
    """Dependency for routes that read or write data."""
    yield from get_manager(request).session()


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
def setup(body: PasscodeIn, response: Response, manager: LockManager = Depends(get_manager)) -> dict:
    if manager.is_set_up:
        raise HTTPException(status_code=409, detail="Kinsum is already set up.")
    try:
        token, recovery_key = manager.setup(body.passcode)
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
        result = manager.recover(body.recovery_key, body.new_passcode)
    except TooManyAttempts as e:
        return _too_many(e)
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


@router.get("/recovery-key")
def recovery_key_info(manager: LockManager = Depends(get_manager)) -> dict:
    """Whether a recovery key exists and when it was made. Never returns the key itself."""
    return {"created": manager.recovery_created()}


@router.post("/recovery-key")
def make_recovery_key(body: PasscodeIn, manager: LockManager = Depends(get_manager)) -> dict:
    try:
        return {"recovery_key": manager.new_recovery_key(body.passcode)}
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
def change_passcode(body: ChangePasscodeIn, manager: LockManager = Depends(get_manager)) -> None:
    try:
        manager.change_passcode(body.current, body.new)
    except VaultError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
