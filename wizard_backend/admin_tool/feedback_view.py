"""
feedback_view.py - View, edit, delete feedback entries; reset votes.
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtWidgets

from db_backend import DbBackend
from dialogs import DangerConfirmDialog, TextInputDialog
from views_base import BaseView, fill_table, make_table, push_button, selected_row_index


class FeedbackView(BaseView):
    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self.set_title(
            "Feedback", "Public feedback messages and their up/down votes."
        )

        btn_refresh = push_button("⟳", role="toolbar_btn")
        btn_refresh.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_refresh)

        self.add_toolbar_stretch()

        btn_edit = push_button("✎  Edit message")
        btn_edit.clicked.connect(self._edit)
        self.add_toolbar_widget(btn_edit)

        btn_reset = push_button("↺  Reset votes")
        btn_reset.clicked.connect(self._reset_votes)
        self.add_toolbar_widget(btn_reset)

        btn_del = push_button("🗑  Delete", role="danger")
        btn_del.clicked.connect(self._delete)
        self.add_toolbar_widget(btn_del)

        self._table = make_table(["ID", "Up", "Down", "Net", "Created", "Message"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self.add_to_body(self._table, stretch=1)

        self._all: list[dict] = []

    def refresh(self) -> None:
        rows = self.safe(
            self.backend.query,
            """
            SELECT id, message, upvotes, downvotes, created_at,
                   (upvotes - downvotes) AS net_votes
              FROM feedback
          ORDER BY created_at DESC
            """,
        )
        if rows is None:
            return
        self._all = rows
        fill_table(
            self._table,
            rows,
            [
                ("id", "ID"),
                ("upvotes", "Up"),
                ("downvotes", "Down"),
                ("net_votes", "Net"),
                ("created_at", "Created"),
                ("message", "Message"),
            ],
        )
        self.set_status(f"{len(rows)} entry/entries loaded.", success=True)

    def _selected(self) -> Optional[dict]:
        idx = selected_row_index(self._table)
        if idx is None:
            return None
        item = self._table.item(idx, 0)
        if item is None:
            return None
        try:
            fid = int(item.text())
        except ValueError:
            return None
        for r in self._all:
            if r["id"] == fid:
                return r
        return None

    # -- Actions ------------------------------------------------------------

    def _edit(self) -> None:
        f = self._selected()
        if not f:
            self.set_status("No entry selected.", success=False)
            return
        dlg = TextInputDialog(
            self,
            "Edit feedback message",
            f"ID {f['id']} (created {f['created_at']})",
            default=f.get("message", ""),
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted or not dlg.value:
            return
        ok = self.safe(
            self.backend.execute,
            "UPDATE feedback SET message = ? WHERE id = ?",
            (dlg.value, f["id"]),
        )
        if ok is None:
            return
        self.set_status("Feedback updated.", success=True)
        self.refresh()

    def _reset_votes(self) -> None:
        f = self._selected()
        if not f:
            self.set_status("No entry selected.", success=False)
            return
        ok = self.safe(
            self.backend.execute,
            "UPDATE feedback SET upvotes = 0, downvotes = 0 WHERE id = ?",
            (f["id"],),
        )
        if ok is None:
            return
        self.set_status(f"Votes for entry #{f['id']} reset.", success=True)
        self.refresh()

    def _delete(self) -> None:
        f = self._selected()
        if not f:
            self.set_status("No entry selected.", success=False)
            return
        dlg = DangerConfirmDialog(
            self,
            title="Delete feedback?",
            message=(
                f"Permanently delete entry #{f['id']} "
                f"(net {f.get('net_votes', 0)})?"
            ),
            confirm_phrase=str(f["id"]),
            detail=f.get("message", ""),
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        ok = self.safe(
            self.backend.execute, "DELETE FROM feedback WHERE id = ?", (f["id"],)
        )
        if ok is None:
            return
        self.set_status(f"Entry #{f['id']} deleted.", success=True)
        self.refresh()
