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


class SaveManager:
    def __init__(self, save_dir: Path = SAVE_DIR) -> None:
        self.save_dir = save_dir
        self.save_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ save

    def save_game(
        self,
        game_data: dict,
        game_name: Optional[str] = None,
    ) -> Path:
        """Persist game_data as JSON; returns the file path."""
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

    # ----------------------------------------------------------- list games

    def list_saved_games(self) -> List[Dict]:
        """Return metadata for all saved games, newest first."""
        games: List[Dict] = []
        for fp in sorted(self.save_dir.glob("*.json"), reverse=True):
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
                    }
                )
            except (json.JSONDecodeError, KeyError):
                pass
        return games

    # --------------------------------------------------------------- plot

    def save_plot(self, fig, filepath: Path) -> None:
        """Export matplotlib figure to image."""
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
