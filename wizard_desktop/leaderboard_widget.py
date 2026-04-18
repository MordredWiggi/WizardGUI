"""
leaderboard_widget.py – Reusable in-app leaderboard views.

Provides:
  • GroupPlayerLeaderboardWidget – player leaderboard for a specific group
    (group-internal only), with Standard/Multiplicative mode toggle,
    clickable header-based sorting, and centered cells.
  • GroupsLeaderboardWidget – global groups ranking (public groups only).

The old global-player leaderboard has been removed: only two leaderboard
kinds exist now — the global groups ranking and each group's internal
player ranking.
"""
from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets, QtGui

from style import (
    ACCENT, ACCENT_DIM, BG_PANEL, BG_CARD, BG_DEEP,
    TEXT_MAIN, TEXT_DIM, LEADER,
)
from app_settings import t, get_leaderboard_url, get_theme
from game_control import GAME_MODE_STANDARD, GAME_MODE_MULTIPLICATIVE


# Sort-capable columns and their header keys.  "_rank" and "name" are not
# sortable; all others are.
_COLUMNS = [
    ("_rank",         "lb_col_rank",     50),
    ("name",          "lb_col_name",    150),
    ("wins",          "lb_col_wins",     70),
    ("games",         "lb_col_games",    70),
    ("win_rate",      "lb_col_win_rate", 80),
    ("avg_score",     "lb_col_avg",      80),
    ("hit_rate",      "lb_col_hit_rate", 80),
    ("highest_score", "lb_col_highest",  80),
    ("win_streak",    "lb_col_streak",   70),
]
_SORTABLE_KEYS = {"wins", "games", "win_rate", "avg_score",
                  "hit_rate", "highest_score", "win_streak"}

_GROUPS_COLUMNS = [
    ("_rank",        "glb_col_rank",      50),
    ("name",         "glb_col_name",     180),
    ("total_games",  "glb_col_games",     80),
    ("avg_score",    "glb_col_avg_score", 90),
    ("avg_hit_rate", "glb_col_hit_rate",  90),
]
_GROUPS_SORTABLE = {"total_games", "avg_score", "avg_hit_rate"}


def _table_stylesheet() -> str:
    dark = get_theme() != "light"
    if dark:
        return f"""
            QTableWidget {{
                background-color: {BG_PANEL};
                border: 1px solid #2a2a4a;
                border-radius: 6px;
                gridline-color: #2a2a4a;
                color: {TEXT_MAIN};
                font-size: 12px;
            }}
            QTableWidget::item {{ padding: 4px 6px; }}
            QTableWidget::item:selected {{
                background-color: {ACCENT_DIM}; color: #fff8e0;
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
            QHeaderView::section:hover {{
                background-color: #2a2a5a;
                color: #fff8e0;
            }}
            QTableWidget QTableCornerButton::section {{
                background-color: {BG_CARD}; border: none;
            }}
        """
    return f"""
        QTableWidget {{
            background-color: #e4e4ee; border: 1px solid #ccccdd;
            border-radius: 6px; gridline-color: #ccccdd;
            color: #1a1a2e; font-size: 12px;
        }}
        QTableWidget::item {{ padding: 4px 6px; }}
        QTableWidget::item:selected {{
            background-color: #c9a84c; color: #ffffff;
        }}
        QHeaderView::section {{
            background-color: #f8f8ff; color: #9b7a1e;
            font-weight: 700; font-size: 11px;
            border: none; border-bottom: 2px solid #c9a84c; padding: 5px 4px;
        }}
        QHeaderView::section:hover {{
            background-color: #efe4bf; color: #5c4a0d;
        }}
    """


def _toggle_btn_style(active: bool) -> str:
    dark = get_theme() != "light"
    if dark:
        if active:
            return (
                f"QPushButton {{ background: {ACCENT_DIM}; color: #fff8e0; "
                f"border: 1px solid {ACCENT}; border-radius: 5px; font-weight: 700; "
                f"font-size: 12px; padding: 4px 12px; }}"
            )
        return (
            f"QPushButton {{ background: {BG_CARD}; color: {TEXT_DIM}; "
            f"border: 1px solid #3a3a6a; border-radius: 5px; font-size: 12px; padding: 4px 12px; }}"
            f"QPushButton:hover {{ border-color: {ACCENT_DIM}; color: {TEXT_MAIN}; }}"
        )
    if active:
        return (
            "QPushButton { background: #9b7a1e; color: #ffffff; "
            "border: 1px solid #c9a84c; border-radius: 5px; font-weight: 700; "
            "font-size: 12px; padding: 4px 12px; }"
        )
    return (
        "QPushButton { background: #f8f8ff; color: #555577; "
        "border: 1px solid #aaaacc; border-radius: 5px; font-size: 12px; padding: 4px 12px; }"
        "QPushButton:hover { border-color: #9b7a1e; color: #1a1a2e; }"
    )


