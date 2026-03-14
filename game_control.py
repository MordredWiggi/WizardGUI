"""
GameControl – Datenmodell für ein Wizard-Spiel.
Enthält: RoundResult, Player, GameControl
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass
class RoundResult:
    said: int
    achieved: int

    @property
    def score_delta(self) -> int:
        if self.said == self.achieved:
            return 20 + self.said * 10
        return -10 * abs(self.said - self.achieved)

    @property
    def is_perfect(self) -> bool:
        return self.said == self.achieved

    def to_dict(self) -> dict:
        return {"said": self.said, "achieved": self.achieved}

    @staticmethod
    def from_dict(d: dict) -> "RoundResult":
        return RoundResult(said=d["said"], achieved=d["achieved"])


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

@dataclass
class Player:
    name: str
    scores: List[int] = field(default_factory=lambda: [0])
    round_results: List[RoundResult] = field(default_factory=list)

    # --- computed properties -------------------------------------------------

    @property
    def current_score(self) -> int:
        return self.scores[-1]

    @property
    def consecutive_perfect(self) -> int:
        """Number of consecutive perfect rounds at the end of history."""
        count = 0
        for r in reversed(self.round_results):
            if r.is_perfect:
                count += 1
            else:
                break
        return count

    @property
    def consecutive_losses(self) -> int:
        """Number of consecutive rounds with negative score_delta at end of history."""
        count = 0
        for r in reversed(self.round_results):
            if r.score_delta < 0:
                count += 1
            else:
                break
        return count

    @property
    def is_revenge(self) -> bool:
        """True if player gained points exactly 2 rounds in a row after 2+ consecutive losses.

        Triggers exactly when the gain streak reaches 2 (the 3rd-to-last round was
        not a gain) and those gains immediately followed a streak of ≥ 2 losses.
        """
        rr = self.round_results
        if len(rr) < 4:
            return False
        # Last 2 rounds must be gains
        if rr[-1].score_delta <= 0 or rr[-2].score_delta <= 0:
            return False
        # Gain streak must be exactly 2 – the round before was not a gain
        if rr[-3].score_delta > 0:
            return False
        # Count consecutive losses that end at rr[-3]
        loss_count = 0
        for r in reversed(rr[:-2]):
            if r.score_delta < 0:
                loss_count += 1
            else:
                break
        return loss_count >= 2

    # --- mutating methods ----------------------------------------------------

    def apply_round(self, result: RoundResult) -> None:
        self.round_results.append(result)
        self.scores.append(self.current_score + result.score_delta)

    def undo_round(self) -> None:
        if self.round_results:
            self.round_results.pop()
            self.scores.pop()

    # --- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rounds": [r.to_dict() for r in self.round_results],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        p = cls(name=data["name"])
        for rd in data["rounds"]:
            p.apply_round(RoundResult.from_dict(rd))
        return p


# ---------------------------------------------------------------------------
# Game events (returned after each round so the UI can react)
# ---------------------------------------------------------------------------

@dataclass
class RoundEvents:
    new_leader: Optional[Player]       # None → no leadership change
    big_scorer: Optional[Player]       # gained ≥ 50 pts this round
    big_score_delta: int
    fire_player: Optional[Player]      # ≥ 3 consecutive perfect rounds
    negative_player: Optional[Player]  # took the biggest loss this round
    bow_player: Optional[Player]       # lost points exactly 3 rounds in a row
    revenge_player: Optional[Player]   # gained 2 rounds in a row after 2+ losses
    huge_loss_player: Optional[Player] # lost ≥ 40 points in a single round
    huge_loss_delta: int               # magnitude of the huge loss (positive number)


# ---------------------------------------------------------------------------
# GameControl
# ---------------------------------------------------------------------------

class GameControl:
    """Central model holding the complete state of one game."""

    def __init__(self, player_names: List[str]) -> None:
        self.players: List[Player] = [Player(name=n) for n in player_names]
        self.round_number: int = 0

    # --- derived properties --------------------------------------------------

    @property
    def num_players(self) -> int:
        return len(self.players)

    @property
    def max_rounds(self) -> int:
        """Maximum number of rounds for this game (round 0 doesn't count)."""
        return 60 // self.num_players

    @property
    def is_game_over(self) -> bool:
        """True once the maximum number of rounds has been played."""
        return self.round_number >= self.max_rounds

    @property
    def player_names(self) -> List[str]:
        return [p.name for p in self.players]

    @property
    def round_indices(self) -> List[int]:
        return list(range(self.round_number + 1))

    @property
    def all_scores(self) -> List[List[int]]:
        return [p.scores for p in self.players]

    @property
    def averages(self) -> List[float]:
        return [
            sum(p.scores[r] for p in self.players) / self.num_players
            for r in range(self.round_number + 1)
        ]

    @property
    def leader(self) -> Optional[Player]:
        if not self.players:
            return None
        return max(self.players, key=lambda p: p.current_score)

    def last_deltas(self) -> List[int]:
        if self.round_number == 0:
            return [0] * self.num_players
        return [p.scores[-1] - p.scores[-2] for p in self.players]

    # --- game actions --------------------------------------------------------

    def submit_round(self, results: List[RoundResult]) -> RoundEvents:
        """Apply round results; returns event info so the UI can show effects."""
        old_leader = self.leader

        for player, result in zip(self.players, results):
            player.apply_round(result)
        self.round_number += 1

        new_leader = self.leader
        deltas = self.last_deltas()

        max_delta = max(deltas)
        min_delta = min(deltas)
        max_player = self.players[deltas.index(max_delta)]
        min_player = self.players[deltas.index(min_delta)]

        # Huge loss: any player who lost ≥ 40 points this round
        huge_loss_player: Optional[Player] = None
        huge_loss_delta: int = 0
        for player, delta in zip(self.players, deltas):
            if delta <= -40 and delta < huge_loss_delta:
                huge_loss_delta = delta
                huge_loss_player = player
        if huge_loss_player is None and min_delta <= -40:
            huge_loss_player = min_player
            huge_loss_delta = min_delta

        return RoundEvents(
            new_leader=new_leader if new_leader is not old_leader else None,
            big_scorer=max_player if max_delta >= 50 else None,
            big_score_delta=max_delta,
            fire_player=next(
                (p for p in self.players if p.consecutive_perfect >= 3), None
            ),
            negative_player=min_player if min_delta < 0 else None,
            bow_player=next(
                (p for p in self.players if p.consecutive_losses == 3), None
            ),
            revenge_player=next(
                (p for p in self.players if p.is_revenge), None
            ),
            huge_loss_player=huge_loss_player,
            huge_loss_delta=abs(huge_loss_delta),
        )

    def undo_round(self) -> bool:
        if self.round_number > 0:
            for player in self.players:
                player.undo_round()
            self.round_number -= 1
            return True
        return False

    # --- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "players": [p.to_dict() for p in self.players],
            "round_number": self.round_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameControl":
        player_names = [p["name"] for p in data["players"]]
        game = cls(player_names)
        # Players are freshly created; rebuild from saved rounds
        for player, pd in zip(game.players, data["players"]):
            for rd in pd["rounds"]:
                player.apply_round(RoundResult.from_dict(rd))
        game.round_number = data["round_number"]
        return game
