"""
auth.py - Password validation for the Wizard Admin Tool.

Uses PBKDF2-HMAC-SHA256 (stdlib) with a random salt.
Hash + salt are stored in admin_config.json (gitignored).
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
CONFIG_PATH = CONFIG_DIR / "admin_config.json"

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
    """Return {'password_hash', 'password_salt', 'password_iterations'}.

    Both hash and salt are stored as base64 strings so the JSON config stays
    human-readable.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, iterations)
    return {
        "password_hash": base64.b64encode(digest).decode("ascii"),
        "password_salt": base64.b64encode(salt).decode("ascii"),
        "password_iterations": iterations,
    }


def verify_password(password: str, stored: dict) -> bool:
    """Constant-time check of ``password`` against the stored hash."""
    try:
        salt = base64.b64decode(stored["password_salt"])
        expected = base64.b64decode(stored["password_hash"])
        iterations = int(stored.get("password_iterations", DEFAULT_ITERATIONS))
    except Exception:
        return False
    digest = _derive(password, salt, iterations)
    return hmac.compare_digest(digest, expected)


# -- Config persistence -------------------------------------------------------


def config_exists() -> bool:
    return CONFIG_PATH.is_file()


def load_config() -> Optional[dict]:
    if not config_exists():
        return None
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def save_config(cfg: dict) -> None:
    """Atomically write the config (so we never end up with a partial file)."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


def update_password(password: str) -> dict:
    """Hash ``password`` and persist it into admin_config.json (creating it
    if necessary). Returns the updated config."""
    cfg = load_config() or {"connections": {}, "default_connection": None}
    cfg.update(hash_password(password))
    save_config(cfg)
    return cfg


def password_configured(cfg: Optional[dict] = None) -> bool:
    cfg = cfg if cfg is not None else load_config()
    if not cfg:
        return False
    return bool(cfg.get("password_hash")) and bool(cfg.get("password_salt"))
