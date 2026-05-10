"""
setup_admin.py - One-time setup for the Wizard Admin Tool.

Asks for:
  - a developer password (twice; can be re-run anytime to change it)
  - one or more database connections (local file and/or remote SSH)

Writes the result to admin_config.json (gitignored).

Usage:
    python setup_admin.py            - full setup (password + connections)
    python setup_admin.py --password - only reset the password
    python setup_admin.py --ssh      - only add an SSH connection
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

import auth


def _prompt_password() -> str:
    while True:
        pw1 = getpass.getpass("New developer password (min. 8 chars): ")
        if len(pw1) < 8:
            print("  Please use at least 8 characters.\n")
            continue
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 != pw2:
            print("  Passwords do not match.\n")
            continue
        return pw1


def _prompt_str(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val or default


def _prompt_bool(label: str, default: bool = False) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    val = input(f"{label}{suffix}: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "j", "ja")


def setup_password() -> None:
    pw = _prompt_password()
    auth.update_password(pw)
    print(f"  -> Password saved to {auth.CONFIG_PATH}")


def setup_local_connection(cfg: dict) -> None:
    print("\n--- Local test database ---")
    if not _prompt_bool("Configure a local DB connection?", default=True):
        return
    label = _prompt_str("Display name", default="Local test DB")
    default_path = str(
        (Path(__file__).resolve().parent.parent / "leaderboard.db").as_posix()
    )
    db_path = _prompt_str("Path to local .db file", default=default_path)
    cfg.setdefault("connections", {})["local"] = {
        "label": label,
        "db_path": db_path,
    }


def setup_remote_connection(cfg: dict) -> None:
    print("\n--- Remote DB (SSH) ---")
    if not _prompt_bool("Configure a remote DB via SSH?", default=True):
        return
    label = _prompt_str("Display name", default="Production (Oracle Cloud)")
    ssh_host = _prompt_str("SSH host", default="158.180.32.188")
    ssh_user = _prompt_str("SSH user", default="ubuntu")
    ssh_key = _prompt_str(
        "Path to SSH key (Windows: e.g. C:\\Users\\...\\oracle_key.key)",
        default=str(Path.home() / ".ssh" / "oracle_key.key"),
    )
    remote_db = _prompt_str("Remote DB path", default="/data/leaderboard.db")
    cfg.setdefault("connections", {})["remote_oracle"] = {
        "label": label,
        "ssh_host": ssh_host,
        "ssh_user": ssh_user,
        "ssh_key": ssh_key,
        "remote_db_path": remote_db,
    }


def setup_default(cfg: dict) -> None:
    conns = cfg.get("connections") or {}
    if not conns:
        return
    if len(conns) == 1:
        cfg["default_connection"] = next(iter(conns.keys()))
        return
    print("\n--- Default connection ---")
    for key, conn in conns.items():
        print(f"  {key}: {conn.get('label', key)}")
    sel = _prompt_str(
        "Which connection should be selected by default at startup?",
        default=cfg.get("default_connection") or next(iter(conns.keys())),
    )
    cfg["default_connection"] = sel


def main() -> int:
    parser = argparse.ArgumentParser(description="Wizard Admin Tool setup")
    parser.add_argument(
        "--password", action="store_true", help="Only reset the password."
    )
    parser.add_argument(
        "--ssh", action="store_true", help="Only add a new SSH connection."
    )
    args = parser.parse_args()

    print("=== Wizard Admin Tool setup ===")
    print(f"Config file: {auth.CONFIG_PATH}\n")

    only_password = args.password and not args.ssh
    only_ssh = args.ssh and not args.password

    if only_password:
        setup_password()
        return 0

    if only_ssh:
        cfg = auth.load_config() or {}
        setup_remote_connection(cfg)
        setup_default(cfg)
        auth.save_config(cfg)
        print(f"  -> SSH connection saved to {auth.CONFIG_PATH}")
        return 0

    # Full setup
    if auth.password_configured():
        if _prompt_bool("A password is already configured. Change it?", default=False):
            setup_password()
    else:
        setup_password()

    cfg = auth.load_config() or {}
    setup_local_connection(cfg)
    setup_remote_connection(cfg)
    setup_default(cfg)
    auth.save_config(cfg)

    print(
        "\nDone. You can now start the tool with 'python main.py' (or run.bat)."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
