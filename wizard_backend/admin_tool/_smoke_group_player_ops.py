"""
_smoke_group_player_ops.py - Self-contained smoke test for the per-group
rename / merge / delete SQL. Uses ``player_ops.build_group_reassign_sql``
directly (the same string that the GUI executes) and verifies expected
end-states against an in-memory SQLite database matching the production
schema.

Run with:  python _smoke_group_player_ops.py
Exits with non-zero status on failure.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from typing import Iterable

# Make the player_ops module importable when this script is invoked from
# anywhere (it lives in the same folder).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from player_ops import build_group_reassign_sql  # noqa: E402


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
"""


def fresh_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def add_group(conn: sqlite3.Connection, name: str, code: str) -> int:
    return conn.execute(
        "INSERT INTO groups (name, code) VALUES (?, ?)", (name, code)
    ).lastrowid


def add_player(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute(
        "INSERT INTO players (name) VALUES (?)", (name,)
    ).lastrowid


def add_game(conn: sqlite3.Connection, group_id: int, ghash: str) -> int:
    return conn.execute(
        "INSERT INTO games (game_hash, game_mode, num_players, played_at, "
        "group_id) VALUES (?, 'standard', 4, '2026-01-01T00:00:00', ?)",
        (ghash, group_id),
    ).lastrowid


def add_result(
    conn: sqlite3.Connection,
    game_id: int,
    player_id: int,
    score: int = 0,
    rank: int = 1,
) -> None:
    conn.execute(
        "INSERT INTO results (game_id, player_id, final_score, rank, "
        "correct_bids, total_rounds) VALUES (?, ?, ?, ?, 0, 10)",
        (game_id, player_id, score, rank),
    )


def ensure_player(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM players WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row:
        return int(row[0])
    return int(add_player(conn, name))


def run_reassign(
    conn: sqlite3.Connection,
    moves: Iterable[tuple[int, int]],
    group_id: int,
) -> None:
    sql = build_group_reassign_sql(moves, group_id)
    if not sql:
        return
    conn.executescript(sql)


def run_delete_in_group(
    conn: sqlite3.Connection, *, player_id: int, group_id: int
) -> None:
    """Mirrors player_ops.delete_player_in_group."""
    sql = (
        f"DELETE FROM results "
        f" WHERE player_id = {player_id} "
        f"   AND game_id IN ("
        f"        SELECT id FROM games WHERE group_id = {group_id}"
        f"       );\n"
        f"DELETE FROM players WHERE id = {player_id} "
        f" AND NOT EXISTS ("
        f"   SELECT 1 FROM results WHERE player_id = {player_id}"
        f" );"
    )
    conn.executescript(sql)


# -- assertion helpers -------------------------------------------------------


def player_id(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM players WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    return int(row[0]) if row else None


def results_for_player_in_group(
    conn: sqlite3.Connection, pid: int, group_id: int
) -> list[tuple]:
    return conn.execute(
        "SELECT r.game_id, r.final_score FROM results r "
        "JOIN games g ON g.id = r.game_id "
        "WHERE r.player_id = ? AND g.group_id = ? ORDER BY r.game_id",
        (pid, group_id),
    ).fetchall()


def total_results_for_player(conn: sqlite3.Connection, pid: int) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM results WHERE player_id = ?", (pid,)
        ).fetchone()[0]
    )


def assert_eq(label: str, got, want) -> None:
    if got != want:
        raise AssertionError(f"{label}: got {got!r}, want {want!r}")
    print(f"  OK  {label}")


# -- scenarios ---------------------------------------------------------------


def scenario_rename_simple():
    """Rename Alice -> Alicia when Alice only plays in this group."""
    print("\n[1] Rename: Alice -> Alicia (Alice has no results elsewhere)")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    game1 = add_game(conn, g1, "h1")
    game2 = add_game(conn, g1, "h2")
    add_result(conn, game1, alice, score=10)
    add_result(conn, game2, alice, score=20)
    tgt = ensure_player(conn, "Alicia")
    run_reassign(conn, [(alice, tgt)], group_id=g1)

    assert_eq("Alice deleted (orphaned)", player_id(conn, "Alice"), None)
    new_id = player_id(conn, "Alicia")
    assert new_id is not None
    assert_eq(
        "Alicia has both rows in g1",
        results_for_player_in_group(conn, new_id, g1),
        [(game1, 10), (game2, 20)],
    )
    conn.close()


def scenario_rename_keep_other_group():
    """Rename in g1 only; the player's g2 rows must stay under Alice."""
    print("\n[2] Rename in g1: Alice's g2 rows remain under Alice")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    g2 = add_group(conn, "G2", "0002")
    alice = add_player(conn, "Alice")
    game1 = add_game(conn, g1, "h1")
    game2 = add_game(conn, g2, "h2")
    add_result(conn, game1, alice, score=10)
    add_result(conn, game2, alice, score=20)
    tgt = ensure_player(conn, "Alicia")
    run_reassign(conn, [(alice, tgt)], group_id=g1)

    assert_eq(
        "Alice still exists (still in g2)", player_id(conn, "Alice"), alice
    )
    assert_eq(
        "Alice still has 1 result globally",
        total_results_for_player(conn, alice),
        1,
    )
    new_id = player_id(conn, "Alicia")
    assert new_id is not None
    assert_eq(
        "Alicia has Alice's g1 row only",
        results_for_player_in_group(conn, new_id, g1),
        [(game1, 10)],
    )
    assert_eq(
        "Alicia has nothing in g2",
        results_for_player_in_group(conn, new_id, g2),
        [],
    )
    conn.close()


def scenario_rename_collision_with_existing_name():
    """Rename Alice -> 'Bob' when Bob already exists and plays the same game."""
    print("\n[3] Rename Alice -> Bob with same-game conflict (Bob wins)")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    bob = add_player(conn, "Bob")
    game1 = add_game(conn, g1, "h1")
    game2 = add_game(conn, g1, "h2")
    add_result(conn, game1, alice, score=10)
    add_result(conn, game1, bob, score=99)
    add_result(conn, game2, alice, score=20)
    tgt = ensure_player(conn, "Bob")
    assert tgt == bob
    run_reassign(conn, [(alice, tgt)], group_id=g1)

    assert_eq("Alice deleted (orphaned)", player_id(conn, "Alice"), None)
    assert_eq(
        "Bob keeps his game1 row (target wins) AND inherits game2",
        results_for_player_in_group(conn, bob, g1),
        [(game1, 99), (game2, 20)],
    )
    conn.close()


def scenario_merge_simple():
    """Merge Alice & Bob -> Charlie (both only in this group)."""
    print("\n[4] Merge Alice + Bob -> Charlie (both orphaned, Charlie new)")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    bob = add_player(conn, "Bob")
    g_a = add_game(conn, g1, "ha")
    g_b = add_game(conn, g1, "hb")
    add_result(conn, g_a, alice, score=10)
    add_result(conn, g_b, bob, score=20)
    tgt = ensure_player(conn, "Charlie")
    run_reassign(conn, [(alice, tgt), (bob, tgt)], group_id=g1)

    assert_eq("Alice deleted", player_id(conn, "Alice"), None)
    assert_eq("Bob deleted", player_id(conn, "Bob"), None)
    new_id = player_id(conn, "Charlie")
    assert new_id is not None
    assert_eq(
        "Charlie has both rows",
        results_for_player_in_group(conn, new_id, g1),
        [(g_a, 10), (g_b, 20)],
    )
    conn.close()


def scenario_merge_target_equals_a():
    """Merge Alice + Bob into 'Alice' (target == A)."""
    print("\n[5] Merge with target name == Alice's name")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    bob = add_player(conn, "Bob")
    g_a = add_game(conn, g1, "ha")
    g_b = add_game(conn, g1, "hb")
    add_result(conn, g_a, alice, score=10)
    add_result(conn, g_b, bob, score=20)
    tgt = ensure_player(conn, "Alice")
    assert tgt == alice
    run_reassign(conn, [(alice, tgt), (bob, tgt)], group_id=g1)

    assert_eq("Bob deleted", player_id(conn, "Bob"), None)
    assert_eq("Alice still exists", player_id(conn, "Alice"), alice)
    assert_eq(
        "Alice has both rows",
        results_for_player_in_group(conn, alice, g1),
        [(g_a, 10), (g_b, 20)],
    )
    conn.close()


def scenario_merge_same_game_conflict():
    """Alice and Bob in the same game. Merge should keep A's row (A first)."""
    print("\n[6] Merge with same-game conflict (Alice processed first wins)")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    bob = add_player(conn, "Bob")
    g_a = add_game(conn, g1, "ha")
    add_result(conn, g_a, alice, score=10)
    add_result(conn, g_a, bob, score=99)
    tgt = ensure_player(conn, "Charlie")
    run_reassign(conn, [(alice, tgt), (bob, tgt)], group_id=g1)

    assert_eq("Alice deleted", player_id(conn, "Alice"), None)
    assert_eq("Bob deleted", player_id(conn, "Bob"), None)
    new_id = player_id(conn, "Charlie")
    assert new_id is not None
    assert_eq(
        "Charlie has exactly one row for the conflicted game (Alice's data)",
        results_for_player_in_group(conn, new_id, g1),
        [(g_a, 10)],
    )
    conn.close()


def scenario_merge_keeps_other_group():
    """Alice is in g1 and g2; Bob only in g1. Merge in g1 to Charlie.
    Alice's g2 row must remain on Alice; Bob deleted; Charlie has merged g1."""
    print("\n[7] Merge in g1 preserves Alice's g2 row under Alice")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    g2 = add_group(conn, "G2", "0002")
    alice = add_player(conn, "Alice")
    bob = add_player(conn, "Bob")
    g1a = add_game(conn, g1, "h1a")
    g1b = add_game(conn, g1, "h1b")
    g2a = add_game(conn, g2, "h2a")
    add_result(conn, g1a, alice, score=10)
    add_result(conn, g1b, bob, score=20)
    add_result(conn, g2a, alice, score=77)
    tgt = ensure_player(conn, "Charlie")
    run_reassign(conn, [(alice, tgt), (bob, tgt)], group_id=g1)

    assert_eq(
        "Alice still exists (still in g2)", player_id(conn, "Alice"), alice
    )
    assert_eq("Bob deleted", player_id(conn, "Bob"), None)
    assert_eq(
        "Alice keeps her g2 row only",
        results_for_player_in_group(conn, alice, g2),
        [(g2a, 77)],
    )
    assert_eq(
        "Alice has nothing left in g1",
        results_for_player_in_group(conn, alice, g1),
        [],
    )
    new_id = player_id(conn, "Charlie")
    assert new_id is not None
    assert_eq(
        "Charlie has merged g1 results",
        results_for_player_in_group(conn, new_id, g1),
        [(g1a, 10), (g1b, 20)],
    )
    conn.close()


def scenario_rename_noop():
    """Renaming to the same name (case-insensitive) is a no-op."""
    print("\n[8] Rename Alice -> 'alice' (case-only change) is a no-op")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    game1 = add_game(conn, g1, "h1")
    add_result(conn, game1, alice, score=10)
    tgt = ensure_player(conn, "alice")
    assert tgt == alice
    run_reassign(conn, [(alice, tgt)], group_id=g1)

    assert_eq(
        "Alice still exists with same id", player_id(conn, "Alice"), alice
    )
    assert_eq(
        "Result count unchanged",
        results_for_player_in_group(conn, alice, g1),
        [(game1, 10)],
    )
    conn.close()


def scenario_rename_collision_no_conflict_in_group():
    """Rename Alice -> 'Bob' when both play in g1 but in different games.
    Bob ends up with both rows; Alice deleted."""
    print("\n[9] Rename Alice -> Bob, different games (Bob inherits both)")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    bob = add_player(conn, "Bob")
    g_a = add_game(conn, g1, "ha")
    g_b = add_game(conn, g1, "hb")
    add_result(conn, g_a, alice, score=10)
    add_result(conn, g_b, bob, score=20)
    tgt = ensure_player(conn, "Bob")
    assert tgt == bob
    run_reassign(conn, [(alice, tgt)], group_id=g1)

    assert_eq("Alice deleted", player_id(conn, "Alice"), None)
    assert_eq(
        "Bob has both rows",
        results_for_player_in_group(conn, bob, g1),
        [(g_a, 10), (g_b, 20)],
    )
    conn.close()


def scenario_delete_player_orphaned():
    """Delete Alice from g1 when she only plays in g1: player row gone."""
    print("\n[10] Delete in g1: Alice only plays in g1 -> player removed")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    alice = add_player(conn, "Alice")
    game1 = add_game(conn, g1, "h1")
    add_result(conn, game1, alice, score=10)
    run_delete_in_group(conn, player_id=alice, group_id=g1)

    assert_eq("Alice deleted (orphaned)", player_id(conn, "Alice"), None)
    assert_eq(
        "No leftover results",
        conn.execute("SELECT COUNT(*) FROM results").fetchone()[0],
        0,
    )
    conn.close()


def scenario_delete_player_keeps_other_group():
    """Delete Alice from g1 when she also plays in g2: g2 rows untouched."""
    print("\n[11] Delete in g1: Alice's g2 row survives")
    conn = fresh_db()
    g1 = add_group(conn, "G1", "0001")
    g2 = add_group(conn, "G2", "0002")
    alice = add_player(conn, "Alice")
    game1 = add_game(conn, g1, "h1")
    game2 = add_game(conn, g2, "h2")
    add_result(conn, game1, alice, score=10)
    add_result(conn, game2, alice, score=20)
    run_delete_in_group(conn, player_id=alice, group_id=g1)

    assert_eq(
        "Alice still exists (still in g2)", player_id(conn, "Alice"), alice
    )
    assert_eq(
        "Only the g2 row remains",
        results_for_player_in_group(conn, alice, g2),
        [(game2, 20)],
    )
    assert_eq(
        "No leftover g1 row",
        results_for_player_in_group(conn, alice, g1),
        [],
    )
    conn.close()


def main() -> int:
    scenarios = [
        scenario_rename_simple,
        scenario_rename_keep_other_group,
        scenario_rename_collision_with_existing_name,
        scenario_merge_simple,
        scenario_merge_target_equals_a,
        scenario_merge_same_game_conflict,
        scenario_merge_keeps_other_group,
        scenario_rename_noop,
        scenario_rename_collision_no_conflict_in_group,
        scenario_delete_player_orphaned,
        scenario_delete_player_keeps_other_group,
    ]
    failures = 0
    for fn in scenarios:
        try:
            fn()
        except AssertionError as exc:
            print(f"  FAIL  {fn.__name__}: {exc}")
            failures += 1
        except Exception as exc:
            print(f"  ERROR {fn.__name__}: {exc!r}")
            failures += 1
    print(f"\n{len(scenarios) - failures}/{len(scenarios)} scenarios passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
