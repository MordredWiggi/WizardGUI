"""
database.py – SQLite database layer for the Wizard Leaderboard.

Tables:
  - players:  unique player names (case-insensitive)
  - groups:   named groups with 4-digit code and visibility
  - games:    one row per completed game (deduplicated by hash)
  - results:  per-player results for each game
  - feedback: public feedback messages with upvote/downvote counters
"""
from __future__ import annotations

import os
import sqlite3
from typing import Optional

DB_PATH = os.environ.get("WIZARD_DB_PATH", "/data/leaderboard.db")


def _get_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db


def init_db() -> None:
    """Create tables if they don't exist, and run idempotent migrations."""
    db = _get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT    UNIQUE NOT NULL COLLATE NOCASE
        );
        CREATE TABLE IF NOT EXISTS groups (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            code       TEXT    UNIQUE NOT NULL,
            visibility TEXT    NOT NULL DEFAULT 'public'
        );
        CREATE TABLE IF NOT EXISTS games (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            game_hash   TEXT    UNIQUE NOT NULL,
            game_mode   TEXT    NOT NULL,
            num_players INTEGER NOT NULL,
            played_at   TEXT    NOT NULL,
            group_id    INTEGER REFERENCES groups(id)
        );
        CREATE TABLE IF NOT EXISTS results (
            game_id      INTEGER NOT NULL REFERENCES games(id),
            player_id    INTEGER NOT NULL REFERENCES players(id),
            final_score  INTEGER NOT NULL,
            rank         INTEGER NOT NULL,
            correct_bids INTEGER NOT NULL,
            total_rounds INTEGER NOT NULL,
            PRIMARY KEY (game_id, player_id)
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            message    TEXT    NOT NULL,
            upvotes    INTEGER NOT NULL DEFAULT 0,
            downvotes  INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """)
    # Idempotent migration: add group_id column to games if missing (for existing DBs)
    cols = {row[1] for row in db.execute("PRAGMA table_info(games)")}
    if "group_id" not in cols:
        db.execute("ALTER TABLE games ADD COLUMN group_id INTEGER REFERENCES groups(id)")
        db.commit()
    db.close()


# ── Player helpers ────────────────────────────────────────────────────────────

def player_exists(name: str) -> bool:
    """Check whether a player name is already registered (global).

    Kept for compatibility with clients still hitting the old endpoint.
    """
    db = _get_db()
    row = db.execute(
        "SELECT 1 FROM players WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    db.close()
    return row is not None


def player_exists_in_group(name: str, code: str) -> Optional[bool]:
    """Check whether ``name`` has played at least one game in the group
    identified by ``code``.

    Returns ``None`` if the group itself does not exist, ``True`` if the
    player has a result in that group, ``False`` otherwise.
    """
    db = _get_db()
    try:
        group_row = db.execute(
            "SELECT id FROM groups WHERE code = ?", (code,)
        ).fetchone()
        if group_row is None:
            return None
        row = db.execute(
            """
            SELECT 1
            FROM results r
            JOIN players p ON p.id = r.player_id
            JOIN games   g ON g.id = r.game_id
            WHERE g.group_id = ? AND p.name = ? COLLATE NOCASE
            LIMIT 1
            """,
            (group_row["id"], name),
        ).fetchone()
        return row is not None
    finally:
        db.close()


def _get_or_create_player(db: sqlite3.Connection, name: str) -> int:
    row = db.execute(
        "SELECT id FROM players WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row:
        return row["id"]
    cursor = db.execute("INSERT INTO players (name) VALUES (?)", (name,))
    return cursor.lastrowid


# ── Group helpers ─────────────────────────────────────────────────────────────

def create_group(name: str, code: str, visibility: str = "public") -> Optional[dict]:
    """Create a new group. Returns the created group dict, or None if code conflicts."""
    if len(code) != 4 or not code.isdigit():
        raise ValueError("Group code must be exactly 4 digits")
    db = _get_db()
    try:
        cursor = db.execute(
            "INSERT INTO groups (name, code, visibility) VALUES (?, ?, ?)",
            (name, code, visibility),
        )
        group_id = cursor.lastrowid
        db.commit()
        return {"id": group_id, "name": name, "code": code, "visibility": visibility}
    except sqlite3.IntegrityError:
        return None  # code already in use
    finally:
        db.close()


def get_group_by_code(code: str) -> Optional[dict]:
    """Fetch a group by its 4-digit code. Returns None if not found."""
    db = _get_db()
    row = db.execute(
        "SELECT id, name, code, visibility FROM groups WHERE code = ?", (code,)
    ).fetchone()
    db.close()
    if row is None:
        return None
    return dict(row)


def list_groups(search: str = "") -> list[dict]:
    """Return all groups (public + hidden), optionally filtered by name.

    The returned dicts intentionally omit the 4-digit ``code`` — it is a shared
    secret for joining and must never leak in public API responses.
    Each entry includes ``player_count`` (distinct players who played in the
    group) so clients can display group sizes instead of the code.
    """
    db = _get_db()
    base_sql = """
        SELECT gr.id,
               gr.name,
               gr.visibility,
               COUNT(DISTINCT r.player_id) AS player_count
        FROM groups gr
        LEFT JOIN games   g ON g.group_id = gr.id
        LEFT JOIN results r ON r.game_id  = g.id
    """
    if search:
        rows = db.execute(
            base_sql + " WHERE gr.name LIKE ? COLLATE NOCASE GROUP BY gr.id ORDER BY gr.name",
            (f"%{search}%",),
        ).fetchall()
    else:
        rows = db.execute(
            base_sql + " GROUP BY gr.id ORDER BY gr.name"
        ).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── Game submission ────────────────────────────────────────────────────────────

def submit_game(
    game_hash: str,
    game_mode: str,
    num_players: int,
    played_at: str,
    player_results: list[dict],
    group_id: Optional[int] = None,
) -> bool:
    """Insert a completed game.  Returns False if game_hash already exists."""
    db = _get_db()
    try:
        if db.execute(
            "SELECT 1 FROM games WHERE game_hash = ?", (game_hash,)
        ).fetchone():
            db.close()
            return False

        cursor = db.execute(
            "INSERT INTO games (game_hash, game_mode, num_players, played_at, group_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (game_hash, game_mode, num_players, played_at, group_id),
        )
        game_id = cursor.lastrowid

        for pr in player_results:
            player_id = _get_or_create_player(db, pr["name"])
            db.execute(
                "INSERT INTO results "
                "(game_id, player_id, final_score, rank, correct_bids, total_rounds) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    game_id,
                    player_id,
                    pr["final_score"],
                    pr["rank"],
                    pr["correct_bids"],
                    pr["total_rounds"],
                ),
            )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Player leaderboard ────────────────────────────────────────────────────────

def get_leaderboard(game_mode: str) -> list[dict]:
    """Return all player stats for a game mode (global, across all groups).
    Sorting is done client-side."""
    db = _get_db()

    rows = db.execute(
        """
        SELECT p.name,
               p.id                                                       AS player_id,
               SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END)               AS wins,
               COUNT(*)                                                    AS games,
               ROUND(AVG(r.final_score), 1)                               AS avg_score,
               ROUND(
                   CAST(SUM(r.correct_bids) AS REAL)
                   / NULLIF(SUM(r.total_rounds), 0) * 100, 1
               )                                                           AS hit_rate,
               MAX(r.final_score)                                          AS highest_score
        FROM results r
        JOIN players p ON r.player_id = p.id
        JOIN games   g ON r.game_id  = g.id
        WHERE g.game_mode = ?
        GROUP BY p.id
        """,
        (game_mode,),
    ).fetchall()

    result = _build_player_stats(db, rows, game_mode)
    db.close()
    return result


def get_group_player_leaderboard(code: str, game_mode: str) -> Optional[list[dict]]:
    """Return player stats for a specific group identified by code.
    Returns None if the group does not exist."""
    db = _get_db()
    group_row = db.execute(
        "SELECT id FROM groups WHERE code = ?", (code,)
    ).fetchone()
    if group_row is None:
        db.close()
        return None

    group_id = group_row["id"]
    rows = db.execute(
        """
        SELECT p.name,
               p.id                                                       AS player_id,
               SUM(CASE WHEN r.rank = 1 THEN 1 ELSE 0 END)               AS wins,
               COUNT(*)                                                    AS games,
               ROUND(AVG(r.final_score), 1)                               AS avg_score,
               ROUND(
                   CAST(SUM(r.correct_bids) AS REAL)
                   / NULLIF(SUM(r.total_rounds), 0) * 100, 1
               )                                                           AS hit_rate,
               MAX(r.final_score)                                          AS highest_score
        FROM results r
        JOIN players p ON r.player_id = p.id
        JOIN games   g ON r.game_id  = g.id
        WHERE g.game_mode = ? AND g.group_id = ?
        GROUP BY p.id
        """,
        (game_mode, group_id),
    ).fetchall()

    result = _build_player_stats(db, rows, game_mode, group_id=group_id)
    db.close()
    return result


def _build_player_stats(
    db: sqlite3.Connection,
    rows,
    game_mode: str,
    group_id: Optional[int] = None,
) -> list[dict]:
    """Convert raw DB rows into player stat dicts with win streaks."""
    result: list[dict] = []
    for row in rows:
        streak_query = """
            SELECT CASE WHEN r.rank = 1 THEN 1 ELSE 0 END AS won
            FROM results r
            JOIN games g ON r.game_id = g.id
            WHERE r.player_id = ? AND g.game_mode = ?
        """
        params: list = [row["player_id"], game_mode]
        if group_id is not None:
            streak_query += " AND g.group_id = ?"
            params.append(group_id)
        streak_query += " ORDER BY g.played_at"

        streak_rows = db.execute(streak_query, params).fetchall()

        max_streak = current_streak = 0
        for sr in streak_rows:
            if sr["won"]:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        games = row["games"] or 1
        result.append(
            {
                "name": row["name"],
                "wins": row["wins"] or 0,
                "games": games,
                "win_rate": round((row["wins"] or 0) / games * 100, 1),
                "avg_score": row["avg_score"] or 0,
                "hit_rate": row["hit_rate"] or 0,
                "highest_score": row["highest_score"] or 0,
                "win_streak": max_streak,
            }
        )
    return result


# ── Global groups leaderboard ─────────────────────────────────────────────────

def get_groups_leaderboard() -> list[dict]:
    """Return aggregated stats per public group (global groups leaderboard).

    Metrics per group:
      - total_games: number of completed games
      - avg_score:   average final score across all players/games
      - avg_hit_rate: average bid hit rate across all players/games
    Hidden groups are excluded.
    """
    db = _get_db()
    rows = db.execute(
        """
        SELECT
            gr.id,
            gr.name,
            COUNT(DISTINCT g.id)                                            AS total_games,
            COUNT(DISTINCT r.player_id)                                     AS player_count,
            ROUND(AVG(r.final_score), 1)                                    AS avg_score,
            ROUND(
                CAST(SUM(r.correct_bids) AS REAL)
                / NULLIF(SUM(r.total_rounds), 0) * 100, 1
            )                                                               AS avg_hit_rate
        FROM groups gr
        JOIN games   g ON g.group_id  = gr.id
        JOIN results r ON r.game_id   = g.id
        WHERE gr.visibility = 'public'
        GROUP BY gr.id
        """
    ).fetchall()
    db.close()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "total_games": r["total_games"] or 0,
            "player_count": r["player_count"] or 0,
            "avg_score": r["avg_score"] or 0.0,
            "avg_hit_rate": r["avg_hit_rate"] or 0.0,
        }
        for r in rows
    ]


# ── Feedback ──────────────────────────────────────────────────────────────────

FEEDBACK_MAX_LEN = 2000


def create_feedback(message: str) -> dict:
    """Insert a new feedback message and return the created row."""
    db = _get_db()
    try:
        cursor = db.execute(
            "INSERT INTO feedback (message) VALUES (?)", (message,)
        )
        feedback_id = cursor.lastrowid
        db.commit()
        row = db.execute(
            "SELECT id, message, upvotes, downvotes, created_at "
            "FROM feedback WHERE id = ?",
            (feedback_id,),
        ).fetchone()
        return dict(row)
    finally:
        db.close()


def list_feedback() -> list[dict]:
    """Return all feedback ordered by net votes (desc) then newest first."""
    db = _get_db()
    rows = db.execute(
        """
        SELECT id, message, upvotes, downvotes, created_at,
               (upvotes - downvotes) AS net_votes
        FROM feedback
        ORDER BY net_votes DESC, created_at DESC
        """
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def vote_feedback(feedback_id: int, vote_type: str) -> Optional[dict]:
    """Increment upvotes or downvotes on a feedback row. Returns the updated row,
    or None if no such feedback exists."""
    if vote_type not in ("up", "down"):
        raise ValueError("vote_type must be 'up' or 'down'")
    column = "upvotes" if vote_type == "up" else "downvotes"
    db = _get_db()
    try:
        cursor = db.execute(
            f"UPDATE feedback SET {column} = {column} + 1 WHERE id = ?",
            (feedback_id,),
        )
        if cursor.rowcount == 0:
            return None
        db.commit()
        row = db.execute(
            "SELECT id, message, upvotes, downvotes, created_at "
            "FROM feedback WHERE id = ?",
            (feedback_id,),
        ).fetchone()
        return dict(row)
    finally:
        db.close()
