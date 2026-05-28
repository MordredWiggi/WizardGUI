"""
elo_view.py - ELO configuration & recompute tab for the Admin Tool.

What it does:
  * Edit every parameter of the ELO formula (stored in the ``elo_config`` row).
  * "Save configuration" writes the parameters. Per the project rules this is
    forward-looking only — existing ratings are NOT touched, future games just
    use the new formula.
  * "Recompute ALL ratings from scratch" replays every game of every group in
    chronological order. Used for the first introduction of ELO (or a reset).

The maths is the shared, dependency-free ``elo`` module (one level up). The
recompute runs locally here and writes the result back as a single batched SQL
script via ``backend.executescript`` — so it works for both the local SQLite
file and the remote (SSH + sqlite3) production database, without needing any
new HTTP endpoint on the server.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PyQt6 import QtWidgets

from db_backend import _sql_quote
from style import TEXT_DIM, TEXT_MAIN
from views_base import BaseView, fill_table, make_table, push_button

# The ELO engine lives in the backend package (parent directory). Make it
# importable from the admin_tool subfolder.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import elo  # noqa: E402  (import after sys.path tweak, by design)


# (key, decimals, step, minimum, maximum) for each editable parameter.
_SPECS: list[tuple[str, int, float, float, float]] = [
    ("start_elo", 1, 50.0, 0.0, 100000.0),
    ("floor", 1, 10.0, 0.0, 100000.0),
    ("k_base", 2, 5.0, 0.0, 100000.0),
    ("d", 1, 25.0, 1.0, 100000.0),
    ("gamma", 3, 0.05, 0.0, 3.0),
    ("w_hit", 2, 1.0, 0.0, 100000.0),
    ("a_hit", 2, 0.1, 0.0, 10.0),
    ("ref_n", 1, 1.0, 1.0, 100.0),
    ("w_ppr", 2, 1.0, 0.0, 100000.0),
    ("ppr_scale", 2, 1.0, 0.1, 100000.0),
    ("w_streak", 2, 1.0, 0.0, 100000.0),
    ("streak_cap", 1, 1.0, 0.0, 1000.0),
    ("provisional_games", 0, 1.0, 0.0, 100000.0),  # rendered as an int spinbox
    ("provisional_mult", 2, 0.1, 0.0, 100.0),
]

_DESCRIPTIONS: dict[str, str] = dict(elo.CONFIG_FIELDS)


class EloView(BaseView):
    def __init__(self, backend) -> None:
        super().__init__(backend)
        self.set_title(
            "ELO", "Tune the rating formula and recompute ratings."
        )
        self._editors: dict[str, QtWidgets.QAbstractSpinBox] = {}

        btn_reload = push_button("⟳  Reload", role="toolbar_btn")
        btn_reload.clicked.connect(self.refresh)
        self.add_toolbar_widget(btn_reload)

        btn_defaults = push_button("Reset to defaults", role="toolbar_btn")
        btn_defaults.clicked.connect(self._fill_defaults)
        self.add_toolbar_widget(btn_defaults)
        self.add_toolbar_stretch()

        # ── Parameter form (scrollable) ──────────────────────────────────
        form_host = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(form_host)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(2, 1)

        for row, (key, decimals, step, lo, hi) in enumerate(_SPECS):
            name = QtWidgets.QLabel(key)
            name.setStyleSheet(
                f"color: {TEXT_MAIN}; font-weight: 600; font-family: Consolas, monospace;"
            )
            if key == "provisional_games":
                editor: QtWidgets.QAbstractSpinBox = QtWidgets.QSpinBox()
                editor.setRange(int(lo), int(hi))
                editor.setSingleStep(int(step))
            else:
                editor = QtWidgets.QDoubleSpinBox()
                editor.setDecimals(decimals)
                editor.setRange(lo, hi)
                editor.setSingleStep(step)
            editor.setMinimumWidth(130)
            desc = QtWidgets.QLabel(_DESCRIPTIONS.get(key, ""))
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")

            grid.addWidget(name, row, 0)
            grid.addWidget(editor, row, 1)
            grid.addWidget(desc, row, 2)
            self._editors[key] = editor

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(form_host)
        scroll.setMaximumHeight(360)
        self.add_to_body(scroll)

        # ── Action buttons ───────────────────────────────────────────────
        btn_row = QtWidgets.QHBoxLayout()
        self._btn_save = push_button(
            "💾  Save configuration",
            role="primary",
            tooltip="Store the formula. Applies to FUTURE games only — "
            "existing ratings are not changed.",
        )
        self._btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(self._btn_save)

        self._btn_recompute = push_button(
            "♻  Recompute ALL ratings from scratch",
            role="danger",
            tooltip="Replay every game of every group with the saved formula. "
            "Use for the first introduction of ELO or a deliberate reset.",
        )
        self._btn_recompute.clicked.connect(self._on_recompute)
        btn_row.addWidget(self._btn_recompute)
        btn_row.addStretch()
        self.add_layout_to_body(btn_row)

        # ── Current ratings preview ──────────────────────────────────────
        hdr = QtWidgets.QLabel("Current ratings")
        hdr.setObjectName("section_header")
        self.add_to_body(hdr)

        self._table = make_table(
            ["Group", "Player", "Mode", "ELO", "Games", "Streak"]
        )
        self.add_to_body(self._table, stretch=1)

    # ── Data ─────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._ensure_schema()
        config = self._load_config()
        self._apply_config_to_form(config)
        self._fill_ratings_table()
        self.set_status("Loaded ELO configuration.", success=True)

    def _ensure_schema(self) -> None:
        """Create the ELO tables if the connected DB predates them."""
        self.safe(
            self.backend.executescript,
            """
            CREATE TABLE IF NOT EXISTS elo_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                params TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS player_ratings (
                player_id INTEGER NOT NULL, group_id INTEGER NOT NULL,
                game_mode TEXT NOT NULL, rating REAL NOT NULL,
                games INTEGER NOT NULL DEFAULT 0, streak INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (player_id, group_id, game_mode)
            );
            CREATE TABLE IF NOT EXISTS game_elo_deltas (
                game_id INTEGER NOT NULL, player_id INTEGER NOT NULL,
                rating_before REAL NOT NULL, rating_after REAL NOT NULL,
                delta REAL NOT NULL, PRIMARY KEY (game_id, player_id)
            );
            """,
        )

    def _load_config(self) -> dict:
        rows = self.safe(
            self.backend.query, "SELECT params FROM elo_config WHERE id = 1"
        )
        raw = None
        if rows:
            try:
                raw = json.loads(rows[0].get("params") or "{}")
            except (ValueError, TypeError):
                raw = None
        return elo.normalize_config(raw)

    def _apply_config_to_form(self, config: dict) -> None:
        for key, editor in self._editors.items():
            value = config.get(key, elo.DEFAULT_CONFIG.get(key, 0))
            if isinstance(editor, QtWidgets.QSpinBox):
                editor.setValue(int(value))
            else:
                editor.setValue(float(value))

    def _fill_defaults(self) -> None:
        self._apply_config_to_form(dict(elo.DEFAULT_CONFIG))
        self.set_status("Form filled with defaults (not yet saved).", success=True)

    def _read_form(self) -> dict:
        out: dict = {}
        for key, editor in self._editors.items():
            out[key] = editor.value()
        return elo.normalize_config(out)

    def _fill_ratings_table(self) -> None:
        rows = self.safe(
            self.backend.query,
            """
            SELECT gr.name AS group_name, p.name AS player_name,
                   pr.game_mode AS mode,
                   CAST(ROUND(pr.rating) AS INTEGER) AS elo,
                   pr.games AS games, pr.streak AS streak
            FROM player_ratings pr
            JOIN players p  ON p.id  = pr.player_id
            JOIN groups  gr ON gr.id = pr.group_id
            ORDER BY pr.rating DESC
            LIMIT 300
            """,
        )
        fill_table(
            self._table,
            rows or [],
            [
                ("group_name", "Group"),
                ("player_name", "Player"),
                ("mode", "Mode"),
                ("elo", "ELO"),
                ("games", "Games"),
                ("streak", "Streak"),
            ],
        )

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        self._ensure_schema()
        params = self._read_form()
        now = _now_iso()
        result = self.safe(
            self.backend.execute,
            "INSERT INTO elo_config (id, params, version, updated_at) "
            "VALUES (1, ?, 1, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "params = excluded.params, version = elo_config.version + 1, "
            "updated_at = excluded.updated_at",
            (json.dumps(params), now),
        )
        if result is not None:
            self.set_status(
                "Configuration saved. Applies to future games only.",
                success=True,
            )

    def _on_recompute(self) -> None:
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Recompute all ratings?",
            "This wipes every stored rating and replays ALL games of ALL "
            "groups with the SAVED formula.\n\nSave the configuration first if "
            "you changed it. Continue?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self._ensure_schema()
        config = self._load_config()

        rows = self.safe(
            self.backend.query,
            """
            SELECT g.id AS game_id, g.group_id AS group_id,
                   g.game_mode AS game_mode,
                   r.player_id AS player_id, r.rank AS rank,
                   r.correct_bids AS correct_bids, r.total_rounds AS total_rounds,
                   r.final_score AS final_score
            FROM games   g
            JOIN results r ON r.game_id = g.id
            WHERE g.group_id IS NOT NULL
            ORDER BY g.group_id, g.game_mode, g.played_at, g.id
            """,
        )
        if rows is None:
            return

        # Group rows into pools and per-pool ordered game lists.
        pools: dict[tuple[int, str], list[dict]] = {}
        for row in rows:
            key = (row["group_id"], row["game_mode"])
            pool = pools.setdefault(key, [])
            game = pool[-1] if pool and pool[-1]["game_id"] == row["game_id"] else None
            if game is None:
                game = {"game_id": row["game_id"], "players": []}
                pool.append(game)
            game["players"].append(
                {
                    "player_id": row["player_id"],
                    "rank": row["rank"],
                    "correct_bids": row["correct_bids"],
                    "total_rounds": row["total_rounds"],
                    "final_score": row["final_score"],
                }
            )

        now = _now_iso()
        rating_rows: list[tuple] = []
        delta_rows: list[tuple] = []
        for (group_id, game_mode), games in pools.items():
            ratings, deltas = elo.replay_pool(games, config)
            for player_id, state in ratings.items():
                rating_rows.append(
                    (
                        player_id,
                        group_id,
                        game_mode,
                        state["rating"],
                        state["games"],
                        state["streak"],
                        now,
                    )
                )
            for d in deltas:
                delta_rows.append(
                    (
                        d["game_id"],
                        d["player_id"],
                        d["rating_before"],
                        d["rating_after"],
                        d["delta"],
                    )
                )

        script = self._build_recompute_script(rating_rows, delta_rows)
        result = self.safe(self.backend.executescript, script)
        if result is None:
            return  # safe() already surfaced the error

        self._fill_ratings_table()
        self.set_status(
            f"Recomputed {len(pools)} pool(s): "
            f"{len(rating_rows)} ratings, {len(delta_rows)} game deltas.",
            success=True,
        )
        QtWidgets.QMessageBox.information(
            self,
            "Recompute complete",
            f"Processed {len(pools)} group/mode pool(s).\n"
            f"Wrote {len(rating_rows)} player ratings and "
            f"{len(delta_rows)} per-game deltas.",
        )

    # ── SQL script builder ─────────────────────────────────────────────────

    def _build_recompute_script(
        self, rating_rows: list[tuple], delta_rows: list[tuple]
    ) -> str:
        """Build a single SQL script that wipes and repopulates ELO tables.

        Values are inlined as escaped literals (the backend's executescript runs
        raw SQL). Multi-row INSERTs are chunked to keep each statement small.
        """
        parts: list[str] = [
            "DELETE FROM game_elo_deltas;",
            "DELETE FROM player_ratings;",
        ]

        def vals(row: tuple) -> str:
            return "(" + ",".join(_sql_quote(v) for v in row) + ")"

        parts += _chunked_inserts(
            "INSERT INTO player_ratings "
            "(player_id, group_id, game_mode, rating, games, streak, updated_at) VALUES",
            rating_rows,
            vals,
        )
        parts += _chunked_inserts(
            "INSERT INTO game_elo_deltas "
            "(game_id, player_id, rating_before, rating_after, delta) VALUES",
            delta_rows,
            vals,
        )
        return "\n".join(parts)


# ── Module helpers ──────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _chunked_inserts(prefix: str, rows: list[tuple], vals, chunk: int = 200) -> list[str]:
    statements: list[str] = []
    for i in range(0, len(rows), chunk):
        batch = rows[i : i + chunk]
        statements.append(prefix + " " + ",".join(vals(r) for r in batch) + ";")
    return statements