def _refresh_btn_style() -> str:
    # Small refresh button: compact padding so the glyph is visible.
    dark = get_theme() != "light"
    if dark:
        return (
            f"QPushButton {{ background: {BG_CARD}; color: {TEXT_MAIN}; "
            f"border: 1px solid #3a3a6a; border-radius: 5px; "
            f"padding: 0; font-size: 18px; font-weight: 700; }}"
            f"QPushButton:hover {{ border-color: {ACCENT_DIM}; color: {ACCENT}; }}"
        )
    return (
        "QPushButton { background: #f8f8ff; color: #555577; "
        "border: 1px solid #aaaacc; border-radius: 5px; "
        "padding: 0; font-size: 18px; font-weight: 700; }"
        "QPushButton:hover { border-color: #9b7a1e; color: #9b7a1e; }"
    )


class GroupPlayerLeaderboardWidget(QtWidgets.QWidget):
    """Player leaderboard for a specific group, with Standard/Multi mode toggle.

    Sorting is performed by clicking on a column header. Until a group code is
    supplied via :meth:`set_group`, the widget shows an informational status
    message instead of a table.
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._fetch_worker: Optional[object] = None
        self._current_mode = GAME_MODE_STANDARD
        self._current_sort = "wins"
        self._group_code: Optional[str] = None
        self._data: list[dict] = []
        self._build_ui()

    # ── Public API ───────────────────────────────────────────────────────────

    def set_group(self, code: Optional[str]) -> None:
        """Bind the widget to a group (by 4-digit code), or ``None`` to clear."""
        self._group_code = code
        if self.isVisible():
            self.refresh()

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Mode (Standard | Multi) + Refresh ──
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(6)

        self._btn_standard = QtWidgets.QPushButton(t("game_mode_standard"))
        self._btn_multi = QtWidgets.QPushButton(t("game_mode_multiplicative"))
        for btn in (self._btn_standard, self._btn_multi):
            btn.setMinimumHeight(30)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_standard.clicked.connect(lambda: self._set_mode(GAME_MODE_STANDARD))
        self._btn_multi.clicked.connect(lambda: self._set_mode(GAME_MODE_MULTIPLICATIVE))
        top_row.addWidget(self._btn_standard)
        top_row.addWidget(self._btn_multi)

        top_row.addStretch()

        self._btn_refresh = QtWidgets.QPushButton("↻")
        self._btn_refresh.setFixedSize(36, 30)
        self._btn_refresh.setToolTip(t("btn_refresh"))
        self._btn_refresh.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_refresh.clicked.connect(self.refresh)
        top_row.addWidget(self._btn_refresh)

        layout.addLayout(top_row)

        # ── Table (clickable headers drive sort) ────────────────────────
        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        header = self._table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        header.sectionClicked.connect(self._on_header_clicked)

        for i, (_, _, width) in enumerate(_COLUMNS):
            self._table.setColumnWidth(i, width)
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)

        wrap = QtWidgets.QHBoxLayout()
        wrap.addStretch()
        wrap.addWidget(self._table, 10)
        wrap.addStretch()
        layout.addLayout(wrap, 1)

        self._status_label = QtWidgets.QLabel()
        self._status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; font-style: italic; padding: 20px; background: transparent;"
        )
        self._status_label.hide()
        layout.addWidget(self._status_label)

        self._apply_mode_style()
        self._apply_refresh_style()
        self._apply_table_style()

    # ── Styling ──────────────────────────────────────────────────────────────

    def _apply_table_style(self) -> None:
        self._table.setStyleSheet(_table_stylesheet())

    def _apply_mode_style(self) -> None:
        self._btn_standard.setStyleSheet(
            _toggle_btn_style(self._current_mode == GAME_MODE_STANDARD)
        )
        self._btn_multi.setStyleSheet(
            _toggle_btn_style(self._current_mode == GAME_MODE_MULTIPLICATIVE)
        )

    def _apply_refresh_style(self) -> None:
        self._btn_refresh.setStyleSheet(_refresh_btn_style())

    # ── Mode / Sort switching ────────────────────────────────────────────────

    def _set_mode(self, mode: str) -> None:
        if mode == self._current_mode:
            return
        self._current_mode = mode
        self._apply_mode_style()
        self.refresh()

    def _on_header_clicked(self, column: int) -> None:
        key = _COLUMNS[column][0]
        if key not in _SORTABLE_KEYS:
            return
        self._current_sort = key
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
        from leaderboard_client import (
            LeaderboardClient,
            GroupPlayerLeaderboardWorker,
        )
        client = LeaderboardClient(url)
        self._fetch_worker = GroupPlayerLeaderboardWorker(
            client, self._group_code, self._current_mode
        )
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
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                if row_idx == 0 and data_key in ("_rank", "name"):
                    item.setForeground(QtGui.QColor(LEADER))
                    f = item.font(); f.setBold(True); item.setFont(f)

                if data_key == self._current_sort:
                    dark = get_theme() != "light"
                    item.setForeground(QtGui.QColor(ACCENT if dark else "#9b7a1e"))
                    f = item.font(); f.setBold(True); item.setFont(f)

                self._table.setItem(row_idx, col_idx, item)

        self._table.resizeRowsToContents()

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    def retranslate_ui(self) -> None:
        self._btn_standard.setText(t("game_mode_standard"))
        self._btn_multi.setText(t("game_mode_multiplicative"))
        self._btn_refresh.setToolTip(t("btn_refresh"))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _COLUMNS])
        self._apply_mode_style()
        self._apply_refresh_style()
        self._apply_table_style()

    def restyle(self) -> None:
        self._apply_mode_style()
        self._apply_refresh_style()
        self._apply_table_style()


# ─────────────────────────────────────────────────────────────────────────────
# GroupsLeaderboardWidget – global groups ranking
# ─────────────────────────────────────────────────────────────────────────────

class GroupsLeaderboardWidget(QtWidgets.QWidget):
    """Groups leaderboard; header clicks drive the sort."""

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

        top_row = QtWidgets.QHBoxLayout()
        top_row.addStretch()
        self._btn_refresh = QtWidgets.QPushButton("↻")
        self._btn_refresh.setFixedSize(36, 30)
        self._btn_refresh.setToolTip(t("btn_refresh"))
        self._btn_refresh.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._btn_refresh.clicked.connect(self.refresh)
        top_row.addWidget(self._btn_refresh)
        layout.addLayout(top_row)

        self._table = QtWidgets.QTableWidget()
        self._table.setColumnCount(len(_GROUPS_COLUMNS))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _GROUPS_COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)

        header = self._table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        header.sectionClicked.connect(self._on_header_clicked)
        for i, (_, _, width) in enumerate(_GROUPS_COLUMNS):
            self._table.setColumnWidth(i, width)
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.Stretch)

        wrap = QtWidgets.QHBoxLayout()
        wrap.addStretch()
        wrap.addWidget(self._table, 10)
        wrap.addStretch()
        layout.addLayout(wrap, 1)

        self._status_label = QtWidgets.QLabel()
        self._status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; font-style: italic; padding: 20px; background: transparent;"
        )
        self._status_label.hide()
        layout.addWidget(self._status_label)

        self._apply_refresh_style()
        self._apply_table_style()

    def _apply_table_style(self) -> None:
        self._table.setStyleSheet(_table_stylesheet())

    def _apply_refresh_style(self) -> None:
        self._btn_refresh.setStyleSheet(_refresh_btn_style())

    def _on_header_clicked(self, column: int) -> None:
        key = _GROUPS_COLUMNS[column][0]
        if key not in _GROUPS_SORTABLE:
            return
        self._current_sort = key
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
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

                if row_idx == 0 and data_key in ("_rank", "name"):
                    item.setForeground(QtGui.QColor(LEADER))
                    f = item.font(); f.setBold(True); item.setFont(f)

                if data_key == self._current_sort:
                    dark = get_theme() != "light"
                    item.setForeground(QtGui.QColor(ACCENT if dark else "#9b7a1e"))
                    f = item.font(); f.setBold(True); item.setFont(f)
                self._table.setItem(row_idx, col_idx, item)
        self._table.resizeRowsToContents()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self.refresh()

    def retranslate_ui(self) -> None:
        self._btn_refresh.setToolTip(t("btn_refresh"))
        self._table.setHorizontalHeaderLabels([t(col[1]) for col in _GROUPS_COLUMNS])
        self._apply_refresh_style()
        self._apply_table_style()

    def restyle(self) -> None:
        self._apply_refresh_style()
        self._apply_table_style()
