"""
main.py - Entry point for the Wizard Database Admin Tool.

Flow:
    1. Initialise QApplication and apply theme
    2. Show login dialog (password + connection picker)
    3. Build the chosen DB backend
    4. Open MainWindow

Usage:
    python main.py                       - normal launch
    python main.py --connection <name>   - preselect a connection (login still required)
"""

from __future__ import annotations

import argparse
import sys
import traceback

from PyQt6 import QtCore, QtWidgets

import auth
from db_backend import DbError, make_backend
from login_dialog import LoginDialog
from style import STYLESHEET, apply_dark_palette


def _show_message(title: str, text: str) -> int:
    box = QtWidgets.QMessageBox()
    box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(text)
    box.exec()
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Wizard DB Admin Tool")
    parser.add_argument(
        "--connection",
        default=None,
        help="Preselect a connection by key.",
    )
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_dark_palette(app)
    app.setStyleSheet(STYLESHEET)
    app.setApplicationName("Wizard DB Admin")

    if not auth.password_configured():
        return _show_message(
            "Shared password missing",
            "admin_password.json does not contain a password hash.\n\n"
            "If you cloned this repo: run 'git pull' to receive the latest "
            "shared password, or ask the maintainer.\n\n"
            "If you ARE the maintainer: run 'python set_shared_password.py' "
            "to set the shared password, then commit & push.",
        )

    if not auth.config_exists():
        return _show_message(
            "Connection setup required",
            "No connections configured for this machine.\n\n"
            "Please run this once inside the admin_tool folder:\n"
            "    python setup_admin.py",
        )

    login = LoginDialog()
    if args.connection:
        idx = login._conn_combo.findData(args.connection)
        if idx >= 0:
            login._conn_combo.setCurrentIndex(idx)

    if login.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return 0

    conn_name = login.connection_name
    conn_cfg = login.connection_cfg

    # Building the backend may take a moment (SSH ping etc.).
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
    try:
        backend = make_backend(conn_name, conn_cfg)
    except DbError as exc:
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.critical(
            None,
            "Connection failed",
            f"Could not open connection '{conn_name}':\n\n{exc}",
        )
        return 2
    except Exception as exc:
        QtWidgets.QApplication.restoreOverrideCursor()
        QtWidgets.QMessageBox.critical(
            None,
            "Unexpected error",
            f"{exc}\n\n{traceback.format_exc()}",
        )
        return 3
    QtWidgets.QApplication.restoreOverrideCursor()

    # Import MainWindow only here so its lazy imports don't slow login.
    from main_window import MainWindow

    win = MainWindow(backend)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
