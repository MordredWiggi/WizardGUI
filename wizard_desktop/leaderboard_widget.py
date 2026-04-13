"""
leaderboard_widget.py – Reusable in-app leaderboard view.

Shows a sortable leaderboard table with mode tabs (Standard / Multiplicative).
Fetches data from the server in a background thread.
"""
from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets, QtGui

from style import (
    ACCENT, ACCENT_DIM, BG_PANEL, BG_CARD, BG_DEEP,
    TEXT_MAIN, TEXT_DIM, SUCCESS, LEADER, PLAYER_COLORS,
)
from app_settings import t, get_leaderboard_url, get_theme
from game_control import GAME_MODE_STANDARD, GAME_MODE_MULTIPLICATIVE


# Sort keys matching the server response fields
_SORT_KEYS = [
    ("wins",          "lb_sort_wins"),
    ("win_rate",      "lb_sort_win_rate"),
    ("avg_score",     "lb_sort_avg_score"),
    ("hit_rate",      "lb_sort_hit_rate"),
    ("highest_score", "lb_sort_highest"),
    ("win_streak",    "lb_sort_streak"),
]

# Column definitions: (data_key, header_translation_key, width)
_COLUMNS = [
    ("_rank",         "lb_col_rank",     40),
    ("name",          "lb_col_name",    140),
    ("wins",          "lb_col_wins",     55),
    ("games",         "lb_col_games",    60),
    ("win_rate",      "lb_col_win_rate", 60),
    ("avg_score",     "lb_col_avg",      60),
    ("hit_rate",      "lb_col_hit_rate", 60),
    ("highest_score", "lb_col_highest",  65),
    ("win_streak",    "lb_col_streak",   55),
]


