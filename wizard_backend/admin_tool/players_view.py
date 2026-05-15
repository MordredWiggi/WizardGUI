"""
players_view.py - "All players" view.

There is no global player leaderboard. Each row represents one player's
stats inside one group, so the same human appears once per group they have
played in. Rename / merge / delete therefore act only on the row's group
and never touch results in any other group.
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets

from db_backend import DbBackend, DbError
from dialogs import (
    DangerConfirmDialog,
    GroupPlayerMergeDialog,
    GroupPlayerRenameDialog,
)
from player_ops import (
    delete_player_in_group,
    ensure_player,
    fetch_players_in_group,
    reassign_in_group,
)
from views_base import (
    BaseView,
    fill_table,
    make_table,
    push_button,
    selected_row_index,
)


class PlayersView(BaseView):
    """Lists every (group, player) pair and supports group-scoped edits."""

    player_changed = QtCore.pyqtSignal()

    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self.set_title(
            "All players",
            "One row per (group, player). Rename, merge and delete apply "
            "only inside the player's group.",
        )

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search by group or name...")
        self._search.setMaximumWidth(320)
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
            ["Player ID", "Group", "Name", "Games", "Wins", "Avg score"]
        )
        self.add_to_body(self._table, stretch=1)

        self._all: list[dict] = []
        self._filtered: list[dict] = []

    # -- Data ---------------------------------------------------------------

    def refresh(self) -> None:
        rows = self.safe(self._fetch_rows)
        if rows is None:
            return
        self._all = rows
        self._render_filtered()
        self.set_status(f"{len(rows)} (group, player) row(s) loaded.", success=True)

    def _fetch_rows(self) -> list[dict]:
        return self.backend.query(
            """
            SELECT p.id          AS id,
                   p.name        AS name,
                   gr.id         AS group_id,
                   gr.name       AS group_name,
                   gr.code       AS group_code,
                   gr.visibility AS visibility,
                   COUNT(r.game_id)                            AS games,
                   SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END) AS wins,
                   ROUND(AVG(r.final_score), 1)               AS avg_score
              FROM players p
              JOIN results r  ON r.player_id = p.id
              JOIN games   g  ON g.id = r.game_id
              JOIN groups  gr ON gr.id = g.group_id
          GROUP BY p.id, gr.id
          ORDER BY gr.name COLLATE NOCASE, p.name COLLATE NOCASE
            """
        )

    def _render_filtered(self) -> None:
        q = self._search.text().strip().lower()
        if q:
            self._filtered = [
                r
                for r in self._all
                if q in (r.get("name") or "").lower()
                or q in (r.get("group_name") or "").lower()
            ]
        else:
            self._filtered = list(self._all)
        fill_table(
            self._table,
            self._filtered,
            [
                ("id", "Player ID"),
                ("group_name", "Group"),
                ("name", "Name"),
                ("games", "Games"),
                ("wins", "Wins"),
                ("avg_score", "Avg score"),
            ],
        )

    def _selected(self) -> Optional[dict]:
        """Recover the dict for the selected row, even after sort/filter.

        The table's column 0 is the player id and column 1 is the group's
        display name. (player_id, group_name) is unique enough in practice -
        if two groups share a name we fall back to the first match, which
        keeps behaviour deterministic.
        """
        idx = selected_row_index(self._table)
        if idx is None:
            return None
        pid_item = self._table.item(idx, 0)
        grp_item = self._table.item(idx, 1)
        if pid_item is None or grp_item is None:
            return None
        try:
            pid = int(pid_item.text())
        except ValueError:
            return None
        gname = grp_item.text()
        for r in self._all:
            if r["id"] == pid and (r.get("group_name") or "") == gname:
                return r
        return None

    # -- Actions ------------------------------------------------------------

    def _rename(self) -> None:
        row = self._selected()
        if not row:
            self.set_status("No player selected.", success=False)
            return
        group = self._group_dict(row)
        peers = self.safe(fetch_players_in_group, self.backend, group["id"])
        if peers is None:
            return
        dlg = GroupPlayerRenameDialog(
            self,
            group=group,
            players_in_group=peers,
            preselect_id=row["id"],
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        src_id = dlg.player_id
        new_name = dlg.new_name
        if src_id is None or not new_name:
            return
        try:
            tgt = ensure_player(self.backend, new_name)
            reassign_in_group(
                self.backend, [(int(src_id), tgt)], group_id=int(group["id"])
            )
        except DbError as exc:
            self._report_error(exc)
            return
        self.set_status(
            f"Player #{src_id} renamed to '{new_name}' in group "
            f"'{group['name']}'.",
            success=True,
        )
        self.refresh()
        self.player_changed.emit()

    def _merge(self) -> None:
        row = self._selected()
        if not row:
            self.set_status("No player selected.", success=False)
            return
        group = self._group_dict(row)
        peers = self.safe(fetch_players_in_group, self.backend, group["id"])
        if peers is None:
            return
        if len(peers) < 2:
            self.set_status(
                f"Only one player in group '{group['name']}' - nothing "
                "to merge with.",
                success=False,
            )
            return
        dlg = GroupPlayerMergeDialog(
            self,
            group=group,
            players_in_group=peers,
            preselect_a_id=row["id"],
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        a_id = dlg.player_a_id
        b_id = dlg.player_b_id
        new_name = dlg.new_name
        if a_id is None or b_id is None or a_id == b_id or not new_name:
            return
        try:
            tgt = ensure_player(self.backend, new_name)
            reassign_in_group(
                self.backend,
                [(int(a_id), tgt), (int(b_id), tgt)],
                group_id=int(group["id"]),
            )
        except DbError as exc:
            self._report_error(exc)
            return
        self.set_status(
            f"Players #{a_id} and #{b_id} merged into '{new_name}' in "
            f"group '{group['name']}'.",
            success=True,
        )
        self.refresh()
        self.player_changed.emit()

    def _delete(self) -> None:
        row = self._selected()
        if not row:
            self.set_status("No player selected.", success=False)
            return
        group = self._group_dict(row)
        detail = (
            f"Player:     {row['name']}\n"
            f"Player ID:  {row['id']}\n"
            f"Group:      {group['name']} (code {group['code']})\n"
            f"Games:      {row.get('games', 0)}\n\n"
            "Only this player's results inside this group will be removed.\n"
            "If the player has no results anywhere else, the player record\n"
            "itself is deleted as well."
        )
        dlg = DangerConfirmDialog(
            self,
            title="Delete player in group?",
            message=(
                f"Remove <b>{row['name']}</b> from group "
                f"<b>{group['name']}</b>?"
            ),
            confirm_phrase=row["name"],
            detail=detail,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        try:
            delete_player_in_group(
                self.backend,
                player_id=int(row["id"]),
                group_id=int(group["id"]),
            )
        except DbError as exc:
            self._report_error(exc)
            return
        self.set_status(
            f"Player #{row['id']} removed from group '{group['name']}'.",
            success=True,
        )
        self.refresh()
        self.player_changed.emit()

    # -- Helpers ------------------------------------------------------------

    def _group_dict(self, row: dict) -> dict:
        return {
            "id": row["group_id"],
            "name": row.get("group_name") or "",
            "code": row.get("group_code") or "",
            "visibility": row.get("visibility") or "public",
        }

    def _report_error(self, exc: DbError) -> None:
        self.set_status(f"Error: {exc}", success=False)
        QtWidgets.QMessageBox.warning(self, "Database error", str(exc))
