"""
set_shared_password.py - MAINTAINER ONLY.

Updates the shared developer password used by all collaborators of the
Wizard Admin Tool.

Workflow:
    1. Run this script (asks twice for the new password).
    2. It writes admin_password.json with a fresh PBKDF2 hash + salt.
    3. Commit and push admin_password.json.
    4. Share the plaintext password with your developers OUT-OF-BAND
       (Signal, in person, password manager - never in chat or email).

Other developers then:
    git pull           # they receive admin_password.json
    python main.py     # log in with the shared password
"""

from __future__ import annotations

import getpass
import sys

import auth


def _prompt_password() -> str:
    while True:
        pw1 = getpass.getpass("New shared password (min. 10 chars): ")
        if len(pw1) < 10:
            print("  Please use at least 10 characters.\n")
            continue
        pw2 = getpass.getpass("Confirm password: ")
        if pw1 != pw2:
            print("  Passwords do not match.\n")
            continue
        return pw1


def main() -> int:
    print("=== Wizard Admin Tool - shared password update ===")
    print(f"Target file: {auth.PASSWORD_PATH}\n")
    print("WARNING: This will overwrite the password used by every developer.")
    print("After this script finishes you must commit & push admin_password.json")
    print("and tell your developers the new password through a secure channel.\n")

    confirm = input("Continue? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes", "j", "ja"):
        print("Aborted.")
        return 0

    pw = _prompt_password()
    record = auth.hash_password(pw)
    auth.save_password(record)

    print()
    print(f"-> Hash written to {auth.PASSWORD_PATH}")
    print()
    print("Next steps:")
    print("  git add admin_password.json")
    print("  git commit -m 'Update shared admin password'")
    print("  git push")
    print()
    print("Then share the new password with your developers via a secure channel.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