class LeaderboardWidget(QtWidgets.QWidget):
    """Embeddable leaderboard panel with mode tabs and sort buttons."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._fetch_worker: Optional[object] = None
        self._current_mode = GAME_MODE_STANDARD
        self._current_sort = "wins"
        self._data: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Mode tabs row ────────────────────────────────────────────────
        mode_row = QtWidgets.QHBoxLayout()
        mode_row.setSpacing(4)

        self._btn_standard = QtWidgets.QPushButton(t("game_mode_standard"))
        self._btn_multi = QtWidgets.QPushButton(t("game_mode_multiplicative"))
        self._btn_refresh = QtWidgets.QPushButton("↻")
        self._btn_refresh.setFixedWidth(36)
        self._btn_refresh.setToolTip(t("btn_refresh"))

        for btn in (self._btn_standard, self._btn_multi):
            btn.setMinimumHeight(30)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        self._btn_refresh.setMinimumHeight(30)
        self._btn_refresh.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        self._btn_standard.clicked.connect(lambda: self._set_mode(GAME_MODE_STANDARD))
        self._btn_multi.clicked.connect(lambda: self._set_mode(GAME_MODE_MULTIPLICATIVE))
        self._btn_refresh.clicked.connect(self.refresh)

        mode_row.addWidget(self._btn_standard)
        mode_row.addWidget(self._btn_multi)
        mode_row.addStretch()
        mode_row.addWidget(self._btn_refresh)
        layout.addLayout(mode_row)

        # ── Sort buttons row ─────────────────────────────────────────────
        sort_row = QtWidgets.QHBoxLayout()
        sort_row.setSpacing(3)

        self._sort_buttons: dict[str, QtWidgets.QPushButton] = {}
        for key, label_key in _SORT_KEYS:
            btn = QtWidgets.QPushButton(t(label_key))
            btn.setMinimumHeight(26)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, k=key: self._set_sort(k))
            self._sort_buttons[key] = btn
            sort_row.addWidget(btn)

        sort_row.addStretch()
        layout.addLayout(sort_row)

        # ── Table ────────────────────────────────────────────────────────
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)

        for i, (_, _, width) in enumerate(_COLUMNS):
            self._table.setColumnWidth(i, width)

        layout.addWidget(self._table, 1)

        # ── Status label (loading / error / empty) ───────────────────────
        self._status_label = QtWidgets.QLabel()
        self._status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; font-style: italic; padding: 20px; background: transparent;"
        )
        self._status_label.hide()
        layout.addWidget(self._status_label)

        self._apply_mode_style()
        self._apply_sort_style()
        self._apply_table_style()

    # ── Styling ──────────────────────────────────────────────────────────────

    def _apply_table_style(self) -> None:
        dark = get_theme() != "light"
        if dark:
            self._table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {BG_PANEL};
                    border: 1px solid #2a2a4a;
                    border-radius: 6px;
                    gridline-color: #2a2a4a;
                    color: {TEXT_MAIN};
                    font-size: 12px;
                }}
                QTableWidget::item {{
                    padding: 4px 6px;
                }}
                QTableWidget::item:selected {{
                    background-color: {ACCENT_DIM};
                    color: #fff8e0;
                }}
                QHeaderView::section {{
                    background-color: {BG_CARD};
                    color: {ACCENT};
                    font-weight: 700;
                    font-size: 11px;
                    border: none;
                    border-bottom: 2px solid {ACCENT_DIM};
                    padding: 5px 4px;
                }}
                QTableWidget QTableCornerButton::section {{
                    background-color: {BG_CARD};
                    border: none;
                }}
            """)
        else:
            self._table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: #e4e4ee;
                    border: 1px solid #ccccdd;
                    border-radius: 6px;
                    gridline-color: #ccccdd;
                    color: #1a1a2e;
                    font-size: 12px;
                }}
                QTableWidget::item {{
                    padding: 4px 6px;
                }}
                QTableWidget::item:selected {{
                    background-color: #c9a84c;
                    color: #ffffff;
                }}
                QHeaderView::section {{
                    background-color: #f8f8ff;
                    color: #9b7a1e;
                    font-weight: 700;
                    font-size: 11px;
                    border: none;
                    border-bottom: 2px solid #c9a84c;
                    padding: 5px 4px;
                }}
                QTableWidget QTableCornerButton::section {{
                    background-color: #f8f8ff;
                    border: none;
                }}
            """)

    def _apply_mode_style(self) -> None:
        dark = get_theme() != "light"
        for btn, mode in [(self._btn_standard, GAME_MODE_STANDARD),
                          (self._btn_multi, GAME_MODE_MULTIPLICATIVE)]:
            active = (mode == self._current_mode)
            if dark:
                if active:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: {ACCENT_DIM}; color: #fff8e0; "
                        f"border: 1px solid {ACCENT}; border-radius: 5px; font-weight: 700; "
                        f"font-size: 12px; padding: 4px 12px; }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: {BG_CARD}; color: {TEXT_DIM}; "
                        f"border: 1px solid #3a3a6a; border-radius: 5px; font-size: 12px; padding: 4px 12px; }}"
                        f"QPushButton:hover {{ border-color: {ACCENT_DIM}; color: {TEXT_MAIN}; }}"
                    )
            else:
                if active:
                    btn.setStyleSheet(
                        "QPushButton { background: #9b7a1e; color: #ffffff; "
                        "border: 1px solid #c9a84c; border-radius: 5px; font-weight: 700; "
                        "font-size: 12px; padding: 4px 12px; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton { background: #f8f8ff; color: #555577; "
                        "border: 1px solid #aaaacc; border-radius: 5px; font-size: 12px; padding: 4px 12px; }"
                        "QPushButton:hover { border-color: #9b7a1e; color: #1a1a2e; }"
                    )

    def _apply_sort_style(self) -> None:
        dark = get_theme() != "light"
        for key, btn in self._sort_buttons.items():
            active = (key == self._current_sort)
            if dark:
                if active:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: {ACCENT}; color: {BG_DEEP}; "
                        f"border: none; border-radius: 4px; font-weight: 700; "
                        f"font-size: 11px; padding: 3px 8px; }}"
                    )
                else:
                    btn.setStyleSheet(
                        f"QPushButton {{ background: transparent; color: {TEXT_DIM}; "
                        f"border: 1px solid #3a3a6a; border-radius: 4px; "
                        f"font-size: 11px; padding: 3px 8px; }}"
                        f"QPushButton:hover {{ color: {ACCENT}; border-color: {ACCENT_DIM}; }}"
                    )
            else:
                if active:
                    btn.setStyleSheet(
                        "QPushButton { background: #9b7a1e; color: #ffffff; "
                        "border: none; border-radius: 4px; font-weight: 700; "
                        "font-size: 11px; padding: 3px 8px; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton { background: transparent; color: #555577; "
                        "border: 1px solid #aaaacc; border-radius: 4px; "
                        "font-size: 11px; padding: 3px 8px; }"
                        "QPushButton:hover { color: #9b7a1e; border-color: #9b7a1e; }"
                    )

    # ── Mode / Sort switching ────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        if mode == self._current_mode:
            return
        self._current_mode = mode
        self._apply_mode_style()
        self.refresh()

    def _set_sort(self, key: str) -> None:
        if key == self._current_sort:
            return
        self._current_sort = key
        self._apply_sort_style()
        self._render_data()

    # ── Data fetching ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Fetch leaderboard data from the server."""
        url = get_leaderboard_url()
        if not url:
            self._show_status(t("lb_error"))
            return

        self._show_status(t("lb_loading"))

        from leaderboard_client import LeaderboardClient, LeaderboardFetchWorker
        client = LeaderboardClient(url)
        self._fetch_worker = LeaderboardFetchWorker(client, self._current_mode)
        self._fetch_worker.result.connect(self._on_data_received)
        self._fetch_worker.start()

    def _on_data_received(self, data: object) -> None:
        if data is None:
            self._show_status(t("lb_error"))
            return
        self._data = data
        if not data:
            self._show_status(t("lb_no_data"))
            return
        self._status_label.hide()
        self._table.show()
        self._render_data()

    def _show_status(self, text: str) -> None:
        self._table.setRowCount(0)
        self._table.hide()
        self._status_label.setText(text)
        self._status_label.show()

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render_data(self) -> None:
        # Sort data
        sorted_data = sorted(
            self._data,
            key=lambda row: row.get(self._current_sort, 0),
            reverse=True,
        )

        self._table.setRowCount(len(sorted_data))

        for row_idx, entry in enumerate(sorted_data):
            for col_idx, (data_key, _, _) in enumerate(_COLUMNS):
                if data_key == "_rank":
                    value = str(row_idx + 1)
                elif data_key in ("win_rate", "hit_rate", "avg_score"):
                    value = f"{entry.get(data_key, 0):.1f}"
                    if data_key in ("win_rate", "hit_rate"):
                        value += "%"
                else:
                    value = str(entry.get(data_key, ""))

                item = QtWidgets.QTableWidgetItem(value)
                # Right-align numeric columns
                if data_key != "name":
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                else:
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )

                # Highlight rank 1
                if row_idx == 0 and data_key == "_rank":
                    item.setForeground(QtGui.QColor(LEADER))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                elif row_idx == 0 and data_key == "name":
                    item.setForeground(QtGui.QColor(LEADER))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

                # Highlight the sorted column
                if data_key == self._current_sort:
                    dark = get_theme() != "light"
                    item.setForeground(QtGui.QColor(ACCENT if dark else "#9b7a1e"))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

                self._table.setItem(row_idx, col_idx, item)

        self._table.resizeRowsToContents()

    # ── Public API ───────────────────────────────────────────────────────────

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        # Auto-refresh when widget becomes visible
        self.refresh()

    def retranslate_ui(self) -> None:
        """Update all translatable texts."""
        self._btn_standard.setText(t("game_mode_standard"))
        self._btn_multi.setText(t("game_mode_multiplicative"))
        self._btn_refresh.setToolTip(t("btn_refresh"))
        for key, label_key in _SORT_KEYS:
            self._sort_buttons[key].setText(t(label_key))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _COLUMNS])
        self._apply_mode_style()
        self._apply_sort_style()
        self._apply_table_style()

    def restyle(self) -> None:
        """Re-apply styles after theme change."""
        self._apply_mode_style()
        self._apply_sort_style()
        self._apply_table_style()


