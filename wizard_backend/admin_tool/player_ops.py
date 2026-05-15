"""
player_ops.py - DB helpers for per-group player rename / merge / delete.

Players are stored once in the global ``players`` table (the schema requires
a UNIQUE name), but the admin tool treats them as group-scoped: a rename or
merge in group X never touches a row that lives in any other group.

Every function here is pure backend logic. UI code is responsible for
catching ``DbError`` and surfacing it.
"""

from __future__ import annotations

from typing import Iterable

from db_backend import DbBackend, DbError


def ensure_player(backend: DbBackend, name: str) -> int:
    """Return the id of the player named ``name`` (case-insensitive),
    creating one if it does not exist yet. Raises ``DbError`` on failure.
    """
    name = name.strip()
    if not name:
        raise DbError("Player name must not be empty.")
    rows = backend.query(
        "SELECT id FROM players WHERE name = ? COLLATE NOCASE", (name,)
    )
    if rows:
        return int(rows[0]["id"])
    backend.execute("INSERT INTO players (name) VALUES (?)", (name,))
    rows = backend.query(
        "SELECT id FROM players WHERE name = ? COLLATE NOCASE", (name,)
    )
    if not rows:
        raise DbError(f"Failed to create or look up player '{name}'.")
    return int(rows[0]["id"])


def build_group_reassign_sql(
    moves: Iterable[tuple[int, int]], group_id: int
) -> str:
    """Build a single SQL script that moves results in ``group_id`` from
    each ``src`` to ``target``, in order.

    For each (src, target) pair, the script:
      1) Drops src's row for any game in ``group_id`` where ``target``
         already has a row (target wins on conflict).
      2) Updates remaining src rows in ``group_id`` to point at ``target``.
      3) Deletes the src player iff it is now globally orphaned (no rows
         in any group).

    The integer ids are inlined - they are obtained from controlled DB
    queries, never from user-supplied text, so injection is not a risk.
    """
    parts: list[str] = []
    gid = int(group_id)
    for src_id, target_id in moves:
        src = int(src_id)
        tgt = int(target_id)
        if src == tgt:
            continue
        parts.append(
            "DELETE FROM results "
            f" WHERE player_id = {src} "
            f"   AND game_id IN ("
            f"        SELECT r2.game_id FROM results r2 "
            f"          JOIN games g ON g.id = r2.game_id "
            f"         WHERE r2.player_id = {tgt} "
            f"           AND g.group_id  = {gid}"
            f"       );"
        )
        parts.append(
            f"UPDATE results SET player_id = {tgt} "
            f" WHERE player_id = {src} "
            f"   AND game_id IN ("
            f"        SELECT id FROM games WHERE group_id = {gid}"
            f"       );"
        )
        parts.append(
            f"DELETE FROM players WHERE id = {src} "
            f" AND NOT EXISTS ("
            f"   SELECT 1 FROM results WHERE player_id = {src}"
            f" );"
        )
    return "\n".join(parts)


def reassign_in_group(
    backend: DbBackend,
    moves: Iterable[tuple[int, int]],
    *,
    group_id: int,
) -> None:
    """Execute the SQL produced by ``build_group_reassign_sql`` atomically.

    Raises ``DbError`` on failure (one script -> one transaction, so a
    failure rolls everything back).
    """
    sql = build_group_reassign_sql(moves, group_id)
    if not sql:
        return
    backend.executescript(sql)


def delete_player_in_group(
    backend: DbBackend, *, player_id: int, group_id: int
) -> None:
    """Remove the player's results from games in ``group_id`` only.

    The player row is dropped iff it is globally orphaned afterwards.
    Raises ``DbError`` on failure.
    """
    pid = int(player_id)
    gid = int(group_id)
    sql = (
        f"DELETE FROM results "
        f" WHERE player_id = {pid} "
        f"   AND game_id IN ("
        f"        SELECT id FROM games WHERE group_id = {gid}"
        f"       );\n"
        f"DELETE FROM players WHERE id = {pid} "
        f" AND NOT EXISTS ("
        f"   SELECT 1 FROM results WHERE player_id = {pid}"
        f" );"
    )
    backend.executescript(sql)


def fetch_players_in_group(
    backend: DbBackend, group_id: int
) -> list[dict]:
    """Players who have at least one result in a game of ``group_id``."""
    return backend.query(
        """
        SELECT p.id,
               p.name,
               COUNT(r.game_id)                            AS games,
               SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END) AS wins,
               ROUND(AVG(r.final_score), 1)               AS avg_score
          FROM players p
          JOIN results r ON r.player_id = p.id
          JOIN games   g ON g.id = r.game_id
         WHERE g.group_id = ?
      GROUP BY p.id
      ORDER BY p.name COLLATE NOCASE
        """,
        (group_id,),
    )
