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
  GET  /api/feedback                     – list all feedback messages
  POST /api/feedback                     – submit a new feedback message
  POST /api/feedback/{id}/vote           – upvote or downvote a message
  GET  /                                 – landing page
  GET  /leaderboard                      – HTML leaderboard page
  GET  /feedback                         – HTML feedback page
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from typing import Optional

import database as db
from translations import TRANSLATIONS

app = FastAPI(title="Wizard Leaderboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

def get_translations(lang: str) -> dict[str, str]:
    if lang not in TRANSLATIONS:
        lang = "en"
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"])

def trans(key: str, lang: str = "en") -> str:
    lang_dict = get_translations(lang)
    return lang_dict.get(key, key)

templates.env.globals["_"] = trans


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


class FeedbackCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=db.FEEDBACK_MAX_LEN)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("message must not be empty")
        return cleaned


class FeedbackVote(BaseModel):
    vote: str

    @field_validator("vote")
    @classmethod
    def vote_must_be_valid(cls, v: str) -> str:
        if v not in ("up", "down"):
            raise ValueError("vote must be 'up' or 'down'")
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
    """Check whether a player name already exists (global registry)."""
    return {"name": name, "exists": db.player_exists(name)}


@app.get("/api/groups/{code}/players/check")
def check_group_player(
    code: str,
    name: str = Query(..., min_length=1),
) -> dict:
    """Check whether a player has already played in the given group.

    Name matching is case-insensitive; existence is scoped to games that
    were submitted with that group's 4-digit code.
    """
    if len(code) != 4 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Code must be exactly 4 digits")
    exists = db.player_exists_in_group(name=name, code=code)
    if exists is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"name": name, "code": code, "exists": exists}


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
    """List all groups (public + hidden), optionally filtered by name.

    The 4-digit ``code`` is deliberately omitted — it is the shared secret
    required to join, and must stay private. Clients display ``player_count``
    instead.
    """
    return db.list_groups(search=search)


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


# ── Feedback endpoints ────────────────────────────────────────────────────────


@app.get("/api/feedback")
def list_feedback_json() -> list[dict]:
    """Return all feedback messages, sorted by net votes."""
    return db.list_feedback()


@app.post("/api/feedback", status_code=201)
def submit_feedback(body: FeedbackCreate) -> dict:
    """Create a new feedback message."""
    return db.create_feedback(message=body.message)


@app.post("/api/feedback/{feedback_id}/vote")
def vote_feedback(feedback_id: int, body: FeedbackVote) -> dict:
    """Upvote or downvote a feedback message."""
    updated = db.vote_feedback(feedback_id=feedback_id, vote_type=body.vote)
    if updated is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return updated


# ── HTML pages ───────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def home_page(request: Request, lang: str = "en") -> HTMLResponse:
    """Render the landing page."""
    return templates.TemplateResponse(
        request, "index.html", {"active_page": "home", "lang": lang}
    )


@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page(request: Request, lang: str = "en") -> HTMLResponse:
    """Render the global groups leaderboard with group-code entry flow."""
    return templates.TemplateResponse(
        request, "leaderboard.html", {"active_page": "leaderboard", "lang": lang}
    )


@app.get("/leaderboard/group/{code}", response_class=HTMLResponse)
def group_leaderboard_page(
    request: Request,
    code: str,
    lang: str = "en",
) -> HTMLResponse:
    """Render a specific group's player leaderboard.

    ``code`` is the group's 4-digit shared secret. Entering it counts as
    proof of membership and works for hidden groups too.
    """
    if len(code) != 4 or not code.isdigit():
        raise HTTPException(status_code=400, detail="Code must be exactly 4 digits")
    group = db.get_group_by_code(code)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return templates.TemplateResponse(
        request,
        "group_leaderboard.html",
        {
            "active_page": "leaderboard",
            "lang": lang,
            "group": group,
        },
    )


@app.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request, lang: str = "en") -> HTMLResponse:
    """Render the public feedback page."""
    feedbacks = db.list_feedback()
    return templates.TemplateResponse(
        request,
        "feedback.html",
        {"active_page": "feedback", "feedbacks": feedbacks, "lang": lang},
    )
