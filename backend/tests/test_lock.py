from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import AppMeta
from app.lock import COOKIE, FREE_ATTEMPTS
from app.main import create_app

from .conftest import PASSCODE
from .test_db import meta


def state(client) -> str:
    return client.get("/api/lock/status").json()["state"]


def test_first_run_asks_for_setup(client):
    body = client.get("/api/lock/status").json()
    assert body == {"state": "setup", "idle_lock_minutes": 10, "retry_after_seconds": 0}


def test_setup_unlocks_and_creates_encrypted_files(unlocked, app, tmp_path):
    assert state(unlocked) == "unlocked"
    assert unlocked.cookies.get(COOKIE)
    assert (tmp_path / "vault.json").is_file()
    assert not (tmp_path / "kinsum.db").read_bytes().startswith(b"SQLite format 3")


def test_setup_only_once(unlocked):
    assert unlocked.post("/api/lock/setup", json={"name": "Alex", "passcode": "another-code"}).status_code == 409


def test_setup_rejects_short_passcode(client):
    response = client.post("/api/lock/setup", json={"name": "Alex", "passcode": "123"})
    assert response.status_code == 400
    assert state(client) == "setup"


def test_setup_refuses_when_key_file_is_missing(client, tmp_path):
    (tmp_path / "kinsum.db").write_bytes(b"existing encrypted data")
    assert client.post("/api/lock/setup", json={"name": "Alex", "passcode": PASSCODE}).status_code == 400


def test_lock_then_unlock(unlocked):
    assert unlocked.post("/api/lock/lock").status_code == 204
    assert state(unlocked) == "locked"
    assert unlocked.post("/api/lock/ping").status_code == 423

    wrong = unlocked.post("/api/lock/unlock", json={"passcode": "not-the-code"})
    assert wrong.status_code == 401
    assert state(unlocked) == "locked"

    assert unlocked.post("/api/lock/unlock", json={"passcode": PASSCODE}).status_code == 200
    assert state(unlocked) == "unlocked"


def test_lock_forgets_key_and_closes_database(unlocked, app):
    unlocked.post("/api/lock/lock")
    manager = app.state.lock
    assert manager._key is None and manager._db is None


def test_another_browser_needs_its_own_unlock(unlocked, app):
    other = TestClient(app, base_url="http://localhost")
    assert state(other) == "locked"
    assert other.post("/api/lock/ping").status_code == 423


def test_locking_ends_every_session(unlocked, app):
    other = TestClient(app, base_url="http://localhost")
    other.post("/api/lock/unlock", json={"passcode": PASSCODE})
    other.post("/api/lock/lock")
    assert state(unlocked) == "locked"


def test_idle_timeout_locks(unlocked, clock):
    clock.advance(9 * 60)
    assert state(unlocked) == "unlocked"
    clock.advance(60)
    assert state(unlocked) == "locked"


def test_activity_holds_off_idle_lock_but_status_checks_do_not(unlocked, clock):
    clock.advance(9 * 60)
    assert unlocked.post("/api/lock/ping").status_code == 204
    clock.advance(9 * 60)
    assert state(unlocked) == "unlocked"  # 9 minutes since the ping
    clock.advance(60)
    assert state(unlocked) == "locked"  # the status check above did not count


def test_background_idle_check_drops_the_key(unlocked, app, clock):
    clock.advance(10 * 60)
    app.state.lock.check_idle()
    assert app.state.lock._key is None


def test_wrong_guesses_are_slowed_down(unlocked, clock):
    unlocked.post("/api/lock/lock")
    for _ in range(FREE_ATTEMPTS):
        assert unlocked.post("/api/lock/unlock", json={"passcode": "guess-guess"}).status_code == 401

    blocked = unlocked.post("/api/lock/unlock", json={"passcode": PASSCODE})
    assert blocked.status_code == 429
    assert blocked.json()["retry_after_seconds"] == 30
    assert blocked.headers["Retry-After"] == "30"

    clock.advance(30)
    assert unlocked.post("/api/lock/unlock", json={"passcode": PASSCODE}).status_code == 200


def test_wait_doubles_after_each_further_wrong_guess(unlocked, clock):
    unlocked.post("/api/lock/lock")
    for _ in range(FREE_ATTEMPTS):
        unlocked.post("/api/lock/unlock", json={"passcode": "guess-guess"})
    clock.advance(30)
    response = unlocked.post("/api/lock/unlock", json={"passcode": "guess-guess"})
    assert response.status_code == 401
    assert response.json()["retry_after_seconds"] == 60


