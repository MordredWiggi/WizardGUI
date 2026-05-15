"""
auth.py - Password validation + connection-config IO for the Admin Tool.

Two files are involved:

  - admin_password.json  (COMMITTED to git, shared among all developers)
        Holds the PBKDF2 hash of the shared developer password.
        Maintainer-only: update via 'python set_shared_password.py'.

  - admin_config.json    (gitignored, per-developer)
        Holds per-developer connection details (SSH key path,
        local DB path, default-connection choice). Created via
        'python setup_admin.py'.

Hashing uses PBKDF2-HMAC-SHA256 with a per-password random salt
(stdlib, no extra dependencies).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(__file__).resolve().parent
PASSWORD_PATH = CONFIG_DIR / "admin_password.json"  # committed
CONFIG_PATH = CONFIG_DIR / "admin_config.json"      # gitignored

DEFAULT_ITERATIONS = 600_000
SALT_BYTES = 16
HASH_BYTES = 32


# -- Hash helpers -------------------------------------------------------------


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=HASH_BYTES,
    )


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> dict:
    """Build a fresh hash record for ``password``.

    Returned dict contains: password_hash, password_salt, password_iterations.
    Both hash and salt are base64-encoded so the JSON file stays human-readable.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, iterations)
    return {
        "password_hash": base64.b64encode(digest).decode("ascii"),
        "password_salt": base64.b64encode(salt).decode("ascii"),
        "password_iterations": iterations,
    }


# -- Shared password (admin_password.json) ------------------------------------


def load_password() -> Optional[dict]:
    """Read the shared password record. Returns None if file missing/invalid."""
    if not PASSWORD_PATH.is_file():
        return None
    try:
        with PASSWORD_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def save_password(record: dict) -> None:
    """Atomically write the shared password record."""
    PASSWORD_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_comment": (
            "Shared developer password for the Wizard Admin Tool. "
            "Update via 'python set_shared_password.py' (maintainer only). "
            "This file IS committed -- the hash is the same for everyone, "
            "the plaintext password is shared out-of-band."
        ),
        "password_hash": record.get("password_hash"),
        "password_salt": record.get("password_salt"),
        "password_iterations": record.get(
            "password_iterations", DEFAULT_ITERATIONS
        ),
    }
    tmp = PASSWORD_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, PASSWORD_PATH)


def password_configured() -> bool:
    """True if admin_password.json holds a usable hash."""
    pw = load_password()
    if not pw:
        return False
    return bool(pw.get("password_hash")) and bool(pw.get("password_salt"))


def verify_password(password: str) -> bool:
    """Constant-time check of ``password`` against the shared hash."""
    pw = load_password()
    if not pw:
        return False
    try:
        salt = base64.b64decode(pw["password_salt"])
        expected = base64.b64decode(pw["password_hash"])
        iterations = int(pw.get("password_iterations", DEFAULT_ITERATIONS))
    except Exception:
        return False
    digest = _derive(password, salt, iterations)
    return hmac.compare_digest(digest, expected)


# -- Per-developer connection config (admin_config.json) ----------------------


def config_exists() -> bool:
    return CONFIG_PATH.is_file()


def load_config() -> Optional[dict]:
    if not CONFIG_PATH.is_file():
        return None
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def save_config(cfg: dict) -> None:
    """Atomically write the per-developer connection config."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)
