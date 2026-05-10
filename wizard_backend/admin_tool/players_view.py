"""
players_view.py - Player management with merge support.
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets

from db_backend import DbBackend
from dialogs import DangerConfirmDialog, PlayerMergeDialog, TextInputDialog
from views_base import BaseView, fill_table, make_table, push_button, selected_row_index


class PlayersView(BaseView):
    player_changed = QtCore.pyqtSignal()

    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self.set_title(
            "Players",
            "Global player list - changes affect every group and every game.",
        )

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search...")
        self._search.setMaximumWidth(280)
        self._search.textChanged.connect(self._render_filtered)
        self.add_toolbar_widget(self._search)

        self.add_toolbar_stretch()

        btn_refresh = push_button("⟳", role="toolbar_btn")
        btn_refresh.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_refresh)

        btn_rename = push_button("✎  Rename")
        btn_rename.clicked.connect(self._rename)
        self.add_toolbar_widget(btn_rename)

        btn_merge = push_button("⇋  Merge", role="primary")
        btn_merge.clicked.connect(self._merge)
        self.add_toolbar_widget(btn_merge)

        btn_del = push_button("🗑  Delete", role="danger")
        btn_del.clicked.connect(self._delete)
        self.add_toolbar_widget(btn_del)

        self._table = make_table(
            ["ID", "Name", "Games", "Wins", "Avg score", "Groups"]
        )
        self.add_to_body(self._table, stretch=1)

        self._all: list[dict] = []

    def refresh(self) -> None:
        rows = self.safe(self._fetch_players)
        if rows is None:
            return
        self._all = rows
        self._render_filtered()
        self.set_status(f"{len(rows)} player(s) loaded.", success=True)

    def _fetch_players(self) -> list[dict]:
        return self.backend.query(
            """
            SELECT p.id,
                   p.name,
                   COUNT(r.game_id)                               AS games,
                   SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END)    AS wins,
                   ROUND(AVG(r.final_score), 1)                   AS avg_score,
                   COUNT(DISTINCT g.group_id)                     AS groups
              FROM players p
         LEFT JOIN results r ON r.player_id = p.id
         LEFT JOIN games   g ON g.id = r.game_id
          GROUP BY p.id
          ORDER BY p.name COLLATE NOCASE
            """
        )

    def _render_filtered(self) -> None:
        q = self._search.text().strip().lower()
        rows = (
            [r for r in self._all if q in (r.get("name") or "").lower()]
            if q
            else self._all
        )
        fill_table(
            self._table,
            rows,
            [
                ("id", "ID"),
                ("name", "Name"),
                ("games", "Games"),
                ("wins", "Wins"),
                ("avg_score", "Avg score"),
                ("groups", "Groups"),
            ],
        )

    def _selected(self) -> Optional[dict]:
        idx = selected_row_index(self._table)
        if idx is None:
            return None
        item = self._table.item(idx, 0)
        if item is None:
            return None
        try:
            pid = int(item.text())
        except ValueError:
            return None
        for p in self._all:
            if p["id"] == pid:
                return p
        return None

    # -- Actions ------------------------------------------------------------

    def _rename(self) -> None:
        p = self._selected()
        if not p:
            self.set_status("No player selected.", success=False)
            return
        dlg = TextInputDialog(
            self, "Rename player", "New name:", default=p["name"]
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted or not dlg.value:
            return
        ok = self.safe(
            self.backend.execute,
            "UPDATE players SET name = ? WHERE id = ?",
            (dlg.value, p["id"]),
        )
        if ok is None:
            return
        self.set_status(f"Player #{p['id']} renamed.", success=True)
        self.refresh()
        self.player_changed.emit()

    def _merge(self) -> None:
        p = self._selected()
        if not p:
            self.set_status("No player selected.", success=False)
            return
        if len(self._all) < 2:
            self.set_status("Nothing to merge.", success=False)
            return
        dlg = PlayerMergeDialog(self, players=self._all, source_player=p)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        target_id = dlg.target_id
        if target_id is None or target_id == p["id"]:
            return
        # Move all results from source -> target. (game_id, player_id) is the
        # PK, so if the target already has a result for one of the source's
        # games the source row has to be dropped first.
        sql = (
            f"DELETE FROM results WHERE player_id = {int(p['id'])} "
            f"AND game_id IN ("
            f"  SELECT game_id FROM results WHERE player_id = {int(target_id)});\n"
            f"UPDATE results SET player_id = {int(target_id)} "
            f"WHERE player_id = {int(p['id'])};\n"
            f"DELETE FROM players WHERE id = {int(p['id'])};"
        )
        ok = self.safe(self.backend.executescript, sql)
        if ok is None:
            return
        self.set_status(
            f"Player #{p['id']} ({p['name']}) -> #{target_id}.", success=True
        )
        self.refresh()
        self.player_changed.emit()

    def _delete(self) -> None:
        p = self._selected()
        if not p:
            self.set_status("No player selected.", success=False)
            return
        detail = (
            f"Player ID:  {p['id']}\n"
            f"Name:       {p['name']}\n"
            f"Games:      {p.get('games', 0)}\n\n"
            "All results for this player will be deleted as well."
        )
        dlg = DangerConfirmDialog(
            self,
            title="Delete player?",
            message=(
                f"Permanently delete <b>{p['name']}</b> and all of their results?"
            ),
            confirm_phrase=p["name"],
            detail=detail,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        sql = (
            f"DELETE FROM results WHERE player_id = {int(p['id'])};\n"
            f"DELETE FROM players WHERE id = {int(p['id'])};"
        )
        ok = self.safe(self.backend.executescript, sql)
        if ok is None:
            return
        self.set_status(f"Player #{p['id']} deleted.", success=True)
        self.refresh()
        self.player_changed.emit()
