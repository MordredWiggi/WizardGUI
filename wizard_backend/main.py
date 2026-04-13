"""
main.py – FastAPI application for the Wizard Leaderboard.

Endpoints:
  POST /api/games                        – submit a completed game
  GET  /api/players/check                – check if a player name exists
  GET  /api/leaderboard                  – JSON player leaderboard (global)
  POST /api/groups                       – create a group
  GET  /api/groups                       – list public groups (optional ?search=)
  GET  /api/groups/{code}                – get group by 4-digit code
  GET  /api/leaderboard/groups           – global groups leaderboard
  GET  /api/leaderboard/group/{code}     – player leaderboard for a specific group
  GET  /                                 – HTML leaderboard page
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

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
    group_code: str | None = None  # optional 4-digit group code


class GroupCreate(BaseModel):
    name: str
    code: str
    visibility: str = "public"

    @field_validator("code")
    @classmethod
    def code_must_be_4_digits(cls, v: str) -> str:
        if len(v) != 4 or not v.isdigit():
            raise ValueError("Group code must be exactly 4 digits")
        return v

    @field_validator("visibility")
    @classmethod
    def visibility_must_be_valid(cls, v: str) -> str:
        if v not in ("public", "hidden"):
            raise ValueError("visibility must be 'public' or 'hidden'")
        return v


# ── Game endpoints ────────────────────────────────────────────────────────────


@app.post("/api/games")
def submit_game(game: GameSubmission) -> dict:
    """Submit a completed game to the leaderboard."""
    group_id: int | None = None
    if game.group_code:
        group = db.get_group_by_code(game.group_code)
        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")
        group_id = group["id"]

    created = db.submit_game(
        game_hash=game.game_hash,
        game_mode=game.game_mode,
        num_players=game.num_players,
        played_at=game.played_at,
        player_results=[p.model_dump() for p in game.players],
        group_id=group_id,
    )
    if created:
        return {"status": "created"}
    return {"status": "duplicate"}


@app.get("/api/players/check")
def check_player(name: str = Query(..., min_length=1)) -> dict:
    """Check whether a player name already exists."""
    return {"name": name, "exists": db.player_exists(name)}


# ── Player leaderboard ────────────────────────────────────────────────────────


@app.get("/api/leaderboard")
def leaderboard_json(mode: str = Query("standard")) -> list[dict]:
    """Return global player leaderboard data as JSON."""
    return db.get_leaderboard(mode)


# ── Group endpoints ───────────────────────────────────────────────────────────


@app.post("/api/groups", status_code=201)
def create_group(body: GroupCreate) -> dict:
    """Create a new group with a unique 4-digit code."""
    result = db.create_group(
        name=body.name,
        code=body.code,
        visibility=body.visibility,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Group code already in use")
    return result


@app.get("/api/groups")
def list_groups(search: str = Query("")) -> list[dict]:
    """List all public groups, optionally filtered by name."""
    return db.list_public_groups(search=search)


@app.get("/api/groups/{code}")
def get_group(code: str) -> dict:
    """Get a group by its 4-digit code (works for hidden groups too)."""
    if len(code) != 4 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Code must be exactly 4 digits")
    group = db.get_group_by_code(code)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


# ── Group leaderboard endpoints ───────────────────────────────────────────────


@app.get("/api/leaderboard/groups")
def groups_leaderboard() -> list[dict]:
    """Return the global groups leaderboard (public groups only, aggregated metrics)."""
    return db.get_groups_leaderboard()


@app.get("/api/leaderboard/group/{code}")
def group_player_leaderboard(
    code: str,
    mode: str = Query("standard"),
) -> list[dict]:
    """Return player leaderboard for a specific group identified by 4-digit code."""
    if len(code) != 4 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Code must be exactly 4 digits")
    result = db.get_group_player_leaderboard(code=code, game_mode=mode)
    if result is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return result


# ── HTML page ────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page(request: Request) -> HTMLResponse:
    """Render the leaderboard as a web page."""
    return templates.TemplateResponse(request, "leaderboard.html")
