"""
games_view.py - Games of a single group with full CRUD support and an
inline editor for per-player results.

Layout:
    Splitter
      |-- Table of games in the group (left)
      +-- Detail panel (right) with player results
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore, QtWidgets

from db_backend import DbBackend
from dialogs import (
    DangerConfirmDialog,
    GameEditDialog,
    ResultEditDialog,
)
from elo_view import ensure_elo_schema
from player_ops import ensure_player as _ensure_player_global
from style import ACCENT, TEXT_DIM
from views_base import BaseView, fill_table, make_table, push_button, selected_row_index


class GamesView(BaseView):
    back_to_groups = QtCore.pyqtSignal()
    player_changed = QtCore.pyqtSignal()  # emitted whenever results change

    def __init__(self, backend: DbBackend) -> None:
        super().__init__(backend)
        self._group: Optional[dict] = None
        self._games: list[dict] = []
        self._players_cache: list[dict] = []
        self._groups_cache: list[dict] = []
        self.set_title("Games", "Pick a group in the Groups view first.")

        # Toolbar
        btn_back = push_button("←  Back to groups", role="toolbar_btn")
        btn_back.clicked.connect(self.back_to_groups.emit)
        self.add_toolbar_widget(btn_back)

        btn_refresh = push_button("⟳", role="toolbar_btn", tooltip="Refresh")
        btn_refresh.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_refresh)

        self.add_toolbar_stretch()

        btn_add = push_button("＋  New game")
        btn_add.clicked.connect(self._add_game)
        self.add_toolbar_widget(btn_add)

        btn_edit = push_button("✎  Edit game")
        btn_edit.clicked.connect(self._edit_game)
        self.add_toolbar_widget(btn_edit)

        btn_move = push_button("↪  Move")
        btn_move.clicked.connect(self._move_game)
        self.add_toolbar_widget(btn_move)

        btn_del = push_button("🗑  Delete", role="danger")
        btn_del.clicked.connect(self._delete_game)
        self.add_toolbar_widget(btn_del)

        # Splitter: games list (left), results (right)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)

        self._games_table = make_table(
            ["ID", "Hash", "Mode", "#P", "Played at", "Results"]
        )
        self._games_table.itemSelectionChanged.connect(self._on_game_selected)
        splitter.addWidget(self._games_table)

        right = QtWidgets.QWidget()
        rl = QtWidgets.QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.setSpacing(8)

        results_header_row = QtWidgets.QHBoxLayout()
        self._results_header = QtWidgets.QLabel("Results")
        self._results_header.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {ACCENT};"
        )
        results_header_row.addWidget(self._results_header)
        results_header_row.addStretch()

        self._btn_add_result = push_button("＋ Result", role="toolbar_btn")
        self._btn_add_result.clicked.connect(self._add_result)
        results_header_row.addWidget(self._btn_add_result)

        self._btn_edit_result = push_button("✎", role="toolbar_btn", tooltip="Edit")
        self._btn_edit_result.clicked.connect(self._edit_result)
        results_header_row.addWidget(self._btn_edit_result)

        self._btn_del_result = push_button("🗑", role="toolbar_btn", tooltip="Delete")
        self._btn_del_result.clicked.connect(self._delete_result)
        results_header_row.addWidget(self._btn_del_result)

        rl.addLayout(results_header_row)

        self._results_table = make_table(
            ["player_id", "Player", "Score", "Rank",
             "Correct", "Rounds", "ELO Δ"]
        )
        rl.addWidget(self._results_table, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.add_to_body(splitter, stretch=1)

    # -- Public API ---------------------------------------------------------

    def set_group(self, group: Optional[dict]) -> None:
        self._group = group
        if group:
            self.set_title(
                f"Games in: {group['name']}",
                f"Code {group['code']}  ·  Visibility: {group['visibility']}",
            )
        else:
            self.set_title("Games", "No group selected.")
        self.refresh()

    def refresh(self) -> None:
        if not self._group:
            self._games = []
            fill_table(self._games_table, [], self._game_columns())
            self._render_results([])
            return
        # Make sure the ELO tables exist before the results panel LEFT JOINs
        # them — for DBs that pre-date the ELO release.
        self.safe(ensure_elo_schema, self.backend)
        self._players_cache = self.safe(self._fetch_players) or []
        self._groups_cache = self.safe(self._fetch_groups) or []
        rows = self.safe(self._fetch_games_for_group, self._group["id"])
        if rows is None:
            return
        self._games = rows
        fill_table(self._games_table, rows, self._game_columns())
        self._render_results([])
        self.set_status(f"{len(rows)} game(s) loaded.", success=True)

    # -- Queries ------------------------------------------------------------

    def _game_columns(self) -> list[tuple[str, str]]:
        return [
            ("id", "ID"),
            ("game_hash", "Hash"),
            ("game_mode", "Mode"),
            ("num_players", "#P"),
            ("played_at", "Played at"),
            ("result_count", "Results"),
        ]

    def _fetch_games_for_group(self, group_id: int) -> list[dict]:
        return self.backend.query(
            """
            SELECT g.id, g.game_hash, g.game_mode, g.num_players,
                   g.played_at, g.group_id,
                   COUNT(r.player_id) AS result_count
              FROM games g
         LEFT JOIN results r ON r.game_id = g.id
             WHERE g.group_id = ?
          GROUP BY g.id
          ORDER BY g.played_at DESC
            """,
            (group_id,),
        )

    def _fetch_results_for_game(self, game_id: int) -> list[dict]:
        return self.backend.query(
            """
            SELECT r.player_id, p.name,
                   r.final_score, r.rank,
                   r.correct_bids, r.total_rounds,
                   r.game_id,
                   d.delta AS elo_delta
              FROM results r
              JOIN players p ON p.id = r.player_id
         LEFT JOIN game_elo_deltas d
                ON d.game_id   = r.game_id
               AND d.player_id = r.player_id
             WHERE r.game_id = ?
          ORDER BY r.rank, r.final_score DESC
            """,
            (game_id,),
        )

    def _fetch_players(self) -> list[dict]:
        return self.backend.query(
            "SELECT id, name FROM players ORDER BY name COLLATE NOCASE"
        )

    def _fetch_groups(self) -> list[dict]:
        return self.backend.query(
            "SELECT id, name, code FROM groups ORDER BY name COLLATE NOCASE"
        )

    # -- Selection handlers -------------------------------------------------

    def _selected_game(self) -> Optional[dict]:
        idx = selected_row_index(self._games_table)
        if idx is None:
            return None
        item = self._games_table.item(idx, 0)
        if item is None:
            return None
        try:
            gid = int(item.text())
        except ValueError:
            return None
        for g in self._games:
            if g["id"] == gid:
                return g
        return None

    def _on_game_selected(self) -> None:
        game = self._selected_game()
        if not game:
            self._render_results([])
            return
        rows = self.safe(self._fetch_results_for_game, game["id"])
        self._render_results(rows or [])

    def _render_results(self, rows: list[dict]) -> None:
        # Pre-format the ELO delta with an explicit sign ("+12" / "−8") and
        # an em-dash for games that have no rating yet. ``fill_table`` keeps
        # this as a text column so the sign is preserved.
        decorated: list[dict] = []
        for r in rows:
            row = dict(r)
            d = row.get("elo_delta")
            if d is None:
                row["elo_delta_display"] = "—"
            else:
                rounded = round(float(d))
                row["elo_delta_display"] = (
                    f"+{rounded}" if rounded >= 0 else f"−{abs(rounded)}"
                )
            decorated.append(row)
        fill_table(
            self._results_table,
            decorated,
            [
                ("player_id", "Player ID"),
                ("name", "Player"),
                ("final_score", "Score"),
                ("rank", "Rank"),
                ("correct_bids", "Correct"),
                ("total_rounds", "Rounds"),
                ("elo_delta_display", "ELO Δ"),
            ],
        )

    def _selected_result(self) -> Optional[dict]:
        idx = selected_row_index(self._results_table)
        if idx is None:
            return None
        pid_item = self._results_table.item(idx, 0)
        name_item = self._results_table.item(idx, 1)
        if pid_item is None or name_item is None:
            return None
        try:
            pid = int(pid_item.text())
        except ValueError:
            return None
        return {
            "player_id": pid,
            "name": name_item.text(),
            "final_score": int(self._results_table.item(idx, 2).text() or 0),
            "rank": int(self._results_table.item(idx, 3).text() or 1),
            "correct_bids": int(self._results_table.item(idx, 4).text() or 0),
            "total_rounds": int(self._results_table.item(idx, 5).text() or 0),
        }

    # -- Game actions -------------------------------------------------------

    def _add_game(self) -> None:
        if not self._group:
            self.set_status("Please pick a group first.", success=False)
            return
        prefilled = {"group_id": self._group["id"], "played_at": _now()}
        dlg = GameEditDialog(self, game=prefilled, groups=self._groups_cache)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        v = dlg.values
        ok = self.safe(
            self.backend.execute,
            "INSERT INTO games (game_hash, game_mode, num_players, played_at, group_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                v["game_hash"],
                v["game_mode"],
                v["num_players"],
                v["played_at"],
                v["group_id"],
            ),
        )
        if ok is None:
            return
        self.set_status(
            f"Game created (hash {v['game_hash'][:12]}...).", success=True
        )
        self.refresh()

    def _edit_game(self) -> None:
        game = self._selected_game()
        if not game:
            self.set_status("No game selected.", success=False)
            return
        dlg = GameEditDialog(self, game=game, groups=self._groups_cache)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        v = dlg.values
        ok = self.safe(
            self.backend.execute,
            "UPDATE games SET game_mode = ?, num_players = ?, played_at = ?, group_id = ? "
            "WHERE id = ?",
            (
                v["game_mode"],
                v["num_players"],
                v["played_at"],
                v["group_id"],
                game["id"],
            ),
        )
        if ok is None:
            return
        self.set_status(f"Game #{game['id']} updated.", success=True)
        self.refresh()

    def _move_game(self) -> None:
        game = self._selected_game()
        if not game:
            self.set_status("No game selected.", success=False)
            return
        labels = ["(no group)"] + [
            f"{g['name']} ({g['code']})" for g in self._groups_cache
        ]
        ids: list[Optional[int]] = [None] + [g["id"] for g in self._groups_cache]
        cur = 0
        for i, gid in enumerate(ids):
            if gid == game.get("group_id"):
                cur = i
                break
        sel, ok = QtWidgets.QInputDialog.getItem(
            self,
            "Move game",
            "New group:",
            labels,
            cur,
            False,
        )
        if not ok:
            return
        new_gid = ids[labels.index(sel)]
        res = self.safe(
            self.backend.execute,
            "UPDATE games SET group_id = ? WHERE id = ?",
            (new_gid, game["id"]),
        )
        if res is None:
            return
        self.set_status(f"Game #{game['id']} moved.", success=True)
        self.refresh()

    def _delete_game(self) -> None:
        game = self._selected_game()
        if not game:
            self.set_status("No game selected.", success=False)
            return
        detail = (
            f"Game ID:     {game['id']}\n"
            f"Hash:        {game['game_hash']}\n"
            f"Mode:        {game['game_mode']}\n"
            f"Players:     {game['num_players']}\n"
            f"Played at:   {game['played_at']}\n"
            f"Results:     {game.get('result_count', 0)}\n\n"
            "All player results for this game will be deleted as well."
        )
        dlg = DangerConfirmDialog(
            self,
            title="Delete game?",
            message=(
                f"Permanently delete game <b>#{game['id']}</b> "
                f"({game['game_hash'][:12]}...)?"
            ),
            confirm_phrase=str(game["id"]),
            detail=detail,
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        gid = int(game["id"])
        sql = (
            f"DELETE FROM results WHERE game_id = {gid};\n"
            f"DELETE FROM games WHERE id = {gid};"
        )
        res = self.safe(self.backend.executescript, sql)
        if res is None:
            return
        self.set_status(f"Game #{gid} deleted.", success=True)
        self.refresh()

    # -- Result actions -----------------------------------------------------

    def _add_result(self) -> None:
        game = self._selected_game()
        if not game:
            self.set_status("No game selected.", success=False)
            return
        dlg = ResultEditDialog(self, players=self._players_cache, lock_player=False)
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        v = dlg.values
        # Resolve player id (creating a new one if needed).
        pid = v.get("player_id")
        if pid is None and v.get("new_player_name"):
            pid = self._ensure_player(v["new_player_name"])
            if pid is None:
                return
        if pid is None:
            self.set_status("Invalid player.", success=False)
            return
        # Duplicate (game_id, player_id) is rejected by the primary key.
        ok = self.safe(
            self.backend.execute,
            "INSERT INTO results "
            "(game_id, player_id, final_score, rank, correct_bids, total_rounds) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                game["id"],
                pid,
                v["final_score"],
                v["rank"],
                v["correct_bids"],
                v["total_rounds"],
            ),
        )
        if ok is None:
            return
        self.set_status("Result added.", success=True)
        self._on_game_selected()
        self.player_changed.emit()

    def _edit_result(self) -> None:
        game = self._selected_game()
        if not game:
            self.set_status("No game selected.", success=False)
            return
        result = self._selected_result()
        if not result:
            self.set_status("No result selected.", success=False)
            return
        dlg = ResultEditDialog(
            self, result=result, players=self._players_cache, lock_player=True
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        v = dlg.values
        ok = self.safe(
            self.backend.execute,
            "UPDATE results SET final_score = ?, rank = ?, "
            "correct_bids = ?, total_rounds = ? "
            "WHERE game_id = ? AND player_id = ?",
            (
                v["final_score"],
                v["rank"],
                v["correct_bids"],
                v["total_rounds"],
                game["id"],
                result["player_id"],
            ),
        )
        if ok is None:
            return
        self.set_status("Result updated.", success=True)
        self._on_game_selected()
        self.player_changed.emit()

    def _delete_result(self) -> None:
        game = self._selected_game()
        if not game:
            return
        result = self._selected_result()
        if not result:
            self.set_status("No result selected.", success=False)
            return
        dlg = DangerConfirmDialog(
            self,
            title="Delete result?",
            message=(
                f"Delete the result of <b>{result['name']}</b> in game "
                f"#{game['id']}?"
            ),
            confirm_phrase=result["name"],
        )
        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        ok = self.safe(
            self.backend.execute,
            "DELETE FROM results WHERE game_id = ? AND player_id = ?",
            (game["id"], result["player_id"]),
        )
        if ok is None:
            return
        self.set_status("Result deleted.", success=True)
        self._on_game_selected()
        self.player_changed.emit()

    # -- Helpers ------------------------------------------------------------

    def _ensure_player(self, name: str) -> Optional[int]:
        return self.safe(_ensure_player_global, self.backend, name)


def _now() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")
