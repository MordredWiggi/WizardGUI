"""
groups_view.py - List and CRUD for all groups.

Double-clicking a row (or pressing the "Open group" button) emits
open_group so MainWindow can switch to the group's detail view, which
hosts the Games and Players tabs for that group.
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets

from db_backend import DbBackend
from dialogs import ConfirmDialog, DangerConfirmDialog, GroupEditDialog
from views_base import BaseView, fill_table, make_table, push_button, selected_row_index


class GroupsView(BaseView):
    open_group = QtCore.pyqtSignal(dict)

    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self.set_title(
            "Groups",
            "Manage all play groups (codes and visibility included).",
        )

        # Toolbar
        self._search_edit = QtWidgets.QLineEdit()
        self._search_edit.setPlaceholderText("Search by name or code...")
        self._search_edit.setMaximumWidth(280)
        self._search_edit.textChanged.connect(self._on_search)
        self.add_toolbar_widget(self._search_edit)

        self.add_toolbar_stretch()

        btn_refresh = push_button("⟳  Refresh", role="toolbar_btn")
        btn_refresh.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_refresh)

        btn_add = push_button("＋  New group")
        btn_add.clicked.connect(self._add_group)
        self.add_toolbar_widget(btn_add)

        btn_edit = push_button("✎  Edit")
        btn_edit.clicked.connect(self._edit_group)
        self.add_toolbar_widget(btn_edit)

        btn_open = push_button("→  Open group", role="primary")
        btn_open.clicked.connect(self._open_group)
        self.add_toolbar_widget(btn_open)

        btn_del = push_button("🗑  Delete", role="danger")
        btn_del.clicked.connect(self._delete_group)
        self.add_toolbar_widget(btn_del)

        # Table
        self._table = make_table(
            ["ID", "Name", "Code", "Visibility", "Games", "Players"]
        )
        self._table.cellDoubleClicked.connect(lambda *_: self._open_group())
        self.add_to_body(self._table, stretch=1)

        self._all_rows: list[dict] = []

    # -- Data loading -------------------------------------------------------

    def refresh(self) -> None:
        rows = self.safe(self._fetch_groups)
        if rows is None:
            return
        self._all_rows = rows
        self._render(self._search_edit.text().strip().lower())
        self.set_status(f"{len(rows)} group(s) loaded.", success=True)

    def _fetch_groups(self) -> list[dict]:
        return self.backend.query(
            """
            SELECT gr.id, gr.name, gr.code, gr.visibility,
                   COUNT(DISTINCT g.id)         AS games,
                   COUNT(DISTINCT r.player_id)  AS players
              FROM groups gr
         LEFT JOIN games   g ON g.group_id = gr.id
         LEFT JOIN results r ON r.game_id  = g.id
          GROUP BY gr.id
          ORDER BY gr.name COLLATE NOCASE
            """
        )

    def _render(self, search: str = "") -> None:
        if search:
            rows = [
                r
                for r in self._all_rows
                if search in (r.get("name") or "").lower()
                or search in (r.get("code") or "")
            ]
        else:
            rows = self._all_rows
        fill_table(
            self._table,
            rows,
            [
                ("id", "ID"),
                ("name", "Name"),
                ("code", "Code"),
                ("visibility", "Visibility"),
                ("games", "Games"),
                ("players", "Players"),
            ],
        )

    def _on_search(self, _text: str) -> None:
        self._render(self._search_edit.text().strip().lower())

    def _selected_group(self) -> Optional[dict]:
        idx = selected_row_index(self._table)
        if idx is None:
            return None
        gid_item = self._table.item(idx, 0)
        if gid_item is None:
            return None
        try:
            gid = int(gid_item.text())
        except ValueError:
            return None
        for g in self._all_rows:
            if g["id"] == gid:
                return g
        return None

    # -- Actions ------------------------------------------------------------

    def _add_group(self) -> None:
        dlg = GroupEditDialog(self)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        v = dlg.values
        ok = self.safe(
            self.backend.execute,
            "INSERT INTO groups (name, code, visibility) VALUES (?, ?, ?)",
            (v["name"], v["code"], v["visibility"]),
        )
        if ok is None:
            return
        self.set_status(f"Group '{v['name']}' created.", success=True)
        self.refresh()

    def _edit_group(self) -> None:
        group = self._selected_group()
        if not group:
            self.set_status("No group selected.", success=False)
            return
        dlg = GroupEditDialog(self, group=group)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        v = dlg.values
        ok = self.safe(
            self.backend.execute,
            "UPDATE groups SET name = ?, code = ?, visibility = ? WHERE id = ?",
            (v["name"], v["code"], v["visibility"], group["id"]),
        )
        if ok is None:
            return
        self.set_status(f"Group '{v['name']}' updated.", success=True)
        self.refresh()

    def _delete_group(self) -> None:
        group = self._selected_group()
        if not group:
            self.set_status("No group selected.", success=False)
            return
        n_games = group.get("games", 0)
        n_players = group.get("players", 0)
        detail = (
            f"Group ID:    {group['id']}\n"
            f"Name:        {group['name']}\n"
            f"Code:        {group['code']}\n"
            f"Visibility:  {group['visibility']}\n"
            f"Games:       {n_games}\n"
            f"Players:     {n_players}\n\n"
            "This will delete the group, all of its games and every\n"
            "associated player result."
        )
        dlg = DangerConfirmDialog(
            self,
            title="Delete group?",
            message=(
                f"Permanently delete group <b>{group['name']}</b>?"
            ),
            confirm_phrase=group["code"],
            detail=detail,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        # Cascading delete: results -> games -> group.
        # Group id is an integer we control, so injection is impossible here.
        gid = int(group["id"])
        sql = (
            f"DELETE FROM results "
            f" WHERE game_id IN (SELECT id FROM games WHERE group_id = {gid});\n"
            f"DELETE FROM games  WHERE group_id = {gid};\n"
            f"DELETE FROM groups WHERE id = {gid};"
        )
        ok = self.safe(self.backend.executescript, sql)
        if ok is None:
            return
        self.set_status(f"Group '{group['name']}' deleted.", success=True)
        self.refresh()

    def _open_group(self) -> None:
        group = self._selected_group()
        if not group:
            self.set_status("No group selected.", success=False)
            return
        self.open_group.emit(group)
