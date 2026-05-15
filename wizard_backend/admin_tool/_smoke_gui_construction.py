"""
_smoke_gui_construction.py - Instantiate every admin-tool view against a
tiny seeded SQLite DB so any wiring / construction error surfaces without
needing to drive the GUI event loop. Verifies the new Group -> tabbed
detail flow at runtime.
"""

from __future__ import annotations

import os
import sys
import tempfile

# QPA offscreen so this also runs in headless environments.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3  # noqa: E402

from PyQt6 import QtWidgets  # noqa: E402

from db_backend import LocalBackend  # noqa: E402

SCHEMA = """
CREATE TABLE players (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    UNIQUE NOT NULL COLLATE NOCASE
);
CREATE TABLE groups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    code       TEXT    UNIQUE NOT NULL,
    visibility TEXT    NOT NULL DEFAULT 'public'
);
CREATE TABLE games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_hash   TEXT    UNIQUE NOT NULL,
    game_mode   TEXT    NOT NULL,
    num_players INTEGER NOT NULL,
    played_at   TEXT    NOT NULL,
    group_id    INTEGER REFERENCES groups(id)
);
CREATE TABLE results (
    game_id      INTEGER NOT NULL REFERENCES games(id),
    player_id    INTEGER NOT NULL REFERENCES players(id),
    final_score  INTEGER NOT NULL,
    rank         INTEGER NOT NULL,
    correct_bids INTEGER NOT NULL,
    total_rounds INTEGER NOT NULL,
    PRIMARY KEY (game_id, player_id)
);
CREATE TABLE feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    message    TEXT    NOT NULL,
    upvotes    INTEGER NOT NULL DEFAULT 0,
    downvotes  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO groups (name, code) VALUES ('Group A', '0001'), ('Group B', '0002');
INSERT INTO players (name) VALUES ('Alice'), ('Bob'), ('Charlie');
INSERT INTO games (game_hash, game_mode, num_players, played_at, group_id)
VALUES ('h1', 'standard', 3, '2026-01-01T00:00:00', 1),
       ('h2', 'standard', 3, '2026-01-02T00:00:00', 1),
       ('h3', 'standard', 2, '2026-01-03T00:00:00', 2);
INSERT INTO results (game_id, player_id, final_score, rank, correct_bids, total_rounds)
VALUES (1, 1, 100, 1, 5, 10),
       (1, 2, 80,  2, 4, 10),
       (1, 3, 60,  3, 3, 10),
       (2, 1, 90,  2, 4, 10),
       (2, 2, 95,  1, 5, 10),
       (3, 1, 70,  2, 3, 10),
       (3, 3, 75,  1, 4, 10);
"""


def main() -> int:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        conn = sqlite3.connect(tmp.name)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

        backend = LocalBackend(tmp.name, label="smoke")
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        from main_window import MainWindow
        from group_players_view import GroupDetailView, GroupPlayersView
        from players_view import PlayersView
        from games_view import GamesView

        win = MainWindow(backend)
        # Sanity: the stack must hold the GroupDetailView at index 2.
        detail = win._stack.widget(2)
        assert isinstance(detail, GroupDetailView), type(detail)
        # Tab order: Games, Players
        assert isinstance(detail._games, GamesView)
        assert isinstance(detail._players, GroupPlayersView)
        assert detail._tabs.count() == 2
        assert "Games" in detail._tabs.tabText(0)
        assert "Players" in detail._tabs.tabText(1)

        # All-players view is at index 3 and lists per-(group, player) rows.
        ap = win._stack.widget(3)
        assert isinstance(ap, PlayersView)
        ap.refresh()
        # 5 result rows live in group A (Alice x2, Bob x2, Charlie x1),
        # 2 in group B (Alice, Charlie) -> 3 distinct players in A + 2 in B
        # = 5 (group, player) rows total.
        assert len(ap._all) == 5, ap._all

        # Open Group A's detail page programmatically and refresh both tabs.
        groups = backend.query("SELECT * FROM groups ORDER BY id")
        win._show_group_detail(groups[0])
        assert win._stack.currentIndex() == 2
        detail._players.refresh()
        # Group A has 3 distinct players in its results.
        assert len(detail._players._rows) == 3, detail._players._rows

        # Now flip to All players and confirm rename through the helper.
        win._switch(3)
        from player_ops import ensure_player, reassign_in_group

        alice = backend.query(
            "SELECT id FROM players WHERE name = 'Alice'"
        )[0]["id"]
        tgt = ensure_player(backend, "Alicia")
        reassign_in_group(backend, [(int(alice), int(tgt))], group_id=1)
        ap.refresh()
        rows = backend.query(
            "SELECT p.name, gr.name AS gname FROM players p "
            "JOIN results r ON r.player_id = p.id "
            "JOIN games g ON g.id = r.game_id "
            "JOIN groups gr ON gr.id = g.group_id "
            "ORDER BY gr.name, p.name"
        )
        names_by_group: dict[str, set[str]] = {}
        for row in rows:
            names_by_group.setdefault(row["gname"], set()).add(row["name"])
        assert "Alicia" in names_by_group["Group A"], names_by_group
        assert "Alice" in names_by_group["Group B"], names_by_group
        assert "Alice" not in names_by_group["Group A"], names_by_group

        print("GUI construction smoke OK.")
        return 0
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
