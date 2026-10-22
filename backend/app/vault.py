"""The key file (vault.json) that guards the database key.

The database is encrypted with one random 256-bit key. That key is never stored as is:
each passcode gets a "slot" holding a copy of the key, encrypted (AES-256-GCM) with a key
derived from the passcode (scrypt). Several slots means several passcodes, one per adult,
all opening the same database, and changing a passcode only rewrites its slot.

The file holds no names, account details or data, only salts and encrypted keys.
Without a correct passcode it is useless. Lose it, and the database cannot be opened.

One extra slot can hold a printable recovery key instead of a passcode: 25 random characters
from an alphabet without look-alike letters, for when a passcode is forgotten.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT = 1
KEY_BYTES = 32

# scrypt cost: about 32 MiB of memory and a fraction of a second per try, so guessing
# passcodes from a stolen key file is slow. Stored per slot, so it can be raised later.
SCRYPT = {"n": 2**15, "r": 8, "p": 1}

MIN_PASSCODE = 6
MAX_PASSCODE = 128

PASSCODE, RECOVERY = "passcode", "recovery"

# Crockford base32: digits and capitals without I, L, O and U, so the key is easy to copy by hand.
RECOVERY_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
RECOVERY_LENGTH = 25  # 125 random bits, shown as 5 groups of 5


class VaultError(Exception):
    pass


def check_passcode(passcode: str) -> None:
    if len(passcode) < MIN_PASSCODE:
        raise VaultError(f"Passcode must be at least {MIN_PASSCODE} characters.")
    if len(passcode) > MAX_PASSCODE:
        raise VaultError(f"Passcode must be at most {MAX_PASSCODE} characters.")


def new_recovery_key() -> str:
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_LENGTH))
    return "-".join(raw[i : i + 5] for i in range(0, RECOVERY_LENGTH, 5))


def normalize_recovery_key(text: str) -> str | None:
    """Accepts any case, spaces and dashes, and O/I/L typed for 0/1. None if it cannot be a key."""
    raw = "".join(ch for ch in text.upper() if ch.isalnum())
    raw = raw.translate(str.maketrans({"O": "0", "I": "1", "L": "1"}))
    if len(raw) != RECOVERY_LENGTH or any(ch not in RECOVERY_ALPHABET for ch in raw):
        return None
    return raw


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _derive(passcode: str, salt: bytes, kdf: dict) -> bytes:
    n, r, p = kdf["n"], kdf["r"], kdf["p"]
    return hashlib.scrypt(
        passcode.encode("utf-8"), salt=salt, n=n, r=r, p=p,
        maxmem=256 * n * r + 2**20, dklen=KEY_BYTES,
    )


def _aad(slot_id: str) -> bytes:
    # Ties each encrypted key to its slot, so slots cannot be swapped around.
    return f"kinsum-vault/{FORMAT}/{slot_id}".encode("ascii")


@dataclass(frozen=True)
class Unlocked:
    key: bytes
    slot_id: str


class Vault:
    def __init__(self, path: Path):
        self.path = path

    def exists(self) -> bool:
        return self.path.is_file()

    # ---- reading and writing the file --------------------------------------
    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise VaultError(f"Key file could not be read: {e}") from e
        if data.get("format") != FORMAT or not isinstance(data.get("slots"), list):
            raise VaultError("Key file has an unknown format.")
        return data

    def _save(self, data: dict) -> None:
        # Write a temp file then swap it in, so a crash never leaves a half-written key file.
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def _make_slot(slot_id: str, key: bytes, secret: str, kind: str = PASSCODE) -> dict:
        if kind == PASSCODE:
            check_passcode(secret)
        salt, nonce = os.urandom(16), os.urandom(12)
        wrapped = AESGCM(_derive(secret, salt, SCRYPT)).encrypt(nonce, key, _aad(slot_id))
        return {
            "id": slot_id,
            "kind": kind,
            "created": date.today().isoformat(),
            "kdf": {"name": "scrypt", **SCRYPT},
            "salt": _b64(salt),
            "nonce": _b64(nonce),
            "wrapped_key": _b64(wrapped),
        }

    # ---- public API --------------------------------------------------------
    def create(self, passcode: str) -> Unlocked:
        """First run: make a new database key guarded by this passcode."""
        if self.exists():
            raise VaultError("Kinsum is already set up.")
        key, slot_id = secrets.token_bytes(KEY_BYTES), secrets.token_hex(4)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._save({"format": FORMAT, "slots": [self._make_slot(slot_id, key, passcode)]})
        return Unlocked(key, slot_id)

    def unlock(self, passcode: str) -> Unlocked | None:
        """Try the passcode against every passcode slot. Returns None if none of them match."""
        return self._try(passcode, PASSCODE)

    def unlock_recovery(self, recovery_key: str) -> Unlocked | None:
        raw = normalize_recovery_key(recovery_key)
        return None if raw is None else self._try(raw, RECOVERY)

    def _try(self, secret: str, kind: str) -> Unlocked | None:
        for slot in self._load()["slots"]:
            kdf = slot["kdf"]
            if slot.get("kind", PASSCODE) != kind or kdf.get("name") != "scrypt":
                continue
            try:
                kek = _derive(secret, _unb64(slot["salt"]), kdf)
                key = AESGCM(kek).decrypt(
                    _unb64(slot["nonce"]), _unb64(slot["wrapped_key"]), _aad(slot["id"])
                )
            except InvalidTag:
                continue
            return Unlocked(key, slot["id"])
        return None

    def add_slot(self, key: bytes, passcode: str) -> str:
        """Add another passcode that opens the same database (one per adult, step 3)."""
        data = self._load()
        slot_id = secrets.token_hex(4)
        data["slots"].append(self._make_slot(slot_id, key, passcode))
        self._save(data)
        return slot_id

    def change_passcode(self, slot_id: str, key: bytes, new_passcode: str) -> None:
        data = self._load()
        for i, slot in enumerate(data["slots"]):
            if slot["id"] == slot_id and slot.get("kind", PASSCODE) == PASSCODE:
                data["slots"][i] = self._make_slot(slot_id, key, new_passcode)
                self._save(data)
                return
        raise VaultError("Passcode slot not found.")

    def passcode_slot_ids(self) -> list[str]:
        return [s["id"] for s in self._load()["slots"] if s.get("kind", PASSCODE) == PASSCODE]

    def recovery_created(self) -> str | None:
        """Date the current recovery key was made, or None if there is none."""
        for slot in self._load()["slots"]:
            if slot.get("kind") == RECOVERY:
                return slot.get("created")
        return None

    def set_recovery_key(self, key: bytes) -> str:
        """Make a new recovery key. Any earlier one stops working. Returns it for printing."""
        recovery_key = new_recovery_key()
        data = self._load()
        data["slots"] = [s for s in data["slots"] if s.get("kind") != RECOVERY]
        slot = self._make_slot(secrets.token_hex(4), key, normalize_recovery_key(recovery_key), RECOVERY)
        data["slots"].append(slot)
        self._save(data)
        return recovery_key
