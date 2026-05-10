"""
login_dialog.py - Password prompt + connection picker shown at startup.

After a successful login the dialog exposes:
    self.connection_name: str
    self.connection_cfg:  dict
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

import auth
from style import (
    ACCENT,
    ACCENT_DIM,
    ADMIN_RED,
    BG_BASE,
    DANGER,
    TEXT_DIM,
    TEXT_MAIN,
    apply_titlebar_theme,
)

MAX_ATTEMPTS = 3


class LoginDialog(QtWidgets.QDialog):
    """Modal login dialog. Closes with Accepted on success."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wizard Admin - Login")
        self.setMinimumWidth(440)
        self.setModal(True)

        self._cfg = auth.load_config() or {}
        self._attempts_left = MAX_ATTEMPTS

        self.connection_name: Optional[str] = None
        self.connection_cfg: Optional[dict] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(14)

        # Banner
        banner = QtWidgets.QFrame()
        banner.setObjectName("admin_banner")
        b_layout = QtWidgets.QHBoxLayout(banner)
        b_layout.setContentsMargins(12, 8, 12, 8)
        warn = QtWidgets.QLabel("⚠  DEV ADMIN TOOL  ⚠")
        warn.setObjectName("admin_banner_text")
        warn.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        b_layout.addWidget(warn)
        layout.addWidget(banner)

        title = QtWidgets.QLabel("Wizard Database Admin")
        title.setObjectName("title")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel("Developer Login")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # Connection picker
        conn_lbl = QtWidgets.QLabel("Database connection")
        conn_lbl.setObjectName("section_header")
        layout.addWidget(conn_lbl)

        self._conn_combo = QtWidgets.QComboBox()
        connections = self._cfg.get("connections") or {}
        if not connections:
            self._conn_combo.addItem("(no connections configured)", None)
            self._conn_combo.setEnabled(False)
        else:
            default = self._cfg.get("default_connection")
            for key, conn in connections.items():
                label = conn.get("label") or key
                kind = "SSH" if "ssh_host" in conn else "local"
                self._conn_combo.addItem(f"{label}  ({kind})", key)
            if default:
                idx = self._conn_combo.findData(default)
                if idx >= 0:
                    self._conn_combo.setCurrentIndex(idx)
        layout.addWidget(self._conn_combo)

        # Password
        pw_lbl = QtWidgets.QLabel("Password")
        pw_lbl.setObjectName("section_header")
        layout.addWidget(pw_lbl)

        self._pw_edit = QtWidgets.QLineEdit()
        self._pw_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self._pw_edit.setPlaceholderText("Developer password")
        self._pw_edit.setMinimumHeight(36)
        self._pw_edit.returnPressed.connect(self._on_login)
        layout.addWidget(self._pw_edit)

        self._status = QtWidgets.QLabel(" ")
        self._status.setStyleSheet(f"color: {DANGER}; font-size: 12px;")
        self._status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_cancel = QtWidgets.QPushButton("Cancel")
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_login = QtWidgets.QPushButton("Login")
        self._btn_login.setObjectName("primary")
        self._btn_login.clicked.connect(self._on_login)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_login)
        layout.addLayout(btn_row)

        # Hint footer
        hint = QtWidgets.QLabel(
            "If you have not set a password yet, close this dialog and run "
            "'python setup_admin.py' inside the admin_tool folder."
        )
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        hint.setWordWrap(True)
        hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self._pw_edit.setFocus()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        apply_titlebar_theme(self)

    # -- login flow ---------------------------------------------------------

    def _on_login(self) -> None:
        if not auth.password_configured(self._cfg):
            self._status.setText(
                "No password configured. Please run setup_admin.py first."
            )
            return
        pw = self._pw_edit.text()
        if not pw:
            self._status.setText("Please enter a password.")
            return
        if not auth.verify_password(pw, self._cfg):
            self._attempts_left -= 1
            if self._attempts_left <= 0:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Login failed",
                    "Too many failed attempts. The tool will now exit.",
                )
                self.reject()
                return
            self._status.setText(
                f"Wrong password. {self._attempts_left} attempt(s) left."
            )
            self._pw_edit.selectAll()
            return

        # Validate connection
        conn_key = self._conn_combo.currentData()
        if not conn_key:
            self._status.setText("No connection selected.")
            return
        conn_cfg = (self._cfg.get("connections") or {}).get(conn_key)
        if not conn_cfg:
            self._status.setText("Connection not found.")
            return

        self.connection_name = conn_key
        self.connection_cfg = conn_cfg
        self.accept()
