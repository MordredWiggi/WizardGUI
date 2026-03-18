"""
GameControl – Datenmodell für ein Wizard-Spiel.
Enthält: RoundResult, Player, GameControl
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Game modes
# ---------------------------------------------------------------------------

GAME_MODE_STANDARD = "standard"
GAME_MODE_MULTIPLICATIVE = "multiplicative"


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

@dataclass(init=False)
class Player:
    name: str
    avatar: str
    scores: List[int]
    round_results: List[RoundResult]

    def __init__(self, name: str, avatar: str = "🧙‍♂️", initial_score: int = 0) -> None:
        self.name = name
        self.avatar = avatar
        self.scores = [initial_score]
        self.round_results = []

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
        """Number of consecutive rounds with a negative score delta at the end of history."""
        count = 0
        for r in reversed(self.round_results):
            if r.score_delta < 0:
                count += 1
            else:
                break
        return count

    @property
    def revenge_triggered(self) -> bool:
        """True if the player gained points in the last 2 rounds after losing ≥2 rounds in a row before that."""
        if len(self.round_results) < 4:
            return False
        r = self.round_results
        return (
            r[-1].score_delta > 0   # current round: gain
            and r[-2].score_delta > 0   # previous round: gain (2nd consecutive)
            and r[-3].score_delta < 0   # before the gain streak: a loss
            and r[-4].score_delta < 0   # and the round before that also a loss (≥2)
        )

    # --- mutating methods ----------------------------------------------------

    def apply_round(self, result: RoundResult) -> None:
        self.round_results.append(result)
        self.scores.append(self.current_score + result.score_delta)

    def apply_round_multiplicative(self, result: RoundResult) -> None:
        """Apply a round result using multiplicative scoring (new game mode)."""
        self.round_results.append(result)
        current = self.current_score
        if result.said == result.achieved:
            new_score = current * (1 + (result.achieved + 2) / 10)
        else:
            new_score = current * (1 - abs(result.said - result.achieved) / 10)
        self.scores.append(round(new_score))

    def undo_round(self) -> None:
        if self.round_results:
            self.round_results.pop()
            self.scores.pop()

    # --- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "avatar": self.avatar,
            "rounds": [r.to_dict() for r in self.round_results],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        p = cls(name=data["name"], avatar=data.get("avatar", "🧙‍♂️"))
        for rd in data["rounds"]:
            p.apply_round(RoundResult.from_dict(rd))
        return p


# ---------------------------------------------------------------------------
# Game events (returned after each round so the UI can react)
# ---------------------------------------------------------------------------

@dataclass
class RoundEvents:
    new_leader: Optional[Player]           # None → no leadership change
    big_scorer: Optional[Player]           # gained ≥ 50 pts this round
    big_score_delta: int
    fire_player: Optional[Player]          # ≥ 3 consecutive perfect rounds
    negative_player: Optional[Player]      # took the biggest loss this round
    game_over: bool = False                  # True when all rounds are played
    bow_players: List[Player] = field(default_factory=list)      # 3 consecutive losses
    revenge_players: List[Player] = field(default_factory=list)  # 2 gains after ≥2 losses
    huge_loss_player: Optional[Player] = None   # lost ≥ 40 pts this round
    huge_loss_delta: int = 0                    # the actual loss (negative)
    tobi_consolation: bool = False              # Tobi is last/2nd-last after ≥60% of rounds


# ---------------------------------------------------------------------------
# GameControl
# ---------------------------------------------------------------------------

class GameControl:
    """Central model holding the complete state of one game."""

    def __init__(
        self,
        player_data: List[dict],
        initial_dealer_index: Optional[int] = None,
        game_mode: str = GAME_MODE_STANDARD,
    ) -> None:
        self.game_mode = game_mode
        initial_score = 100 if game_mode == GAME_MODE_MULTIPLICATIVE else 0
        self.players: List[Player] = [
            Player(name=p["name"], avatar=p.get("avatar", "🧙‍♂️"), initial_score=initial_score)
            for p in player_data
        ]
        self.round_number: int = 0
        self.initial_dealer_index: int = (
            initial_dealer_index
            if initial_dealer_index is not None
            else random.randrange(len(player_data)) if player_data else 0
        )

    # --- derived properties --------------------------------------------------

    @property
    def num_players(self) -> int:
        return len(self.players)

    @property
    def player_names(self) -> List[str]:
        return [p.name for p in self.players]

    @property
    def total_rounds(self) -> int:
        """Total number of rounds in the game (round 0 doesn't count)."""
        if self.num_players == 0:
            return 0
        return 60 // self.num_players

    @property
    def is_game_over(self) -> bool:
        """True when all rounds have been played."""
        return self.round_number >= self.total_rounds

    @property
    def current_dealer_index(self) -> int:
        """Index of the player who deals in the current (next) round."""
        if not self.players:
            return 0
        return (self.initial_dealer_index + self.round_number) % self.num_players

    @property
    def current_dealer(self) -> Optional[Player]:
        """Player who deals in the current (next) round."""
        if not self.players:
            return None
        return self.players[self.current_dealer_index]

    @property
    def cards_this_round(self) -> int:
        """Number of cards to deal in the current (next) round."""
        return self.round_number + 1

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

    @property
    def leaders(self) -> List[Player]:
        """All players tied for the highest score."""
        if not self.players:
            return []
        max_score = max(p.current_score for p in self.players)
        return [p for p in self.players if p.current_score == max_score]

    def last_deltas(self) -> List[int]:
        if self.round_number == 0:
            return [0] * self.num_players
        return [p.scores[-1] - p.scores[-2] for p in self.players]

    # --- game actions --------------------------------------------------------

    def submit_round(self, results: List[RoundResult]) -> RoundEvents:
        """Apply round results; returns event info so the UI can show effects."""
        old_leader = self.leader

        for player, result in zip(self.players, results):
            if self.game_mode == GAME_MODE_MULTIPLICATIVE:
                player.apply_round_multiplicative(result)
            else:
                player.apply_round(result)
        self.round_number += 1

        new_leader = self.leader
        deltas = self.last_deltas()

        max_delta = max(deltas)
        min_delta = min(deltas)
        max_player = self.players[deltas.index(max_delta)]
        min_player = self.players[deltas.index(min_delta)]

        # Determine the player who lost the most this round (≥40 pts loss)
        huge_loss_player = min_player if min_delta <= -40 else None

        # Tobi consolation: Tobi is last/second-last after ≥60% of rounds
        tobi_consolation = False
        if self.total_rounds > 0 and self.round_number / self.total_rounds >= 0.6:
            tobi_player = next(
                (p for p in self.players if p.name.lower() == "tobi"), None
            )
            if tobi_player is not None:
                sorted_asc = sorted(self.players, key=lambda p: p.current_score)
                rank_from_bottom = sorted_asc.index(tobi_player)
                if rank_from_bottom <= 1:
                    tobi_consolation = True

        return RoundEvents(
            new_leader=new_leader if new_leader is not old_leader else None,
            big_scorer=max_player if max_delta >= 50 else None,
            big_score_delta=max_delta,
            fire_player=next(
                (p for p in self.players if p.consecutive_perfect >= 3), None
            ),
            negative_player=min_player if min_delta < 0 else None,
            game_over=self.is_game_over,
            bow_players=[p for p in self.players if p.consecutive_losses == 3],
            revenge_players=[p for p in self.players if p.revenge_triggered],
            huge_loss_player=huge_loss_player,
            huge_loss_delta=min_delta if huge_loss_player else 0,
            tobi_consolation=tobi_consolation,
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
            "initial_dealer_index": self.initial_dealer_index,
            "game_mode": self.game_mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameControl":
        game_mode = data.get("game_mode", GAME_MODE_STANDARD)
        player_data = [
            {"name": p["name"], "avatar": p.get("avatar", "🧙‍♂️")}
            for p in data["players"]
        ]
        game = cls(
            player_data,
            initial_dealer_index=data.get("initial_dealer_index"),
            game_mode=game_mode,
        )
        # Players are freshly created; rebuild from saved rounds
        for player, pd in zip(game.players, data["players"]):
            for rd in pd["rounds"]:
                result = RoundResult.from_dict(rd)
                if game_mode == GAME_MODE_MULTIPLICATIVE:
                    player.apply_round_multiplicative(result)
                else:
                    player.apply_round(result)
        game.round_number = data["round_number"]
        return game
