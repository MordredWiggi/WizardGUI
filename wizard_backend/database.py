"""
database.py – SQLite database layer for the Wizard Leaderboard.

Tables:
  - players: unique player names (case-insensitive)
  - games: one row per completed game (deduplicated by hash)
  - results: per-player results for each game
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
    """Create tables if they don't exist."""
    db = _get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT    UNIQUE NOT NULL COLLATE NOCASE
        );
        CREATE TABLE IF NOT EXISTS games (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            game_hash   TEXT    UNIQUE NOT NULL,
            game_mode   TEXT    NOT NULL,
            num_players INTEGER NOT NULL,
            played_at   TEXT    NOT NULL
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
    """)
    db.close()

def player_exists(name: str) -> bool:
    """Check whether a player name is already registered."""
    db = _get_db()
    row = db.execute(
        "SELECT 1 FROM players WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    db.close()
    return row is not None


def _get_or_create_player(db: sqlite3.Connection, name: str) -> int:
    row = db.execute(
        "SELECT id FROM players WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    if row:
        return row["id"]
    cursor = db.execute("INSERT INTO players (name) VALUES (?)", (name,))
    return cursor.lastrowid


def submit_game(
    game_hash: str,
    game_mode: str,
    num_players: int,
    played_at: str,
    player_results: list[dict],
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
            "INSERT INTO games (game_hash, game_mode, num_players, played_at) "
            "VALUES (?, ?, ?, ?)",
            (game_hash, game_mode, num_players, played_at),
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


def get_leaderboard(game_mode: str) -> list[dict]:
    """Return all player stats for a game mode.  Sorting is done client-side."""
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

    result: list[dict] = []
    for row in rows:
        # Compute longest win streak for this player
        streak_rows = db.execute(
            """
            SELECT CASE WHEN r.rank = 1 THEN 1 ELSE 0 END AS won
            FROM results r
            JOIN games g ON r.game_id = g.id
            WHERE r.player_id = ? AND g.game_mode = ?
            ORDER BY g.played_at
            """,
            (row["player_id"], game_mode),
        ).fetchall()

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

    db.close()
    return result
