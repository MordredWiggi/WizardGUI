"""
sql_console.py - Run arbitrary SQL.

  - Defaults to read-only mode (only SELECT/PRAGMA/EXPLAIN/WITH allowed)
  - The "Write mode" toggle must be enabled explicitly to run mutations
  - Mutating statements ask for an extra confirmation before execution
"""

from __future__ import annotations

import re
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from db_backend import DbBackend, list_tables
from dialogs import ConfirmDialog
from style import ACCENT, ADMIN_RED, BG_CARD, TEXT_DIM, TEXT_MAIN
from views_base import BaseView, fill_table, make_table, push_button


_READONLY_PREFIXES = ("select", "with", "pragma", "explain")


class SqlConsole(BaseView):
    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self.set_title(
            "SQL Console",
            "Run arbitrary SQL - mutations require enabling write mode.",
        )

        self._chk_write = QtWidgets.QCheckBox("Write mode (dangerous)")
        self._chk_write.setStyleSheet(f"color: {ADMIN_RED}; font-weight: 600;")
        self.add_toolbar_widget(self._chk_write)

        self.add_toolbar_stretch()

        btn_clear = push_button("Clear", role="toolbar_btn")
        btn_clear.clicked.connect(lambda: self._editor.setPlainText(""))
        self.add_toolbar_widget(btn_clear)

        btn_tables = push_button("Show tables", role="toolbar_btn")
        btn_tables.clicked.connect(self._show_tables)
        self.add_toolbar_widget(btn_tables)

        btn_run = push_button("▶  Run  (Ctrl+Enter)", role="primary")
        btn_run.clicked.connect(self._run)
        self.add_toolbar_widget(btn_run)

        # Editor
        self._editor = QtWidgets.QPlainTextEdit()
        self._editor.setPlaceholderText("SELECT * FROM groups;")
        self._editor.setMinimumHeight(150)
        sc = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self._editor)
        sc.activated.connect(self._run)
        sc2 = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self._editor)
        sc2.activated.connect(self._run)
        self.add_to_body(self._editor)

        # Result table
        self._table = make_table(["(no results yet)"], sortable=False)
        self.add_to_body(self._table, stretch=1)

    def refresh(self) -> None:
        # Nothing to refresh by default; user runs queries explicitly.
        pass

    # -- helpers ------------------------------------------------------------

    def _show_tables(self) -> None:
        names = self.safe(list_tables, self.backend) or []
        self._editor.setPlainText(
            "-- Tables:\n"
            + "\n".join(f"-- {n}" for n in names)
            + "\nSELECT name FROM sqlite_master WHERE type='table';"
        )

    def _is_readonly(self, sql: str) -> bool:
        body = sql.strip().lstrip("-")
        body = re.sub(r"^\s*(--[^\n]*\n)+", "", body, flags=re.MULTILINE).strip().lower()
        return body.startswith(_READONLY_PREFIXES)

    def _run(self) -> None:
        sql = self._editor.toPlainText().strip()
        if not sql:
            self.set_status("Empty input.", success=False)
            return

        readonly = self._is_readonly(sql)
        if not readonly and not self._chk_write.isChecked():
            self.set_status(
                "Write statement detected - please enable write mode first.",
                success=False,
            )
            return

        if not readonly:
            dlg = ConfirmDialog(
                self,
                title="Execute SQL?",
                message="This statement modifies the database:",
                detail=sql,
                ok_text="Execute",
                ok_role="danger",
            )
            if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return

        if readonly:
            rows = self.safe(self.backend.query, sql)
            if rows is None:
                return
            self._render_rows(rows)
            self.set_status(f"OK - {len(rows)} row(s).", success=True)
        else:
            # Multiple statements -> executescript; otherwise execute.
            if ";" in sql.rstrip(";"):
                self.safe(self.backend.executescript, sql)
            else:
                rc = self.safe(self.backend.execute, sql)
                if rc is None:
                    return
                self.set_status(f"OK - {rc} row(s) affected.", success=True)
                return
            self.set_status("OK - script executed.", success=True)

    def _render_rows(self, rows: list[dict]) -> None:
        if not rows:
            fill_table(self._table, [], [("_empty", "(0 rows)")])
            return
        cols = list(rows[0].keys())
        fill_table(self._table, rows, [(c, c) for c in cols])
