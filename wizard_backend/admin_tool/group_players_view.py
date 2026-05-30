"""
group_players_view.py - Per-group player leaderboard + group detail tabs.

Contains:
  - GroupPlayersView   Leaderboard table for one group, with rename / merge
                       buttons that act only on this group's results.
  - GroupDetailView    Thin wrapper that pairs GamesView and GroupPlayersView
                       under a QTabWidget. The Groups view opens this when a
                       group is selected.
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets

from db_backend import DbBackend, DbError
from dialogs import (
    GroupPlayerMergeDialog,
    GroupPlayerRenameDialog,
    PlayerEloHistoryDialog,
)
from elo_view import ensure_elo_schema
from games_view import GamesView
from player_ops import (
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


class GroupPlayersView(BaseView):
    """Leaderboard for a single group with per-group rename / merge."""

    back_to_groups = QtCore.pyqtSignal()
    player_changed = QtCore.pyqtSignal()

    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self._group: Optional[dict] = None
        self._rows: list[dict] = []
        self.set_title("Players", "Pick a group in the Groups view first.")

        btn_back = push_button("←  Back to groups", role="toolbar_btn")
        btn_back.clicked.connect(self.back_to_groups.emit)
        self.add_toolbar_widget(btn_back)

        btn_refresh = push_button("⟳", role="toolbar_btn", tooltip="Refresh")
        btn_refresh.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_refresh)

        self.add_toolbar_stretch()

        btn_history = push_button(
            "📈  ELO history",
            tooltip="Show how the selected player's ELO has changed over time.",
        )
        btn_history.clicked.connect(self._show_history)
        self.add_toolbar_widget(btn_history)

        btn_rename = push_button("✎  Rename player")
        btn_rename.clicked.connect(self._rename)
        self.add_toolbar_widget(btn_rename)

        btn_merge = push_button("⇋  Merge players", role="primary")
        btn_merge.clicked.connect(self._merge)
        self.add_toolbar_widget(btn_merge)

        self._table = make_table(
            ["Player ID", "Name", "ELO (Std)", "ELO (Mult)",
             "Games", "Wins", "Avg score"]
        )
        # Double-clicking a row is a fast path to the ELO history dialog.
        self._table.itemDoubleClicked.connect(lambda _it: self._show_history())
        self.add_to_body(self._table, stretch=1)

    # -- Public API ---------------------------------------------------------

    def set_group(self, group: Optional[dict]) -> None:
        self._group = group
        if group:
            self.set_title(
                f"Players in: {group['name']}",
                f"Code {group['code']}  ·  Visibility: {group['visibility']}",
            )
        else:
            self.set_title("Players", "No group selected.")
        self.refresh()

    def refresh(self) -> None:
        if not self._group:
            self._rows = []
            fill_table(self._table, [], self._columns())
            return
        # Make sure the ELO tables exist before the LEFT JOIN tries to read
        # them — for DBs that pre-date the ELO release.
        self.safe(ensure_elo_schema, self.backend)
        rows = self.safe(fetch_players_in_group, self.backend, self._group["id"])
        if rows is None:
            return
        self._rows = rows
        fill_table(self._table, rows, self._columns())
        self.set_status(f"{len(rows)} player(s) in this group.", success=True)

    # -- Internals ----------------------------------------------------------

    def _columns(self) -> list[tuple[str, str]]:
        return [
            ("id", "Player ID"),
            ("name", "Name"),
            ("elo_standard", "ELO (Std)"),
            ("elo_multiplicative", "ELO (Mult)"),
            ("games", "Games"),
            ("wins", "Wins"),
            ("avg_score", "Avg score"),
        ]

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
        for r in self._rows:
            if r["id"] == pid:
                return r
        return None

    # -- Actions ------------------------------------------------------------

    def _rename(self) -> None:
        if not self._group:
            self.set_status("Please pick a group first.", success=False)
            return
        if not self._rows:
            self.set_status(
                "No players have results in this group.", success=False
            )
            return
        preselect = None
        sel = self._selected()
        if sel:
            preselect = sel["id"]
        dlg = GroupPlayerRenameDialog(
            self,
            group=self._group,
            players_in_group=self._rows,
            preselect_id=preselect,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        src_id = dlg.player_id
        new_name = dlg.new_name
        if src_id is None or not new_name:
            return
        gid = int(self._group["id"])
        try:
            tgt = ensure_player(self.backend, new_name)
            reassign_in_group(
                self.backend, [(int(src_id), tgt)], group_id=gid
            )
        except DbError as exc:
            self._report_error(exc)
            return
        self.set_status(
            f"Player #{src_id} renamed to '{new_name}' in this group.",
            success=True,
        )
        self.refresh()
        self.player_changed.emit()

    def _merge(self) -> None:
        if not self._group:
            self.set_status("Please pick a group first.", success=False)
            return
        if len(self._rows) < 2:
            self.set_status(
                "Need at least two players in this group to merge.",
                success=False,
            )
            return
        preselect = None
        sel = self._selected()
        if sel:
            preselect = sel["id"]
        dlg = GroupPlayerMergeDialog(
            self,
            group=self._group,
            players_in_group=self._rows,
            preselect_a_id=preselect,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        a_id = dlg.player_a_id
        b_id = dlg.player_b_id
        new_name = dlg.new_name
        if a_id is None or b_id is None or a_id == b_id or not new_name:
            return
        gid = int(self._group["id"])
        try:
            tgt = ensure_player(self.backend, new_name)
            reassign_in_group(
                self.backend,
                [(int(a_id), tgt), (int(b_id), tgt)],
                group_id=gid,
            )
        except DbError as exc:
            self._report_error(exc)
            return
        self.set_status(
            f"Players #{a_id} and #{b_id} merged into '{new_name}' "
            "in this group.",
            success=True,
        )
        self.refresh()
        self.player_changed.emit()

    def _show_history(self) -> None:
        """Open the ELO-history dialog for the currently selected player."""
        if not self._group:
            self.set_status("Please pick a group first.", success=False)
            return
        sel = self._selected()
        if not sel:
            self.set_status("Select a player first.", success=False)
            return
        dlg = PlayerEloHistoryDialog(
            self, backend=self.backend, player=sel, group=self._group
        )
        dlg.exec()

    def _report_error(self, exc: DbError) -> None:
        self.set_status(f"Error: {exc}", success=False)
        QtWidgets.QMessageBox.warning(self, "Database error", str(exc))


# ---------------------------------------------------------------------------
# GroupDetailView - tabs for one selected group
# ---------------------------------------------------------------------------


class GroupDetailView(QtWidgets.QWidget):
    """A thin QTabWidget that ties Games and Players for one group."""

    back_to_groups = QtCore.pyqtSignal()
    player_changed = QtCore.pyqtSignal()

    def __init__(self, backend: DbBackend) -> None:
        super().__init__()
        self.backend = backend
        self._group: Optional[dict] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QtWidgets.QTabWidget()
        self._games = GamesView(backend)
        self._players = GroupPlayersView(backend)
        self._tabs.addTab(self._games, "🎮  Games")
        self._tabs.addTab(self._players, "🧑  Players")
        layout.addWidget(self._tabs)

        # Forward signals from the inner views.
        self._games.back_to_groups.connect(self.back_to_groups.emit)
        self._players.back_to_groups.connect(self.back_to_groups.emit)
        self._games.player_changed.connect(self._on_player_changed)
        self._players.player_changed.connect(self._on_player_changed)
        self._tabs.currentChanged.connect(self._on_tab_changed)

    # -- Public API ---------------------------------------------------------

    def set_group(self, group: Optional[dict]) -> None:
        self._group = group
        self._games.set_group(group)
        self._players.set_group(group)

    def refresh(self) -> None:
        """Refresh whatever tab is currently visible."""
        current = self._tabs.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()

    # -- Internals ----------------------------------------------------------

    def _on_player_changed(self) -> None:
        # Renames/merges change rows that both tabs care about.
        self._games.refresh()
        self._players.refresh()
        self.player_changed.emit()

    def _on_tab_changed(self, _idx: int) -> None:
        current = self._tabs.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()
