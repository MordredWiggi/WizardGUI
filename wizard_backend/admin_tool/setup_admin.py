"""
setup_admin.py - Per-developer setup for the Wizard Admin Tool.

This script ONLY configures the database connections (local file +
remote SSH details) for *your* machine. The result is written to
``admin_config.json``, which is gitignored.

The shared developer password is NOT set here. It is committed to the
repo (admin_password.json) by the maintainer; if the password does not
work for you, ask the maintainer for the current value.

Usage:
    python setup_admin.py                  - interactive: configure connections
    python setup_admin.py --ssh            - only add an SSH connection
    python setup_admin.py --install-sqlite3 [conn]
                                            - install sqlite3 on the remote VM
                                              of <conn> (default: any SSH conn)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import auth


# -- Subprocess helpers (suppress console flashes on Windows) ----------------

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        **kw,
    )


# -- Prompt helpers ----------------------------------------------------------


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


# -- Setup steps --------------------------------------------------------------


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


# -- Remote sqlite3 installer -------------------------------------------------


def install_sqlite3_on_remote(conn_key: str | None) -> int:
    """Install sqlite3 on a remote VM via apt-get."""
    cfg = auth.load_config() or {}
    conns = cfg.get("connections") or {}
    if not conns:
        print("No connections configured. Run 'python setup_admin.py' first.")
        return 1

    # Pick a connection
    target = None
    if conn_key:
        target = (conn_key, conns.get(conn_key))
        if target[1] is None:
            print(f"Connection '{conn_key}' not found.")
            return 1
    else:
        ssh_conns = [(k, v) for k, v in conns.items() if "ssh_host" in v]
        if not ssh_conns:
            print("No SSH connections configured.")
            return 1
        if len(ssh_conns) == 1:
            target = ssh_conns[0]
        else:
            print("Multiple SSH connections configured:")
            for k, v in ssh_conns:
                print(f"  {k}: {v.get('label', k)}")
            sel = input("Which one? ").strip()
            for k, v in ssh_conns:
                if k == sel:
                    target = (k, v)
                    break
            if target is None:
                print(f"Unknown selection '{sel}'.")
                return 1

    name, conn = target
    if "ssh_host" not in conn:
        print(f"Connection '{name}' is not an SSH connection.")
        return 1

    if shutil.which("ssh") is None:
        print("OpenSSH client (ssh) not found on this machine.")
        return 1

    ssh_cmd = [
        "ssh",
        "-i", conn["ssh_key"],
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        f"{conn['ssh_user']}@{conn['ssh_host']}",
        "sudo apt-get update -y && sudo apt-get install -y sqlite3",
    ]
    print(f"Connecting to {conn['ssh_user']}@{conn['ssh_host']} ...")
    print("This will run: sudo apt-get install -y sqlite3")
    print("(may take 30-60 seconds; sudo password may be required if not passwordless)\n")
    res = _run(ssh_cmd, timeout=180)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)
    if res.returncode != 0:
        print(f"\nFailed (exit code {res.returncode}).")
        print("If the error mentions 'sudo: a password is required', run the")
        print("install manually after connecting via SSH:")
        print(f"   ssh -i {conn['ssh_key']} {conn['ssh_user']}@{conn['ssh_host']}")
        print("   sudo apt-get install -y sqlite3")
        return res.returncode

    # Verify it worked
    verify = _run(
        [
            "ssh",
            "-i", conn["ssh_key"],
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            f"{conn['ssh_user']}@{conn['ssh_host']}",
            "sqlite3 -version",
        ],
        timeout=20,
    )
    if verify.returncode == 0 and verify.stdout.strip():
        print(f"OK: sqlite3 installed -> {verify.stdout.strip()}")
        return 0
    print("Install completed but sqlite3 -version still fails. Check manually.")
    return 1


# -- Entry point --------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wizard Admin Tool - per-developer setup",
    )
    parser.add_argument(
        "--ssh", action="store_true", help="Only (re-)add the SSH connection."
    )
    parser.add_argument(
        "--install-sqlite3",
        nargs="?",
        const="",
        metavar="CONN",
        help="Install sqlite3 on the remote VM of CONN (default: only SSH conn).",
    )
    args = parser.parse_args()

    if args.install_sqlite3 is not None:
        return install_sqlite3_on_remote(args.install_sqlite3 or None)

    print("=== Wizard Admin Tool - per-developer setup ===")
    print(f"Config file: {auth.CONFIG_PATH}")
    if not auth.password_configured():
        print()
        print("NOTE: No shared password found at admin_password.json.")
        print("      Either run 'git pull' to receive it, or - if you are the")
        print("      maintainer - run 'python set_shared_password.py' first.")
    print()

    if args.ssh:
        cfg = auth.load_config() or {}
        setup_remote_connection(cfg)
        setup_default(cfg)
        auth.save_config(cfg)
        print(f"  -> SSH connection saved to {auth.CONFIG_PATH}")
        return 0

    cfg = auth.load_config() or {}
    setup_local_connection(cfg)
    setup_remote_connection(cfg)
    setup_default(cfg)
    auth.save_config(cfg)

    print("\nDone. You can now start the tool with 'python main.py' (or run.bat).")
    if any("ssh_host" in c for c in (cfg.get("connections") or {}).values()):
        print()
        print("Tip: if logging in to the remote DB fails with 'sqlite3: command")
        print("not found', run:  python setup_admin.py --install-sqlite3")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
