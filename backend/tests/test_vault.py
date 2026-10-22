import json

import pytest

from app.vault import RECOVERY_ALPHABET, Vault, VaultError, new_recovery_key, normalize_recovery_key


@pytest.fixture
def vault(tmp_path):
    return Vault(tmp_path / "vault.json")


def test_create_then_unlock(vault):
    created = vault.create("first-passcode")
    assert len(created.key) == 32
    assert vault.unlock("first-passcode") == created
    assert vault.unlock("wrong-passcode") is None


def test_create_twice_is_refused(vault):
    vault.create("first-passcode")
    with pytest.raises(VaultError):
        vault.create("other-passcode")


@pytest.mark.parametrize("passcode", ["", "12345", "x" * 129])
def test_passcode_length_is_checked(vault, passcode):
    with pytest.raises(VaultError):
        vault.create(passcode)
    assert not vault.exists()


def test_file_holds_neither_key_nor_passcode(vault):
    created = vault.create("first-passcode")
    text = vault.path.read_text(encoding="utf-8")
    assert "first-passcode" not in text
    assert created.key.hex() not in text


def test_second_passcode_opens_the_same_key(vault):
    created = vault.create("parent-one-code")
    vault.add_slot(created.key, "parent-two-code")
    assert vault.unlock("parent-one-code").key == created.key
    assert vault.unlock("parent-two-code").key == created.key


def test_change_passcode(vault):
    created = vault.create("old-passcode")
    vault.change_passcode(created.slot_id, created.key, "new-passcode")
    assert vault.unlock("old-passcode") is None
    assert vault.unlock("new-passcode").key == created.key


def test_swapped_slot_ids_do_not_unlock(vault):
    created = vault.create("first-passcode")
    vault.add_slot(created.key, "second-passcode")
    data = json.loads(vault.path.read_text(encoding="utf-8"))
    a, b = data["slots"]
    a["id"], b["id"] = b["id"], a["id"]
    vault.path.write_text(json.dumps(data), encoding="utf-8")
    assert vault.unlock("first-passcode") is None


def test_damaged_file_gives_a_clear_error(vault):
    vault.path.write_text("not json", encoding="utf-8")
    with pytest.raises(VaultError):
        vault.unlock("first-passcode")


# ---- recovery key -------------------------------------------------------------
def test_recovery_key_format():
    key = new_recovery_key()
    groups = key.split("-")
    assert [len(g) for g in groups] == [5, 5, 5, 5, 5]
    assert all(ch in RECOVERY_ALPHABET for ch in "".join(groups))
    assert new_recovery_key() != key


def test_recovery_key_typing_is_forgiving():
    assert normalize_recovery_key("ab0cd 1ef23-456gh 789jk mnpqr") == "AB0CD1EF23456GH789JKMNPQR"
    assert normalize_recovery_key("abocd iefe3 456gh 789jk mnpql") == "AB0CD1EFE3456GH789JKMNPQ1"
    assert normalize_recovery_key("too-short") is None
    assert normalize_recovery_key("U" * 25) is None  # U is not in the alphabet


def test_recovery_key_unlocks_but_not_as_a_passcode(vault):
    created = vault.create("first-passcode")
    recovery = vault.set_recovery_key(created.key)
    assert vault.unlock_recovery(recovery.lower().replace("-", " ")).key == created.key
    assert vault.unlock(recovery) is None
    assert vault.unlock_recovery("first-passcode") is None
    assert vault.recovery_created() is not None
    assert recovery.replace("-", "") not in vault.path.read_text(encoding="utf-8")


def test_new_recovery_key_replaces_the_old_one(vault):
    created = vault.create("first-passcode")
    old = vault.set_recovery_key(created.key)
    new = vault.set_recovery_key(created.key)
    assert vault.unlock_recovery(old) is None
    assert vault.unlock_recovery(new).key == created.key
    assert vault.passcode_slot_ids() == [created.slot_id]