# ─────────────────────────────────────────────────────────────────────────────
# GroupsLeaderboardWidget  – global groups leaderboard
# ─────────────────────────────────────────────────────────────────────────────

_GROUPS_SORT_KEYS = [
    ("total_games", "glb_sort_games"),
    ("avg_score",   "glb_sort_avg"),
    ("avg_hit_rate","glb_sort_hit"),
]

_GROUPS_COLUMNS = [
    ("_rank",       "glb_col_rank",     40),
    ("name",        "glb_col_name",    160),
    ("total_games", "glb_col_games",    65),
    ("avg_score",   "glb_col_avg_score",70),
    ("avg_hit_rate","glb_col_hit_rate", 60),
]


class GroupsLeaderboardWidget(QtWidgets.QWidget):
    """Shows the global groups leaderboard (public groups ranked by metrics)."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._fetch_worker: Optional[object] = None
        self._current_sort = "total_games"
        self._data: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Sort + refresh row ───────────────────────────────────────────
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(3)

        self._sort_buttons: dict[str, QtWidgets.QPushButton] = {}
        for key, label_key in _GROUPS_SORT_KEYS:
            btn = QtWidgets.QPushButton(t(label_key))
            btn.setMinimumHeight(26)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, k=key: self._set_sort(k))
            self._sort_buttons[key] = btn
            top_row.addWidget(btn)

        top_row.addStretch()
        self._btn_refresh = QtWidgets.QPushButton("↻")
        self._btn_refresh.setFixedWidth(36)
        self._btn_refresh.setMinimumHeight(26)
        self._btn_refresh.setToolTip(t("btn_refresh"))
        self._btn_refresh.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_refresh.clicked.connect(self.refresh)
        top_row.addWidget(self._btn_refresh)
        layout.addLayout(top_row)

        # ── Table ────────────────────────────────────────────────────────
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(len(_GROUPS_COLUMNS))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _GROUPS_COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        for i, (_, _, width) in enumerate(_GROUPS_COLUMNS):
            self._table.setColumnWidth(i, width)
        layout.addWidget(self._table, 1)

        # ── Status label ─────────────────────────────────────────────────
        self._status_label = QtWidgets.QLabel()
        self._status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; font-style: italic; padding: 20px; background: transparent;"
        )
        self._status_label.hide()
        layout.addWidget(self._status_label)

        self._apply_sort_style()
        self._apply_table_style()

    def _apply_table_style(self) -> None:
        dark = get_theme() != "light"
        if dark:
            self._table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {BG_PANEL};
                    border: 1px solid #2a2a4a;
                    border-radius: 6px;
                    gridline-color: #2a2a4a;
                    color: {TEXT_MAIN};
                    font-size: 12px;
                }}
                QTableWidget::item {{ padding: 4px 6px; }}
                QTableWidget::item:selected {{ background-color: {ACCENT_DIM}; color: #fff8e0; }}
                QHeaderView::section {{
                    background-color: {BG_CARD}; color: {ACCENT};
                    font-weight: 700; font-size: 11px;
                    border: none; border-bottom: 2px solid {ACCENT_DIM}; padding: 5px 4px;
                }}
            """)
        else:
            self._table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: #e4e4ee; border: 1px solid #ccccdd;
                    border-radius: 6px; gridline-color: #ccccdd;
                    color: #1a1a2e; font-size: 12px;
                }}
                QTableWidget::item {{ padding: 4px 6px; }}
                QTableWidget::item:selected {{ background-color: #c9a84c; color: #ffffff; }}
                QHeaderView::section {{
                    background-color: #f8f8ff; color: #9b7a1e;
                    font-weight: 700; font-size: 11px;
                    border: none; border-bottom: 2px solid #c9a84c; padding: 5px 4px;
                }}
            """)

    def _apply_sort_style(self) -> None:
        dark = get_theme() != "light"
        for key, btn in self._sort_buttons.items():
            active = (key == self._current_sort)
            if dark:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {ACCENT}; color: {BG_DEEP}; border: none; border-radius: 4px; font-weight: 700; font-size: 11px; padding: 3px 8px; }}"
                    if active else
                    f"QPushButton {{ background: transparent; color: {TEXT_DIM}; border: 1px solid #3a3a6a; border-radius: 4px; font-size: 11px; padding: 3px 8px; }}"
                    f"QPushButton:hover {{ color: {ACCENT}; border-color: {ACCENT_DIM}; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: #9b7a1e; color: #ffffff; border: none; border-radius: 4px; font-weight: 700; font-size: 11px; padding: 3px 8px; }"
                    if active else
                    "QPushButton { background: transparent; color: #555577; border: 1px solid #aaaacc; border-radius: 4px; font-size: 11px; padding: 3px 8px; }"
                    "QPushButton:hover { color: #9b7a1e; border-color: #9b7a1e; }"
                )

    def _set_sort(self, key: str) -> None:
        if key == self._current_sort:
            return
        self._current_sort = key
        self._apply_sort_style()
        self._render_data()

    def refresh(self) -> None:
        url = get_leaderboard_url()
        if not url:
            self._show_status(t("glb_error"))
            return
        self._show_status(t("glb_loading"))
        from leaderboard_client import LeaderboardClient, GroupsLeaderboardFetchWorker
        client = LeaderboardClient(url)
        self._fetch_worker = GroupsLeaderboardFetchWorker(client)
        self._fetch_worker.result.connect(self._on_data_received)
        self._fetch_worker.start()

    def _on_data_received(self, data: object) -> None:
        if data is None:
            self._show_status(t("glb_error"))
            return
        self._data = data
        if not data:
            self._show_status(t("glb_no_data"))
            return
        self._status_label.hide()
        self._table.show()
        self._render_data()

    def _show_status(self, text: str) -> None:
        self._table.setRowCount(0)
        self._table.hide()
        self._status_label.setText(text)
        self._status_label.show()

    def _render_data(self) -> None:
        sorted_data = sorted(
            self._data,
            key=lambda row: row.get(self._current_sort, 0),
            reverse=True,
        )
        self._table.setRowCount(len(sorted_data))
        for row_idx, entry in enumerate(sorted_data):
            for col_idx, (data_key, _, _) in enumerate(_GROUPS_COLUMNS):
                if data_key == "_rank":
                    value = str(row_idx + 1)
                elif data_key in ("avg_score", "avg_hit_rate"):
                    v = entry.get(data_key, 0)
                    value = f"{v:.1f}" + ("%" if data_key == "avg_hit_rate" else "")
                else:
                    value = str(entry.get(data_key, ""))

                item = QtWidgets.QTableWidgetItem(value)
                if data_key != "name":
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                if row_idx == 0 and data_key in ("_rank", "name"):
                    item.setForeground(QtGui.QColor(LEADER))
                    f = item.font(); f.setBold(True); item.setFont(f)
                if data_key.replace("_rate", "").replace("_score", "") == self._current_sort.replace("_rate", "").replace("_score", "") or data_key == self._current_sort:
                    dark = get_theme() != "light"
                    item.setForeground(QtGui.QColor(ACCENT if dark else "#9b7a1e"))
                    f = item.font(); f.setBold(True); item.setFont(f)
                self._table.setItem(row_idx, col_idx, item)
        self._table.resizeRowsToContents()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    def retranslate_ui(self) -> None:
        for key, label_key in _GROUPS_SORT_KEYS:
            self._sort_buttons[key].setText(t(label_key))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _GROUPS_COLUMNS])
        self._apply_sort_style()
        self._apply_table_style()

    def restyle(self) -> None:
        self._apply_sort_style()
        self._apply_table_style()


# ─────────────────────────────────────────────────────────────────────────────
# GroupPlayerLeaderboardWidget  – per-group player leaderboard
# ─────────────────────────────────────────────────────────────────────────────

class GroupPlayerLeaderboardWidget(QtWidgets.QWidget):
    """Shows a player leaderboard filtered to a specific group (by 4-digit code)."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._fetch_worker: Optional[object] = None
        self._current_mode = GAME_MODE_STANDARD
        self._current_sort = "wins"
        self._data: list[dict] = []
        self._group_code: Optional[str] = None
        self._build_ui()

    def set_group(self, code: Optional[str]) -> None:
        """Update which group's leaderboard to show. Pass None to clear."""
        self._group_code = code
        if self.isVisible():
            self.refresh()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Mode tabs row ────────────────────────────────────────────────
        mode_row = QtWidgets.QHBoxLayout()
        mode_row.setSpacing(4)

        self._btn_standard = QtWidgets.QPushButton(t("game_mode_standard"))
        self._btn_multi = QtWidgets.QPushButton(t("game_mode_multiplicative"))
        self._btn_refresh = QtWidgets.QPushButton("↻")
        self._btn_refresh.setFixedWidth(36)
        self._btn_refresh.setToolTip(t("btn_refresh"))

        for btn in (self._btn_standard, self._btn_multi):
            btn.setMinimumHeight(30)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_refresh.setMinimumHeight(30)
        self._btn_refresh.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        self._btn_standard.clicked.connect(lambda: self._set_mode(GAME_MODE_STANDARD))
        self._btn_multi.clicked.connect(lambda: self._set_mode(GAME_MODE_MULTIPLICATIVE))
        self._btn_refresh.clicked.connect(self.refresh)

        mode_row.addWidget(self._btn_standard)
        mode_row.addWidget(self._btn_multi)
        mode_row.addStretch()
        mode_row.addWidget(self._btn_refresh)
        layout.addLayout(mode_row)

        # ── Sort buttons row ─────────────────────────────────────────────
        sort_row = QtWidgets.QHBoxLayout()
        sort_row.setSpacing(3)

        self._sort_buttons: dict[str, QtWidgets.QPushButton] = {}
        for key, label_key in _SORT_KEYS:
            btn = QtWidgets.QPushButton(t(label_key))
            btn.setMinimumHeight(26)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(lambda checked, k=key: self._set_sort(k))
            self._sort_buttons[key] = btn
            sort_row.addWidget(btn)
        sort_row.addStretch()
        layout.addLayout(sort_row)

        # ── Table ────────────────────────────────────────────────────────
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        for i, (_, _, width) in enumerate(_COLUMNS):
            self._table.setColumnWidth(i, width)
        layout.addWidget(self._table, 1)

        # ── Status label ─────────────────────────────────────────────────
        self._status_label = QtWidgets.QLabel()
        self._status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; font-style: italic; padding: 20px; background: transparent;"
        )
        self._status_label.hide()
        layout.addWidget(self._status_label)

        self._apply_mode_style()
        self._apply_sort_style()
        self._apply_table_style()

    # ── Styling ──────────────────────────────────────────────────────────────

    def _apply_table_style(self) -> None:
        # Reuse same style logic as LeaderboardWidget
        dark = get_theme() != "light"
        if dark:
            self._table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {BG_PANEL}; border: 1px solid #2a2a4a;
                    border-radius: 6px; gridline-color: #2a2a4a;
                    color: {TEXT_MAIN}; font-size: 12px;
                }}
                QTableWidget::item {{ padding: 4px 6px; }}
                QTableWidget::item:selected {{ background-color: {ACCENT_DIM}; color: #fff8e0; }}
                QHeaderView::section {{
                    background-color: {BG_CARD}; color: {ACCENT};
                    font-weight: 700; font-size: 11px;
                    border: none; border-bottom: 2px solid {ACCENT_DIM}; padding: 5px 4px;
                }}
            """)
        else:
            self._table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: #e4e4ee; border: 1px solid #ccccdd;
                    border-radius: 6px; gridline-color: #ccccdd;
                    color: #1a1a2e; font-size: 12px;
                }}
                QTableWidget::item {{ padding: 4px 6px; }}
                QTableWidget::item:selected {{ background-color: #c9a84c; color: #ffffff; }}
                QHeaderView::section {{
                    background-color: #f8f8ff; color: #9b7a1e;
                    font-weight: 700; font-size: 11px;
                    border: none; border-bottom: 2px solid #c9a84c; padding: 5px 4px;
                }}
            """)

    def _apply_mode_style(self) -> None:
        dark = get_theme() != "light"
        for btn, mode in [(self._btn_standard, GAME_MODE_STANDARD),
                          (self._btn_multi, GAME_MODE_MULTIPLICATIVE)]:
            active = (mode == self._current_mode)
            if dark:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {ACCENT_DIM}; color: #fff8e0; border: 1px solid {ACCENT}; border-radius: 5px; font-weight: 700; font-size: 12px; padding: 4px 12px; }}"
                    if active else
                    f"QPushButton {{ background: {BG_CARD}; color: {TEXT_DIM}; border: 1px solid #3a3a6a; border-radius: 5px; font-size: 12px; padding: 4px 12px; }}"
                    f"QPushButton:hover {{ border-color: {ACCENT_DIM}; color: {TEXT_MAIN}; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: #9b7a1e; color: #ffffff; border: 1px solid #c9a84c; border-radius: 5px; font-weight: 700; font-size: 12px; padding: 4px 12px; }"
                    if active else
                    "QPushButton { background: #f8f8ff; color: #555577; border: 1px solid #aaaacc; border-radius: 5px; font-size: 12px; padding: 4px 12px; }"
                    "QPushButton:hover { border-color: #9b7a1e; color: #1a1a2e; }"
                )

    def _apply_sort_style(self) -> None:
        dark = get_theme() != "light"
        for key, btn in self._sort_buttons.items():
            active = (key == self._current_sort)
            if dark:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {ACCENT}; color: {BG_DEEP}; border: none; border-radius: 4px; font-weight: 700; font-size: 11px; padding: 3px 8px; }}"
                    if active else
                    f"QPushButton {{ background: transparent; color: {TEXT_DIM}; border: 1px solid #3a3a6a; border-radius: 4px; font-size: 11px; padding: 3px 8px; }}"
                    f"QPushButton:hover {{ color: {ACCENT}; border-color: {ACCENT_DIM}; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: #9b7a1e; color: #ffffff; border: none; border-radius: 4px; font-weight: 700; font-size: 11px; padding: 3px 8px; }"
                    if active else
                    "QPushButton { background: transparent; color: #555577; border: 1px solid #aaaacc; border-radius: 4px; font-size: 11px; padding: 3px 8px; }"
                    "QPushButton:hover { color: #9b7a1e; border-color: #9b7a1e; }"
                )

    # ── Mode / Sort switching ────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        if mode == self._current_mode:
            return
        self._current_mode = mode
        self._apply_mode_style()
        self.refresh()

    def _set_sort(self, key: str) -> None:
        if key == self._current_sort:
            return
        self._current_sort = key
        self._apply_sort_style()
        self._render_data()

    # ── Data fetching ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        if not self._group_code:
            self._show_status(t("group_required"))
            return
        url = get_leaderboard_url()
        if not url:
            self._show_status(t("lb_error"))
            return
        self._show_status(t("lb_loading"))
        from leaderboard_client import LeaderboardClient, GroupPlayerLeaderboardWorker
        client = LeaderboardClient(url)
        self._fetch_worker = GroupPlayerLeaderboardWorker(client, self._group_code, self._current_mode)
        self._fetch_worker.result.connect(self._on_data_received)
        self._fetch_worker.start()

    def _on_data_received(self, data: object) -> None:
        if data is None:
            self._show_status(t("lb_error"))
            return
        self._data = data
        if not data:
            self._show_status(t("lb_no_data"))
            return
        self._status_label.hide()
        self._table.show()
        self._render_data()

    def _show_status(self, text: str) -> None:
        self._table.setRowCount(0)
        self._table.hide()
        self._status_label.setText(text)
        self._status_label.show()

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render_data(self) -> None:
        sorted_data = sorted(
            self._data,
            key=lambda row: row.get(self._current_sort, 0),
            reverse=True,
        )
        self._table.setRowCount(len(sorted_data))
        for row_idx, entry in enumerate(sorted_data):
            for col_idx, (data_key, _, _) in enumerate(_COLUMNS):
                if data_key == "_rank":
                    value = str(row_idx + 1)
                elif data_key in ("win_rate", "hit_rate", "avg_score"):
                    value = f"{entry.get(data_key, 0):.1f}"
                    if data_key in ("win_rate", "hit_rate"):
                        value += "%"
                else:
                    value = str(entry.get(data_key, ""))

                item = QtWidgets.QTableWidgetItem(value)
                if data_key != "name":
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                else:
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                if row_idx == 0 and data_key in ("_rank", "name"):
                    item.setForeground(QtGui.QColor(LEADER))
                    f = item.font(); f.setBold(True); item.setFont(f)
                if data_key == self._current_sort:
                    dark = get_theme() != "light"
                    item.setForeground(QtGui.QColor(ACCENT if dark else "#9b7a1e"))
                    f = item.font(); f.setBold(True); item.setFont(f)
                self._table.setItem(row_idx, col_idx, item)
        self._table.resizeRowsToContents()

    # ── Public API ───────────────────────────────────────────────────────────

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    def retranslate_ui(self) -> None:
        self._btn_standard.setText(t("game_mode_standard"))
        self._btn_multi.setText(t("game_mode_multiplicative"))
        self._btn_refresh.setToolTip(t("btn_refresh"))
        for key, label_key in _SORT_KEYS:
            self._sort_buttons[key].setText(t(label_key))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _COLUMNS])
        self._apply_mode_style()
        self._apply_sort_style()
        self._apply_table_style()

    def restyle(self) -> None:
        self._apply_mode_style()
        self._apply_sort_style()
        self._apply_table_style()
