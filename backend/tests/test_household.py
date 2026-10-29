import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.models import Member

from .conftest import PASSCODE

SAM_CODE = "sam-passcode-7"
JORDAN_CODE = "jordan-passcode-9"


def new_browser(app) -> TestClient:
    return TestClient(app, base_url="http://localhost")


def add_member(client, name, **extra) -> dict:
    response = client.post("/api/members", json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def add_sign_in(client, member_id, passcode):
    return client.post(f"/api/members/{member_id}/sign-in", json={"passcode": passcode})


def signed_in_as(app, passcode) -> TestClient:
    browser = new_browser(app)
    assert browser.post("/api/lock/unlock", json={"passcode": passcode}).status_code == 200
    return browser


def add_account(client, owner_ids, **extra) -> dict:
    body = {"name": "Total Checking", "institution": "Example Bank", "type": "checking",
            "owner_ids": owner_ids, **extra}
    response = client.post("/api/accounts", json=body)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def me(unlocked) -> dict:
    return unlocked.get("/api/me").json()["member"]


@pytest.fixture
def jordan(unlocked, app):
    """A second adult who signs in with access to their own accounts only."""
    member = add_member(unlocked, "Jordan", access="own")
    assert add_sign_in(unlocked, member["id"], JORDAN_CODE).status_code == 200
    return member, signed_in_as(app, JORDAN_CODE)


# ---- me and setup ---------------------------------------------------------------
def test_setup_creates_the_first_adult(me):
    assert me["name"] == "Alex"
    assert me["role"] == "adult" and me["access"] == "household"
    assert me["can_sign_in"] and me["is_me"]


def test_setup_needs_a_name(client):
    assert client.post("/api/lock/setup", json={"passcode": PASSCODE}).status_code == 422
    assert client.post("/api/lock/setup", json={"name": "  ", "passcode": PASSCODE}).status_code == 400


def test_passcode_from_before_members_asks_who_you_are(unlocked, app):
    with app.state.lock.transaction() as s:
        s.execute(delete(Member))
    assert unlocked.get("/api/me").json() == {"member": None}
    assert unlocked.get("/api/members").status_code == 409

    created = unlocked.post("/api/me", json={"name": "Alex"})
    assert created.status_code == 201
    assert created.json()["member"]["access"] == "household"
    assert unlocked.get("/api/me").json()["member"]["name"] == "Alex"
    assert unlocked.post("/api/me", json={"name": "Again"}).status_code == 409


# ---- members --------------------------------------------------------------------
def test_add_members_of_every_role(unlocked, me):
    sam = add_member(unlocked, "Sam")
    teen = add_member(unlocked, "Riley", role="teen")
    child = add_member(unlocked, "Mia", role="child", colour="#DB2777")
    assert child["colour"] == "#DB2777"
    colours = {me["colour"], sam["colour"], teen["colour"]}
    assert len(colours) == 3  # picked automatically, all different
    names = [m["name"] for m in unlocked.get("/api/members").json()]
    assert names == ["Alex", "Sam", "Riley", "Mia"]


@pytest.mark.parametrize("body", [{"role": "grandparent"}, {"colour": "#123456"}, {"access": "everything"}])
def test_member_choices_are_checked(unlocked, body):
    assert unlocked.post("/api/members", json={"name": "Sam", **body}).status_code == 400


def test_second_adult_signs_in_as_themselves(unlocked, app):
    sam = add_member(unlocked, "Sam")
    response = add_sign_in(unlocked, sam["id"], SAM_CODE)
    assert response.status_code == 200 and response.json()["can_sign_in"]

    browser = signed_in_as(app, SAM_CODE)
    assert browser.get("/api/me").json()["member"]["name"] == "Sam"
    assert unlocked.get("/api/me").json()["member"]["name"] == "Alex"


def test_two_people_cannot_share_a_passcode(unlocked):
    sam = add_member(unlocked, "Sam")
    response = add_sign_in(unlocked, sam["id"], PASSCODE)
    assert response.status_code == 400
    assert "different" in response.json()["detail"]


def test_only_adults_sign_in(unlocked):
    child = add_member(unlocked, "Mia", role="child")
    assert add_sign_in(unlocked, child["id"], SAM_CODE).status_code == 400


def test_adult_with_sign_in_cannot_become_a_child(unlocked):
    sam = add_member(unlocked, "Sam")
    add_sign_in(unlocked, sam["id"], SAM_CODE)
    assert unlocked.patch(f"/api/members/{sam['id']}", json={"role": "teen"}).status_code == 400


def test_last_household_adult_keeps_access(unlocked, me):
    assert unlocked.patch(f"/api/members/{me['id']}", json={"access": "own"}).status_code == 400

    sam = add_member(unlocked, "Sam")
    add_sign_in(unlocked, sam["id"], SAM_CODE)
    assert unlocked.patch(f"/api/members/{me['id']}", json={"access": "own"}).status_code == 200


def test_cannot_archive_or_remove_yourself(unlocked, me):
    assert unlocked.patch(f"/api/members/{me['id']}", json={"is_archived": True}).status_code == 400
    assert unlocked.delete(f"/api/members/{me['id']}/sign-in").status_code == 400


def test_archiving_takes_away_sign_in_and_ends_their_session(unlocked, jordan):
    member, browser = jordan
    response = unlocked.patch(f"/api/members/{member['id']}", json={"is_archived": True})
    assert response.status_code == 200
    assert not response.json()["can_sign_in"]
    assert browser.get("/api/me").status_code == 423
    assert browser.post("/api/lock/unlock", json={"passcode": JORDAN_CODE}).status_code == 401
    assert [m["name"] for m in unlocked.get("/api/members").json()] == ["Alex"]
    assert len(unlocked.get("/api/members?include_archived=true").json()) == 2


def test_removing_a_sign_in(unlocked, jordan):
    member, browser = jordan
    assert unlocked.delete(f"/api/members/{member['id']}/sign-in").status_code == 200
    assert browser.get("/api/me").status_code == 423
    assert new_browser(browser.app).post("/api/lock/unlock", json={"passcode": JORDAN_CODE}).status_code == 401


# ---- access -----------------------------------------------------------------------
def test_own_access_adult_cannot_manage_the_household(jordan):
    member, browser = jordan
    assert browser.post("/api/members", json={"name": "Someone"}).status_code == 403
    assert browser.patch(f"/api/members/{member['id']}", json={"access": "household"}).status_code == 403
    assert browser.get("/api/lock/recovery-key").status_code == 403
    assert browser.post("/api/lock/recovery-key", json={"passcode": JORDAN_CODE}).status_code == 403


def test_own_access_sees_only_own_and_shared_accounts(unlocked, me, jordan):
    member, browser = jordan
    mine = add_account(unlocked, [me["id"]], nickname="Alex's card")
    shared = add_account(unlocked, [me["id"], member["id"]], nickname="Joint")
    theirs = add_account(browser, [member["id"]], nickname="Jordan's savings", type="savings")

    assert [a["nickname"] for a in browser.get("/api/accounts").json()] == ["Joint", "Jordan's savings"]
    assert len(unlocked.get("/api/accounts").json()) == 3
    assert browser.patch(f"/api/accounts/{mine['id']}", json={"nickname": "x"}).status_code == 404
    assert browser.patch(f"/api/accounts/{shared['id']}", json={"nickname": "Joint account"}).status_code == 200
    # They cannot take themselves off an account (it would vanish from their view) ...
    assert browser.patch(f"/api/accounts/{theirs['id']}", json={"owner_ids": [me["id"]]}).status_code == 400
    # ... or add an account they do not own.
    body = {"name": "X", "institution": "Y", "type": "checking", "owner_ids": [me["id"]]}
    assert browser.post("/api/accounts", json=body).status_code == 400


def test_passcode_change_needs_your_own_passcode(jordan):
    _, browser = jordan
    body = {"current": PASSCODE, "new": "brand-new-code"}  # Alex's passcode, not Jordan's
    assert browser.post("/api/lock/change-passcode", json=body).status_code == 400
    body = {"current": JORDAN_CODE, "new": PASSCODE}  # already Alex's
    assert browser.post("/api/lock/change-passcode", json=body).status_code == 400
    body = {"current": JORDAN_CODE, "new": "brand-new-code"}
    assert browser.post("/api/lock/change-passcode", json=body).status_code == 204


# ---- accounts ---------------------------------------------------------------------
def test_add_account(unlocked, me):
    account = add_account(unlocked, [me["id"]], last4="4821", opening_balance_cents=125_050,
                          opening_date="2026-04-01")
    assert account["display_name"] == "Example Bank Total Checking"
    assert account["last4"] == "4821" and account["currency"] == "USD"
    assert account["opening_balance_cents"] == 125_050
    assert account["opening_date"] == "2026-04-01"
    assert account["owner_ids"] == [me["id"]]
    assert not account["is_liability"]


def test_nickname_is_shown_everywhere(unlocked, me):
    account = add_account(unlocked, [me["id"]], nickname="  Grocery card  ", type="credit_card",
                          opening_balance_cents=-42_000)
    assert account["display_name"] == "Grocery card"
    assert account["is_liability"]
    renamed = unlocked.patch(f"/api/accounts/{account['id']}", json={"nickname": ""}).json()
    assert renamed["nickname"] is None
    assert renamed["display_name"] == "Example Bank Total Checking"


@pytest.mark.parametrize("last4", ["123456789012", "12a4", "123"])
def test_full_account_numbers_are_refused(unlocked, me, last4):
    body = {"name": "Checking", "institution": "Example Bank", "type": "checking",
            "owner_ids": [me["id"]], "last4": last4}
    response = unlocked.post("/api/accounts", json=body)
    assert response.status_code == 400
    assert "last 4 digits" in response.json()["detail"]


def test_shared_account_and_owner_checks(unlocked, me):
    sam = add_member(unlocked, "Sam")
    shared = add_account(unlocked, [sam["id"], me["id"], me["id"]])
    assert shared["owner_ids"] == sorted([me["id"], sam["id"]])
    counts = {m["name"]: m["account_count"] for m in unlocked.get("/api/members").json()}
    assert counts == {"Alex": 1, "Sam": 1}

    body = {"name": "X", "institution": "Y", "type": "checking"}
    assert unlocked.post("/api/accounts", json={**body, "owner_ids": []}).status_code == 422
    assert unlocked.post("/api/accounts", json={**body, "owner_ids": [999]}).status_code == 400
    assert unlocked.post("/api/accounts", json={**body, "type": "piggy_bank", "owner_ids": [me["id"]]}).status_code == 400

    unlocked.patch(f"/api/members/{sam['id']}", json={"is_archived": True})
    assert unlocked.post("/api/accounts", json={**body, "owner_ids": [sam["id"]]}).status_code == 400


def test_archive_and_restore_account(unlocked, me):
    account = add_account(unlocked, [me["id"]])
    unlocked.patch(f"/api/accounts/{account['id']}", json={"is_active": False})
    assert unlocked.get("/api/accounts").json() == []
    assert len(unlocked.get("/api/accounts?include_archived=true").json()) == 1
    unlocked.patch(f"/api/accounts/{account['id']}", json={"is_active": True})
    assert len(unlocked.get("/api/accounts").json()) == 1


# ---- recovery with several adults ---------------------------------------------------
def recover(client, key, member_id=None, new_passcode="after-recovery"):
    body = {"recovery_key": key, "new_passcode": new_passcode}
    if member_id is not None:
        body["member_id"] = member_id
    return client.post("/api/lock/recover", json=body)


@pytest.fixture
def recovery_key(unlocked):
    return unlocked.post("/api/lock/recovery-key", json={"passcode": PASSCODE}).json()["recovery_key"]


def test_recovery_asks_whose_passcode(unlocked, app, me, jordan, recovery_key):
    member, _ = jordan
    unlocked.post("/api/lock/lock")
    browser = new_browser(app)

    choice = recover(browser, recovery_key)
    assert choice.status_code == 409
    assert choice.json()["choices"] == [{"id": me["id"], "name": "Alex"}, {"id": member["id"], "name": "Jordan"}]
    assert app.state.lock._failures == 0  # the key was right, so it is not a wrong try

    done = recover(browser, recovery_key, member_id=member["id"])
    assert done.status_code == 200
    assert browser.get("/api/me").json()["member"]["name"] == "Jordan"

    browser.post("/api/lock/lock")
    assert new_browser(app).post("/api/lock/unlock", json={"passcode": JORDAN_CODE}).status_code == 401
    assert new_browser(app).post("/api/lock/unlock", json={"passcode": "after-recovery"}).status_code == 200
    assert new_browser(app).post("/api/lock/unlock", json={"passcode": PASSCODE}).status_code == 200


def test_recovery_cannot_pick_someone_without_sign_in(unlocked, jordan, recovery_key):
    child = add_member(unlocked, "Mia", role="child")
    unlocked.post("/api/lock/lock")
    assert recover(unlocked, recovery_key, member_id=child["id"]).status_code == 400


def test_recovery_passcode_must_not_match_another_adult(unlocked, me, jordan, recovery_key):
    unlocked.post("/api/lock/lock")
    response = recover(unlocked, recovery_key, member_id=me["id"], new_passcode=JORDAN_CODE)
    assert response.status_code == 400


# ---- parallel requests ------------------------------------------------------------
def test_parallel_requests_do_not_crash(unlocked, me):
    """Pages load several things at once. This once crashed the whole app (wrong pool)."""
    from concurrent.futures import ThreadPoolExecutor

    add_account(unlocked, [me["id"]])
    paths = ["/api/members", "/api/accounts", "/api/me"] * 60
    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = list(pool.map(lambda p: unlocked.get(p).status_code, paths))
    assert set(codes) == {200}
