import pytest
import sqlalchemy as sa

from app.db import Base

from .test_household import JORDAN_CODE, add_member, add_sign_in, signed_in_as


def categories(client, archived=False) -> list[dict]:
    return client.get(f"/api/categories{'?include_archived=true' if archived else ''}").json()


def find(client, name, archived=False) -> dict:
    return next(c for c in categories(client, archived) if c["name"] == name)


def create(client, **body):
    return client.post("/api/categories", json=body)


# ---- starter set ------------------------------------------------------------------
def test_starter_categories_come_with_icons(unlocked):
    cats = categories(unlocked)
    groups = [c["name"] for c in cats if c["parent_id"] is None]
    assert groups == ["Income", "Housing", "Food", "Transportation", "Shopping", "Health", "Lifestyle",
                      "Family & education", "Financial", "Investments", "Transfers"]
    assert all(c["icon"] and c["colour"] for c in cats)
    food = find(unlocked, "Food")
    assert [c["name"] for c in cats if c["parent_id"] == food["id"]] == ["Coffee", "Delivery", "Groceries", "Restaurants"]
    assert find(unlocked, "Card payment")["kind"] == "transfer"
    assert find(unlocked, "Dividends")["kind"] == "income"
    # No two subcategories share a name, so a flat picker is never ambiguous.
    names = [c["name"] for c in cats if c["parent_id"] is not None]
    assert len(names) == len(set(names))


# ---- add ------------------------------------------------------------------------
def test_add_group_and_subcategory(unlocked):
    group = create(unlocked, name="Hobbies", kind="expense", icon="palette", colour="#0F766E")
    assert group.status_code == 201
    group = group.json()
    sub = create(unlocked, name="Photography", parent_id=group["id"], icon="camera").json()
    assert sub["kind"] == "expense"
    assert sub["colour"] == "#0F766E"  # takes the group's colour unless one is picked
    # Groups keep their order: a new group goes after the starter ones (before nothing else).
    names = [c["name"] for c in categories(unlocked) if c["parent_id"] is None]
    assert names[-1] == "Hobbies"


def test_subcategory_takes_its_groups_kind(unlocked):
    food = find(unlocked, "Food")
    sub = create(unlocked, name="Bakery", parent_id=food["id"], kind="income", icon="cake").json()
    assert sub["kind"] == "expense"


@pytest.mark.parametrize(
    "body, message",
    [
        ({"name": "X", "kind": "expense", "icon": "palette"}, "colour"),
        ({"name": "X", "kind": "fun", "icon": "palette", "colour": "#0F766E"}, "income, spending"),
        ({"name": "X", "kind": "expense", "icon": "Not An Icon!", "colour": "#0F766E"}, "icon"),
        ({"name": "X", "kind": "expense", "icon": "palette", "colour": "#123456"}, "colour"),
        ({"name": "food", "kind": "expense", "icon": "palette", "colour": "#0F766E"}, "already"),
    ],
)
def test_add_is_checked(unlocked, body, message):
    response = create(unlocked, **body)
    assert response.status_code == 400
    assert message in response.json()["detail"]


def test_only_two_levels(unlocked):
    groceries = find(unlocked, "Groceries")
    response = create(unlocked, name="Organic", parent_id=groceries["id"], icon="carrot")
    assert response.status_code == 400


def test_same_name_allowed_in_different_groups(unlocked):
    housing = find(unlocked, "Housing")
    food = find(unlocked, "Food")
    assert create(unlocked, name="Snacks", parent_id=food["id"], icon="apple").status_code == 201
    assert create(unlocked, name="Snacks", parent_id=housing["id"], icon="apple").status_code == 201
    assert create(unlocked, name="snacks", parent_id=food["id"], icon="apple").status_code == 400


# ---- edit ---------------------------------------------------------------------------
def test_rename_and_change_icon_and_colour(unlocked):
    coffee = find(unlocked, "Coffee")
    response = unlocked.patch(f"/api/categories/{coffee['id']}", json={"name": "Coffee & tea", "icon": "cup-soda",
                                                                       "colour": "#4D7C0F"})
    assert response.status_code == 200
    assert response.json() | {"id": 0} == {"id": 0, "name": "Coffee & tea", "parent_id": coffee["parent_id"],
                                            "kind": "expense", "icon": "cup-soda", "colour": "#4D7C0F",
                                            "is_archived": False}


def test_changing_a_groups_kind_changes_its_subcategories(unlocked):
    investments = find(unlocked, "Investments")
    unlocked.patch(f"/api/categories/{investments['id']}", json={"kind": "transfer"})
    assert find(unlocked, "Buy")["kind"] == "transfer"
    buy = find(unlocked, "Buy")
    assert unlocked.patch(f"/api/categories/{buy['id']}", json={"kind": "income"}).status_code == 400


def test_move_subcategory_to_another_group(unlocked):
    delivery, lifestyle = find(unlocked, "Delivery"), find(unlocked, "Lifestyle")
    moved = unlocked.patch(f"/api/categories/{delivery['id']}", json={"parent_id": lifestyle["id"]}).json()
    assert moved["parent_id"] == lifestyle["id"]
    salary, income = find(unlocked, "Salary"), find(unlocked, "Income")
    moved = unlocked.patch(f"/api/categories/{salary['id']}", json={"parent_id": find(unlocked, "Food")["id"]}).json()
    assert moved["kind"] == "expense"  # it now follows its new group
    assert income["id"] != moved["parent_id"]


