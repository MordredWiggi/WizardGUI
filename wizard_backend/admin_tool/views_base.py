"""
views_base.py - Shared base components for every view widget.
"""

from __future__ import annotations

from typing import Iterable, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from db_backend import DbBackend, DbError
from style import ACCENT, ADMIN_RED, TEXT_DIM, TEXT_MAIN


class BaseView(QtWidgets.QWidget):
    """Standard layout: header (title + subtitle) + toolbar + body + status."""

    def __init__(self, backend: DbBackend) -> None:
        super().__init__()
        self.backend = backend

        self._main = QtWidgets.QVBoxLayout(self)
        self._main.setContentsMargins(24, 22, 24, 18)
        self._main.setSpacing(12)

        self._title_lbl = QtWidgets.QLabel("")
        self._title_lbl.setObjectName("title")
        self._main.addWidget(self._title_lbl)

        self._subtitle_lbl = QtWidgets.QLabel("")
        self._subtitle_lbl.setObjectName("subtitle")
        self._main.addWidget(self._subtitle_lbl)

        self._toolbar = QtWidgets.QHBoxLayout()
        self._toolbar.setSpacing(8)
        self._main.addLayout(self._toolbar)

        # Body container – subclasses fill via add_to_body()
        self._body = QtWidgets.QVBoxLayout()
        self._body.setSpacing(10)
        self._main.addLayout(self._body, 1)

        self._status_lbl = QtWidgets.QLabel("")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px;")
        self._main.addWidget(self._status_lbl)

    def set_title(self, title: str, subtitle: str = "") -> None:
        self._title_lbl.setText(title)
        self._subtitle_lbl.setText(subtitle)
        self._subtitle_lbl.setVisible(bool(subtitle))

    def add_toolbar_widget(self, widget: QtWidgets.QWidget) -> None:
        self._toolbar.addWidget(widget)

    def add_toolbar_stretch(self) -> None:
        self._toolbar.addStretch()

    def add_to_body(self, widget: QtWidgets.QWidget, stretch: int = 0) -> None:
        self._body.addWidget(widget, stretch)

    def add_layout_to_body(self, layout: QtWidgets.QLayout, stretch: int = 0) -> None:
        self._body.addLayout(layout, stretch)

    def set_status(self, text: str, success: bool = True) -> None:
        color = ACCENT if success else ADMIN_RED
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        self._status_lbl.setText(text)

    # -- error wrapper ------------------------------------------------------

    def safe(self, func, *args, **kwargs):
        """Run a DB operation; surface DbError as a status + dialog."""
        try:
            return func(*args, **kwargs)
        except DbError as exc:
            self.set_status(f"Error: {exc}", success=False)
            QtWidgets.QMessageBox.warning(self, "Database error", str(exc))
            return None

    def refresh(self) -> None:
        """Override in subclasses to reload data."""


# -- Helpers ------------------------------------------------------------------


def make_table(
    columns: Iterable[str],
    *,
    selection: str = "row",
    edit_triggers_off: bool = True,
    sortable: bool = True,
) -> QtWidgets.QTableWidget:
    cols = list(columns)
    table = QtWidgets.QTableWidget(0, len(cols))
    table.setHorizontalHeaderLabels(cols)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(
        QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        if selection == "row"
        else QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems
    )
    table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    if edit_triggers_off:
        table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
    table.setSortingEnabled(sortable)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(
        QtWidgets.QHeaderView.ResizeMode.Interactive
    )
    return table


def fill_table(
    table: QtWidgets.QTableWidget,
    rows: list[dict],
    columns: list[tuple[str, str]],
) -> None:
    """Populate ``table`` from row dicts.

    ``columns`` = list of (key_in_dict, header_label). Header labels are
    written into ``table.setHorizontalHeaderLabels`` so callers can reuse
    this to also (re-)label.
    """
    table.setSortingEnabled(False)
    table.setRowCount(0)
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels([c[1] for c in columns])
    for r, row in enumerate(rows):
        table.insertRow(r)
        for c, (key, _label) in enumerate(columns):
            val = row.get(key)
            text = "" if val is None else str(val)
            item = QtWidgets.QTableWidgetItem(text)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            if isinstance(val, (int, float)):
                item.setData(QtCore.Qt.ItemDataRole.DisplayRole, val)
                item.setTextAlignment(
                    QtCore.Qt.AlignmentFlag.AlignRight
                    | QtCore.Qt.AlignmentFlag.AlignVCenter
                )
            table.setItem(r, c, item)
    table.setSortingEnabled(True)
    table.resizeColumnsToContents()


def selected_row_index(table: QtWidgets.QTableWidget) -> Optional[int]:
    sel = table.selectionModel().selectedRows()
    if not sel:
        return None
    return sel[0].row()


def push_button(text: str, role: str = "", tooltip: str = "") -> QtWidgets.QPushButton:
    btn = QtWidgets.QPushButton(text)
    if role:
        btn.setObjectName(role)
    if tooltip:
        btn.setToolTip(tooltip)
    btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
    return btn
