"""
main.py – FastAPI application for the Wizard Leaderboard.

Endpoints:
  POST /api/games              – submit a completed game
  GET  /api/players/check      – check if a player name exists
  GET  /api/leaderboard        – JSON leaderboard data
  GET  /                       – HTML leaderboard page
"""
from __future__ import annotations

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import database as db

app = FastAPI(title="Wizard Leaderboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup() -> None:
    db.init_db()


# ── Pydantic models ─────────────────────────────────────────────────────────


class PlayerResult(BaseModel):
    name: str
    final_score: int
    rank: int
    correct_bids: int
    total_rounds: int


class GameSubmission(BaseModel):
    game_hash: str
    game_mode: str
    num_players: int
    played_at: str
    players: list[PlayerResult]


# ── API endpoints ────────────────────────────────────────────────────────────


@app.post("/api/games")
def submit_game(game: GameSubmission) -> dict:
    """Submit a completed game to the leaderboard."""
    created = db.submit_game(
        game_hash=game.game_hash,
        game_mode=game.game_mode,
        num_players=game.num_players,
        played_at=game.played_at,
        player_results=[p.model_dump() for p in game.players],
    )
    if created:
        return {"status": "created"}
    return {"status": "duplicate"}


@app.get("/api/players/check")
def check_player(name: str = Query(..., min_length=1)) -> dict:
    """Check whether a player name already exists."""
    return {"name": name, "exists": db.player_exists(name)}


@app.get("/api/leaderboard")
def leaderboard_json(mode: str = Query("standard")) -> list[dict]:
    """Return leaderboard data as JSON."""
    return db.get_leaderboard(mode)


# ── HTML page ────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page(request: Request) -> HTMLResponse:
    """Render the leaderboard as a web page."""
    return templates.TemplateResponse(request, "leaderboard.html")