def test_subcategory_becomes_a_group_and_back(unlocked):
    pets = find(unlocked, "Pets")
    group = unlocked.patch(f"/api/categories/{pets['id']}", json={"parent_id": None}).json()
    assert group["parent_id"] is None
    assert [c["name"] for c in categories(unlocked) if c["parent_id"] is None][-1] == "Pets"
    # A group with subcategories cannot go inside another group.
    food = find(unlocked, "Food")
    assert unlocked.patch(f"/api/categories/{food['id']}", json={"parent_id": pets["id"]}).status_code == 400


# ---- archive --------------------------------------------------------------------------
def test_archiving_a_group_archives_its_subcategories(unlocked):
    family = find(unlocked, "Family & education")
    unlocked.patch(f"/api/categories/{family['id']}", json={"is_archived": True})
    names = [c["name"] for c in categories(unlocked)]
    assert "Family & education" not in names and "Pets" not in names
    assert find(unlocked, "Pets", archived=True)["is_archived"]

    pets = find(unlocked, "Pets", archived=True)
    response = unlocked.patch(f"/api/categories/{pets['id']}", json={"is_archived": False})
    assert response.status_code == 400 and "Restore the Family & education group first" in response.json()["detail"]

    unlocked.patch(f"/api/categories/{family['id']}", json={"is_archived": False})
    assert not find(unlocked, "Pets")["is_archived"]


def test_archived_name_can_be_reused(unlocked):
    coffee = find(unlocked, "Coffee")
    unlocked.patch(f"/api/categories/{coffee['id']}", json={"is_archived": True})
    assert create(unlocked, name="Coffee", parent_id=coffee["parent_id"], icon="coffee").status_code == 201
    # ...but the old one cannot come back while the name is taken.
    assert unlocked.patch(f"/api/categories/{coffee['id']}", json={"is_archived": False}).status_code == 400


# ---- merge ------------------------------------------------------------------------------
def test_merge_subcategories(unlocked):
    coffee, restaurants = find(unlocked, "Coffee"), find(unlocked, "Restaurants")
    response = unlocked.post(f"/api/categories/{coffee['id']}/merge", json={"into_id": restaurants["id"]})
    assert response.status_code == 200
    names = [c["name"] for c in categories(unlocked, archived=True)]
    assert "Coffee" not in names and "Restaurants" in names


def test_merge_groups_moves_and_folds_subcategories(unlocked):
    lifestyle, shopping = find(unlocked, "Lifestyle"), find(unlocked, "Shopping")
    create(unlocked, name="Household", parent_id=lifestyle["id"], icon="sofa")  # also in Shopping
    unlocked.post(f"/api/categories/{lifestyle['id']}/merge", json={"into_id": shopping["id"]})
    cats = categories(unlocked)
    in_shopping = sorted(c["name"] for c in cats if c["parent_id"] == shopping["id"])
    assert in_shopping == ["Clothing", "Electronics", "Entertainment", "Gifts", "Household",
                           "Online marketplaces", "Personal care", "Subscriptions", "Travel"]
    assert "Lifestyle" not in [c["name"] for c in cats]


@pytest.mark.parametrize(
    "source, target",
    [("Salary", "Groceries"),  # different kinds
     ("Food", "Groceries"),  # into its own subcategory
     ("Food", "Coffee"),  # a group with subcategories into a subcategory
     ("Food", "Food")],
)
def test_merge_is_checked(unlocked, source, target):
    s, t = find(unlocked, source), find(unlocked, target)
    assert unlocked.post(f"/api/categories/{s['id']}/merge", json={"into_id": t["id"]}).status_code == 400


@pytest.fixture
def uses_categories(app):
    """A stand-in for a future table that points at categories (like transactions)."""
    table = sa.Table(
        "test_uses", Base.metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id")),
    )
    yield table
    Base.metadata.remove(table)


def test_merge_points_everything_at_the_new_category(unlocked, app, uses_categories):
    coffee, restaurants = find(unlocked, "Coffee"), find(unlocked, "Restaurants")
    db = app.state.lock._db
    uses_categories.create(db.engine)
    with db.engine.begin() as conn:
        conn.execute(uses_categories.insert(), [{"category_id": coffee["id"]}, {"category_id": restaurants["id"]}])

    unlocked.post(f"/api/categories/{coffee['id']}/merge", json={"into_id": restaurants["id"]})
    with db.engine.connect() as conn:
        used = [r.category_id for r in conn.execute(sa.select(uses_categories.c.category_id))]
    assert used == [restaurants["id"], restaurants["id"]]


# ---- who may change them ---------------------------------------------------------------------
def test_own_access_adult_can_read_but_not_change(unlocked, app):
    jordan = add_member(unlocked, "Jordan", access="own")
    add_sign_in(unlocked, jordan["id"], JORDAN_CODE)
    browser = signed_in_as(app, JORDAN_CODE)
    assert len(categories(browser)) == len(categories(unlocked))
    coffee = find(browser, "Coffee")
    assert create(browser, name="X", kind="expense", icon="palette", colour="#0F766E").status_code == 403
    assert browser.patch(f"/api/categories/{coffee['id']}", json={"name": "Tea"}).status_code == 403
    assert browser.post(f"/api/categories/{coffee['id']}/merge", json={"into_id": coffee["id"]}).status_code == 403