def test_change_passcode(unlocked):
    bad = unlocked.post("/api/lock/change-passcode", json={"current": "wrong-code", "new": "brand-new-code"})
    assert bad.status_code == 400
    ok = unlocked.post("/api/lock/change-passcode", json={"current": PASSCODE, "new": "brand-new-code"})
    assert ok.status_code == 204

    unlocked.post("/api/lock/lock")
    assert unlocked.post("/api/lock/unlock", json={"passcode": PASSCODE}).status_code == 401
    assert unlocked.post("/api/lock/unlock", json={"passcode": "brand-new-code"}).status_code == 200


def test_change_passcode_needs_a_session(client):
    client.post("/api/lock/setup", json={"name": "Alex", "passcode": PASSCODE})
    client.cookies.clear()
    response = client.post("/api/lock/change-passcode", json={"current": PASSCODE, "new": "brand-new-code"})
    assert response.status_code == 423


def test_data_routes_get_the_database_only_when_unlocked(app, unlocked):
    from app.lock import get_db

    @app.get("/api/test-meta")
    def read_meta(db: Session = Depends(get_db)) -> dict:
        return {"has_created_at": db.get(AppMeta, "created_at") is not None}

    app.router.routes.insert(0, app.router.routes.pop())  # ahead of the frontend catch-all

    assert unlocked.get("/api/test-meta").json() == {"has_created_at": True}
    unlocked.post("/api/lock/lock")
    assert unlocked.get("/api/test-meta").status_code == 423


def test_data_survives_a_restart(unlocked, app, tmp_path):
    created = meta(app.state.lock._db, "created_at")
    app.state.lock.lock()

    restarted = create_app(data_dir=tmp_path, idle_lock_minutes=10)
    try:
        client = TestClient(restarted, base_url="http://localhost")
        assert state(client) == "locked"
        assert client.post("/api/lock/unlock", json={"passcode": PASSCODE}).status_code == 200
        assert meta(restarted.state.lock._db, "created_at") == created
    finally:
        restarted.state.lock.lock()


# ---- recovery key -------------------------------------------------------------
def setup_with_key(client) -> str:
    response = client.post("/api/lock/setup", json={"name": "Alex", "passcode": PASSCODE})
    assert response.status_code == 201
    return response.json()["recovery_key"]


def recover(client, recovery_key, new_passcode="after-recovery"):
    return client.post("/api/lock/recover", json={"recovery_key": recovery_key, "new_passcode": new_passcode})


def test_setup_gives_a_recovery_key(client):
    key = setup_with_key(client)
    assert len(key) == 29
    assert client.get("/api/lock/recovery-key").json()["created"]


def test_recovery_key_resets_the_passcode(client):
    old_key = setup_with_key(client)
    client.post("/api/lock/lock")

    response = recover(client, old_key)
    assert response.status_code == 200
    new_key = response.json()["recovery_key"]
    assert new_key != old_key
    assert state(client) == "unlocked"

    client.post("/api/lock/lock")
    assert client.post("/api/lock/unlock", json={"passcode": PASSCODE}).status_code == 401
    assert client.post("/api/lock/unlock", json={"passcode": "after-recovery"}).status_code == 200
    client.post("/api/lock/lock")
    assert recover(client, old_key).status_code == 401  # a used key stops working
    assert recover(client, new_key).status_code == 200


def test_wrong_recovery_key(client):
    setup_with_key(client)
    client.post("/api/lock/lock")
    assert recover(client, "AAAAA-AAAAA-AAAAA-AAAAA-AAAAA").status_code == 401
    assert recover(client, "not a key").status_code == 401
    assert state(client) == "locked"


def test_recovery_with_short_passcode_costs_no_attempt(client, app):
    key = setup_with_key(client)
    client.post("/api/lock/lock")
    assert recover(client, key, new_passcode="123").status_code == 400
    assert app.state.lock._failures == 0


def test_recovery_guesses_share_the_wait_with_passcode_guesses(client):
    key = setup_with_key(client)
    client.post("/api/lock/lock")
    for _ in range(FREE_ATTEMPTS):
        client.post("/api/lock/unlock", json={"passcode": "guess-guess"})
    assert recover(client, key).status_code == 429


def test_make_new_recovery_key_needs_session_and_passcode(client):
    old_key = setup_with_key(client)
    assert client.post("/api/lock/recovery-key", json={"passcode": "wrong-code"}).status_code == 400
    response = client.post("/api/lock/recovery-key", json={"passcode": PASSCODE})
    assert response.status_code == 200
    new_key = response.json()["recovery_key"]

    client.post("/api/lock/lock")
    assert client.post("/api/lock/recovery-key", json={"passcode": PASSCODE}).status_code == 423
    assert client.get("/api/lock/recovery-key").status_code == 423
    assert recover(client, old_key).status_code == 401
    assert recover(client, new_key).status_code == 200
