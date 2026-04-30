"""
SaveManager – Laden/Speichern von Spielständen als JSON
sowie Export von Plots als Bilddatei.

Speicherort: ~/.wizard_gui/games/
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

SAVE_DIR = Path.home() / ".wizard_gui" / "games"
SCHEMA_VERSION = "1.1"

# Reserved filename for the auto-paused game (Home button mid-round).
# Stored alongside regular saves but excluded from listings.
PAUSED_FILENAME = "__paused__.json"


class SaveManager:
    def __init__(self, save_dir: Path = SAVE_DIR) -> None:
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ save

    def save_game(
        self,
        game_data: dict,
        game_name: Optional[str] = None,
        pending_sync: bool = False,
        group_code: Optional[str] = None,
    ) -> Path:
        """Persist game_data as JSON; returns the file path.

        ``pending_sync`` marks games completed offline that still need to be
        uploaded to the leaderboard. ``group_code`` (optional) is the target
        group for later sync.
        """
        if not game_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            players = "_".join(p["name"] for p in game_data.get("players", []))
            game_name = f"{ts}_{players}" if players else f"game_{ts}"

        # sanitise filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in game_name)
        filepath = self.save_dir / f"{safe_name}.json"

        payload = {
            "schema_version": SCHEMA_VERSION,
            "meta": {
                "name": game_name,
                "saved_at": datetime.now().isoformat(),
                "pending_sync": bool(pending_sync),
                "group_code": group_code,
            },
            "game": game_data,
        }
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        return filepath

    # ------------------------------------------------------------------ load

    def load_game(self, filepath: Path) -> dict:
        """Load a JSON file and return the inner game dict."""
        with open(filepath, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload["game"]

    # ----------------------------------------------------------- paused game

    @property
    def _paused_path(self) -> Path:
        return self.save_dir / PAUSED_FILENAME

    def save_paused(self, game_data: dict, group: Optional[dict] = None) -> Path:
        """Persist the in-progress game so it can be resumed from the menu."""
        payload = {
            "schema_version": SCHEMA_VERSION,
            "meta": {
                "saved_at": datetime.now().isoformat(),
                "paused": True,
                "group": group,
            },
            "game": game_data,
        }
        fp = self._paused_path
        with open(fp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        return fp

    def load_paused(self) -> Optional[Dict]:
        """Return ``{'game': ..., 'group': ...}`` or None when nothing is paused."""
        fp = self._paused_path
        if not fp.exists():
            return None
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            return {
                "game": payload.get("game", {}),
                "group": (payload.get("meta") or {}).get("group"),
            }
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def has_paused(self) -> bool:
        return self._paused_path.exists()

    def clear_paused(self) -> None:
        try:
            self._paused_path.unlink(missing_ok=True)
        except OSError:
            pass

    # ----------------------------------------------------------- list games

    def list_saved_games(self) -> List[Dict]:
        """Return metadata for all saved games, newest first."""
        games: List[Dict] = []
        for fp in sorted(self.save_dir.glob("*.json"), reverse=True):
            if fp.name == PAUSED_FILENAME:
                continue
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                meta = payload.get("meta", {})
                game = payload.get("game", {})
                players = [p["name"] for p in game.get("players", [])]
                rounds = game.get("round_number", 0)
                games.append(
                    {
                        "filepath": fp,
                        "name": meta.get("name", fp.stem),
                        "saved_at": meta.get("saved_at", ""),
                        "players": players,
                        "rounds": rounds,
                        "pending_sync": bool(meta.get("pending_sync", False)),
                        "group_code": meta.get("group_code"),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return games

    # ----------------------------------------------------------- pending sync

    def list_pending_sync_games(self) -> List[Dict]:
        """Return metadata + game for games that need to be uploaded."""
        pending: List[Dict] = []
        for fp in sorted(self.save_dir.glob("*.json")):
            if fp.name == PAUSED_FILENAME:
                continue
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                meta = payload.get("meta", {})
                if not meta.get("pending_sync"):
                    continue
                pending.append(
                    {
                        "filepath": fp,
                        "name": meta.get("name", fp.stem),
                        "saved_at": meta.get("saved_at", ""),
                        "group_code": meta.get("group_code"),
                        "game": payload.get("game", {}),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return pending

    def mark_synced(self, filepath: Path) -> None:
        """Clear the pending_sync flag on a saved game file."""
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            meta = payload.setdefault("meta", {})
            meta["pending_sync"] = False
            with open(filepath, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def update_pending_group_code(self, filepath: Path, group_code: Optional[str]) -> None:
        """Update the stored group_code on a pending game (useful if assigned later)."""
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            meta = payload.setdefault("meta", {})
            meta["group_code"] = group_code
            with open(filepath, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # --------------------------------------------------------------- plot

    def save_plot(self, fig, filepath: Path) -> None:
        """Export matplotlib figure to image."""
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
