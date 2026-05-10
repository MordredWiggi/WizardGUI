"""
main_window.py - Main window with sidebar and a QStackedWidget.

Sidebar sections:
    Dashboard
    Groups
    Games
    Players
    Feedback
    SQL Console
    Backup
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from db_backend import DbBackend, DbError
from style import (
    ACCENT,
    ACCENT_DIM,
    ADMIN_RED,
    BG_BASE,
    BG_PANEL,
    TEXT_DIM,
    TEXT_MAIN,
    apply_titlebar_theme,
)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, backend: DbBackend) -> None:
        super().__init__()
        self.backend = backend
        self.setWindowTitle(f"Wizard DB Admin - {backend.label}")
        self.setMinimumSize(1180, 720)

        # Lazy imports to avoid circular dependencies.
        from dashboard_view import DashboardView
        from groups_view import GroupsView
        from games_view import GamesView
        from players_view import PlayersView
        from feedback_view import FeedbackView
        from sql_console import SqlConsole
        from backup_view import BackupView

        # Layout: sidebar + stacked main panel
        central = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        sidebar = self._build_sidebar()
        h.addWidget(sidebar)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_layout.addWidget(self._build_top_banner())

        self._stack = QtWidgets.QStackedWidget()
        self._stack.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._stack, 1)

        right_layout.addWidget(self._build_status_bar())

        h.addWidget(right, 1)
        self.setCentralWidget(central)

        # Instantiate views
        self._dashboard = DashboardView(self.backend)
        self._groups = GroupsView(self.backend)
        self._games = GamesView(self.backend)
        self._players = PlayersView(self.backend)
        self._feedback = FeedbackView(self.backend)
        self._sql = SqlConsole(self.backend)
        self._backup = BackupView(self.backend)

        for view in (
            self._dashboard,
            self._groups,
            self._games,
            self._players,
            self._feedback,
            self._sql,
            self._backup,
        ):
            self._stack.addWidget(view)

        # Cross-view navigation: click on a group -> open its games
        self._groups.open_group_games.connect(self._show_games_for_group)
        self._games.back_to_groups.connect(lambda: self._switch(1))
        self._games.player_changed.connect(lambda: self._players.refresh())
        self._players.player_changed.connect(lambda: self._games.refresh())

        # Default view
        self._switch(0)

    # -- UI bricks ----------------------------------------------------------

    def _build_sidebar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setObjectName("sidebar")
        w.setFixedWidth(220)

        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(2)

        title = QtWidgets.QLabel("WIZARD\nADMIN")
        title.setStyleSheet(
            f"color: {ACCENT}; font-size: 18px; font-weight: 800; "
            f"letter-spacing: 2px; padding: 8px 18px 16px 18px; background: transparent;"
        )
        layout.addWidget(title)

        self._nav_buttons: list[QtWidgets.QPushButton] = []

        sections = [
            ("📊  Dashboard", 0),
            ("👥  Groups", 1),
            ("🎮  Games", 2),
            ("🧑  Players", 3),
            ("💬  Feedback", 4),
            ("🛠  SQL Console", 5),
            ("💾  Backup", 6),
        ]
        for label, idx in sections:
            btn = QtWidgets.QPushButton(label)
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        layout.addStretch()

        # Connection footer
        footer = QtWidgets.QLabel(self.backend.description())
        footer.setWordWrap(True)
        footer.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; padding: 12px 16px; background: transparent;"
        )
        layout.addWidget(footer)

        return w

    def _build_top_banner(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QFrame()
        bar.setObjectName("admin_banner")
        bar.setFixedHeight(32)
        bar.setStyleSheet(
            f"background-color: #2a0f12; border: none; border-bottom: 1px solid {ADMIN_RED};"
        )
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        lbl = QtWidgets.QLabel(
            "⚠  DEV ADMIN TOOL  -  Changes apply DIRECTLY to the database"
        )
        lbl.setStyleSheet(
            f"color: {ADMIN_RED}; font-size: 11px; font-weight: 700; "
            f"letter-spacing: 2px; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addStretch()

        conn_lbl = QtWidgets.QLabel(self.backend.label)
        conn_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: 700; "
            f"letter-spacing: 1px; background: transparent;"
        )
        layout.addWidget(conn_lbl)
        return bar

    def _build_status_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QFrame()
        bar.setStyleSheet(
            f"background-color: {BG_PANEL}; border-top: 1px solid #2a2a4a;"
        )
        bar.setFixedHeight(26)
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(14, 0, 14, 0)
        self._status_lbl = QtWidgets.QLabel("Ready.")
        self._status_lbl.setObjectName("status_bar")
        layout.addWidget(self._status_lbl)
        layout.addStretch()
        return bar

    # -- public helpers -----------------------------------------------------

    def set_status(self, text: str) -> None:
        self._status_lbl.setText(text)

    # -- navigation ---------------------------------------------------------

    def _switch(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)
        # Auto-refresh on entry
        try:
            current = self._stack.currentWidget()
            if hasattr(current, "refresh"):
                current.refresh()
        except DbError as exc:
            QtWidgets.QMessageBox.warning(self, "Database error", str(exc))

    def _show_games_for_group(self, group: dict) -> None:
        self._games.set_group(group)
        self._switch(2)

    # -- window behaviour ---------------------------------------------------

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        apply_titlebar_theme(self)
