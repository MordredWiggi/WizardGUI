"""
leaderboard_client.py – HTTP client for the Wizard Leaderboard API.

Provides synchronous helpers and QThread workers so the UI never blocks.
Uses only urllib (stdlib) to avoid extra dependencies.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional

from PyQt6 import QtCore


# ── Submission builder ───────────────────────────────────────────────────────


def compute_game_hash(game_data: dict) -> str:
    """Deterministic hash for deduplication (first 16 hex chars of SHA-256)."""
    canonical = {"mode": game_data.get("game_mode", "standard"), "players": []}
    for p in sorted(game_data.get("players", []), key=lambda x: x["name"]):
        canonical["players"].append(
            {
                "n": p["name"],
                "r": [{"s": r["said"], "a": r["achieved"]} for r in p["rounds"]],
            }
        )
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_game_submission(
    game_data: dict,
    played_at: Optional[str] = None,
    group_code: Optional[str] = None,
) -> dict:
    """Convert a local game dict into the payload expected by POST /api/games."""
    players = game_data.get("players", [])
    num_players = len(players)
    total_rounds = 60 // num_players if num_players else 0
    game_mode = game_data.get("game_mode", "standard")

    player_results: list[dict] = []
    for p in players:
        rounds = p.get("rounds", [])
        # Recompute final score from rounds
        if game_mode == "multiplicative":
            score = 100
            for r in rounds:
                if r["said"] == r["achieved"]:
                    score = score * (2 + r["achieved"])
                else:
                    score = score / (1 + abs(r["achieved"] - r["said"]))
            score = round(score)
        else:
            score = 0
            for r in rounds:
                if r["said"] == r["achieved"]:
                    score += 20 + r["said"] * 10
                else:
                    score += -10 * abs(r["said"] - r["achieved"])

        correct_bids = sum(1 for r in rounds if r["said"] == r["achieved"])
        player_results.append(
            {
                "name": p["name"],
                "final_score": score,
                "correct_bids": correct_bids,
                "total_rounds": len(rounds),
            }
        )

    # Assign ranks by descending score
    for rank, pr in enumerate(
        sorted(player_results, key=lambda x: x["final_score"], reverse=True), 1
    ):
        pr["rank"] = rank

    payload: dict = {
        "game_hash": compute_game_hash(game_data),
        "game_mode": game_mode,
        "num_players": num_players,
        "played_at": played_at or datetime.now().isoformat(),
        "players": player_results,
    }
    if group_code:
        payload["group_code"] = group_code
    return payload


# ── Synchronous HTTP helpers ─────────────────────────────────────────────────


def _post_json(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _get_json(url: str, timeout: int = 5):
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


class LeaderboardClient:
    """Thin wrapper around the leaderboard REST API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def check_player(self, name: str) -> Optional[bool]:
        """Returns True if name exists, False if new, None on error."""
        url = f"{self.base_url}/api/players/check?name={urllib.parse.quote(name)}"
        data = _get_json(url, timeout=3)
        if data is None:
            return None
        return data.get("exists", False)

    def submit_game(self, payload: dict) -> bool:
        url = f"{self.base_url}/api/games"
        result = _post_json(url, payload)
        return result is not None

    def get_leaderboard(self, mode: str = "standard") -> Optional[list]:
        """Fetch global player leaderboard data. Returns list of dicts or None on error."""
        url = f"{self.base_url}/api/leaderboard?mode={urllib.parse.quote(mode)}"
        data = _get_json(url, timeout=5)
        if data is None:
            return None
        return data

    # ── Group methods ────────────────────────────────────────────────────────

    def create_group(self, name: str, code: str, visibility: str = "public") -> Optional[dict]:
        """Create a new group. Returns group dict on success, None on failure."""
        url = f"{self.base_url}/api/groups"
        result = _post_json(url, {"name": name, "code": code, "visibility": visibility})
        return result

    def get_group_by_code(self, code: str) -> Optional[dict]:
        """Fetch group by 4-digit code. Returns dict or None if not found/error."""
        url = f"{self.base_url}/api/groups/{urllib.parse.quote(code)}"
        return _get_json(url, timeout=5)

    def list_groups(self, search: str = "") -> Optional[list]:
        """Fetch public groups, optionally filtered by name."""
        qs = f"?search={urllib.parse.quote(search)}" if search else ""
        url = f"{self.base_url}/api/groups{qs}"
        return _get_json(url, timeout=5)

    def get_groups_leaderboard(self) -> Optional[list]:
        """Fetch the global groups leaderboard."""
        url = f"{self.base_url}/api/leaderboard/groups"
        return _get_json(url, timeout=5)

    def get_group_player_leaderboard(self, code: str, mode: str = "standard") -> Optional[list]:
        """Fetch player leaderboard for a specific group."""
        url = (
            f"{self.base_url}/api/leaderboard/group/{urllib.parse.quote(code)}"
            f"?mode={urllib.parse.quote(mode)}"
        )
        return _get_json(url, timeout=5)


# ── QThread workers (keep UI responsive) ─────────────────────────────────────


class PlayerCheckWorker(QtCore.QThread):
    """Check player name availability in the background."""

    result = QtCore.pyqtSignal(str, object)  # (name, exists_or_None)

    def __init__(self, client: LeaderboardClient, name: str) -> None:
        super().__init__()
        self._client = client
        self._name = name

    def run(self) -> None:
        exists = self._client.check_player(self._name)
        self.result.emit(self._name, exists)


class GameSubmitWorker(QtCore.QThread):
    """Submit a completed game in the background."""

    finished = QtCore.pyqtSignal(bool)

    def __init__(self, client: LeaderboardClient, payload: dict) -> None:
        super().__init__()
        self._client = client
        self._payload = payload

    def run(self) -> None:
        success = self._client.submit_game(self._payload)
        self.finished.emit(success)


class LeaderboardFetchWorker(QtCore.QThread):
    """Fetch player leaderboard data in the background."""

    result = QtCore.pyqtSignal(object)  # list[dict] or None

    def __init__(self, client: LeaderboardClient, mode: str) -> None:
        super().__init__()
        self._client = client
        self._mode = mode

    def run(self) -> None:
        data = self._client.get_leaderboard(self._mode)
        self.result.emit(data)


class GroupCodeCheckWorker(QtCore.QThread):
    """Validate a group code in the background."""

    result = QtCore.pyqtSignal(object)  # dict (group) or None

    def __init__(self, client: LeaderboardClient, code: str) -> None:
        super().__init__()
        self._client = client
        self._code = code

    def run(self) -> None:
        group = self._client.get_group_by_code(self._code)
        self.result.emit(group)


class GroupsListWorker(QtCore.QThread):
    """Fetch public groups list in the background."""

    result = QtCore.pyqtSignal(object)  # list[dict] or None

    def __init__(self, client: LeaderboardClient, search: str = "") -> None:
        super().__init__()
        self._client = client
        self._search = search

    def run(self) -> None:
        groups = self._client.list_groups(self._search)
        self.result.emit(groups)


class GroupsLeaderboardFetchWorker(QtCore.QThread):
    """Fetch global groups leaderboard in the background."""

    result = QtCore.pyqtSignal(object)  # list[dict] or None

    def __init__(self, client: LeaderboardClient) -> None:
        super().__init__()
        self._client = client

    def run(self) -> None:
        data = self._client.get_groups_leaderboard()
        self.result.emit(data)


class GroupPlayerLeaderboardWorker(QtCore.QThread):
    """Fetch player leaderboard for a specific group in the background."""

    result = QtCore.pyqtSignal(object)  # list[dict] or None

    def __init__(self, client: LeaderboardClient, code: str, mode: str) -> None:
        super().__init__()
        self._client = client
        self._code = code
        self._mode = mode

    def run(self) -> None:
        data = self._client.get_group_player_leaderboard(self._code, self._mode)
        self.result.emit(data)


class GroupCreateWorker(QtCore.QThread):
    """Create a new group in the background."""

    result = QtCore.pyqtSignal(object)  # dict (group) or None

    def __init__(self, client: LeaderboardClient, name: str, code: str, visibility: str) -> None:
        super().__init__()
        self._client = client
        self._name = name
        self._code = code
        self._visibility = visibility

    def run(self) -> None:
        group = self._client.create_group(self._name, self._code, self._visibility)
        self.result.emit(group)
