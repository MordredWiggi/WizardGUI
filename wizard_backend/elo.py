"""
elo.py – Pure ELO rating engine for the Wizard Leaderboard.

This module is intentionally **dependency-free** (only the Python stdlib) and
**database-free**. It contains the single source of truth for how an ELO
change is computed for a finished game. It is imported by:

  - the FastAPI backend (database.py) for live per-game updates on submit, and
  - the desktop Admin Tool (elo_view.py) for the full retroactive recompute.

Keeping the maths in one place guarantees both paths always agree.

Scope model (per the project decision):
  Ratings are tracked **per (player, group, game_mode)**. There is no global
  cross-group pool — players only ever compete inside their own group.

Key properties of the formula:
  - The placement core is *zero-sum* across a table: what the winners gain,
    the losers lose. Pure grinding against equal opponents nets ~0, so the
    rating cannot be inflated just by skill-neutral play.
  - The hit-rate and points-per-round terms are *one-sided bonuses*: every
    player above the table mean gets a positive contribution, every player at
    or below contributes nothing (they are never penalised for these stats).
  - The win-streak bonus is an additive reward, on top of the above.
  - Ratings are clamped to a floor (never below it).

See ELO_SYSTEM.md for the full human-readable explanation.
"""

from __future__ import annotations

from typing import Optional

# ── Default configuration ──────────────────────────────────────────────────
#
# Every value here is overridable via the ``elo_config`` DB row (edited in the
# Admin Tool). The defaults are tuned so that a clean win in a 4-player game is
# worth roughly +100 rating points.

DEFAULT_CONFIG: dict = {
    # Base values
    "start_elo": 1000.0,        # rating assigned to a player's first game
    "floor": 0.0,               # rating can never drop below this
    # Placement core
    "k_base": 115.0,            # base step size (≈ +100 for a 4-player win)
    "d": 400.0,                 # ELO logistic divisor (classic 400)
    "gamma": 0.5,               # player-count weighting of placement (0..1)
    # Hit-rate bonus (one-sided: only above-mean players gain; never penalises)
    "w_hit": 30.0,              # weight of the hit-rate bonus
    "a_hit": 1.0,               # how strongly the bonus is dampened by player count
    "ref_n": 4.0,               # reference player count for the dampening
    # Points-per-round bonus (one-sided: only above-mean players gain)
    "w_ppr": 12.0,              # weight of the points-per-round bonus
    "ppr_scale": 20.0,          # points-per-round span that maps to one unit
    # Win-streak bonus
    "w_streak": 8.0,            # rating per consecutive win beyond the first
    "streak_cap": 5.0,          # streak length at which the bonus stops growing
    # Provisional (reliability) phase
    "provisional_games": 5,     # games before a rating is considered settled
    "provisional_mult": 1.5,    # K multiplier while a player is still provisional
}

# Numeric parameters that must always be present and finite. Used by the Admin
# Tool to render the editing form in a stable order.
CONFIG_FIELDS: list[tuple[str, str]] = [
    ("start_elo", "Starting rating for a brand-new player."),
    ("floor", "Lower bound — a rating can never fall below this."),
    ("k_base", "Base step size. Higher = bigger swings (≈+100 for a 4p win)."),
    ("d", "ELO logistic divisor. 400 is the classic chess value."),
    ("gamma", "Player-count weight of placement (0 = ignore count, 1 = full)."),
    ("w_hit", "Weight of the hit-rate bonus (deviation from the table mean)."),
    ("a_hit", "How strongly the hit-rate bonus shrinks with more players."),
    ("ref_n", "Reference player count for the hit-rate dampening."),
    ("w_ppr", "Weight of the points-per-round bonus."),
    ("ppr_scale", "Points-per-round difference that equals one bonus unit."),
    ("w_streak", "Rating awarded per consecutive win beyond the first."),
    ("streak_cap", "Streak length at which the streak bonus stops growing."),
    ("provisional_games", "Games played before a rating is treated as settled."),
    ("provisional_mult", "K multiplier applied while a player is provisional."),
]


def normalize_config(raw: Optional[dict]) -> dict:
    """Return a complete config dict: defaults overlaid with any valid ``raw``
    values. Unknown keys are ignored; ``None`` values fall back to the default.
    """
    cfg = dict(DEFAULT_CONFIG)
    if raw:
        for key, value in raw.items():
            if key in cfg and value is not None:
                try:
                    cfg[key] = float(value)
                except (TypeError, ValueError):
                    pass  # keep the default for unparseable values
    # A couple of values are conceptually integers.
    cfg["provisional_games"] = int(cfg["provisional_games"])
    return cfg


# ── Core maths ──────────────────────────────────────────────────────────────


def _expected(rating_i: float, rating_j: float, d: float) -> float:
    """Probability that player i finishes above player j (logistic ELO)."""
    return 1.0 / (1.0 + 10.0 ** ((rating_j - rating_i) / d))


def compute_game_deltas(players: list[dict], config: dict) -> list[dict]:
    """Compute the rating change for every player of a single finished game.

    ``players`` is a list of dicts (order is preserved in the output). Each entry
    holds the player's per-game result **and** their rating state *before* this
    game::

        {
            "player_id":    int,
            "rank":         int,    # 1 = best; ties share a rank
            "correct_bids": int,
            "total_rounds": int,
            "final_score":  number,
            "rating":       float,  # rating BEFORE this game
            "games":        int,    # games played BEFORE this game (in this pool)
            "streak":       int,    # current win streak BEFORE this game
        }

    Returns a list of dicts (same order)::

        {
            "player_id", "rating_before", "delta",
            "rating_after", "games_after", "streak_after",
        }
    """
    n = len(players)
    if n == 0:
        return []

    cfg = config

    # A solo "game" has no opponents: rating is unchanged, but we still advance
    # the games counter and the streak so the bookkeeping stays consistent.
    if n == 1:
        p = players[0]
        won = p["rank"] == 1
        return [
            {
                "player_id": p["player_id"],
                "rating_before": float(p["rating"]),
                "delta": 0.0,
                "rating_after": float(p["rating"]),
                "games_after": int(p["games"]) + 1,
                "streak_after": (int(p["streak"]) + 1) if won else 0,
            }
        ]

    d = cfg["d"]
    floor = cfg["floor"]

    # Per-game derived stats and their table means (used by the one-sided
    # hit-rate and points-per-round bonuses below).
    hit_rates: list[float] = []
    pprs: list[float] = []
    for p in players:
        rounds = p["total_rounds"] or 1
        hit_rates.append(p["correct_bids"] / rounds)
        pprs.append(p["final_score"] / rounds)
    mean_hr = sum(hit_rates) / n
    mean_ppr = sum(pprs) / n

    # Player-count modifier for the placement core: (n-1)^(gamma-1).
    #   gamma = 1 -> 1            (raw pairwise sum: big games swing hard)
    #   gamma = 0 -> 1/(n-1)      (fully normalised: player count irrelevant)
    m_n = (n - 1) ** (cfg["gamma"] - 1.0)

    # Hit-rate dampening: more players -> hit rate matters less.
    hit_damp = (cfg["ref_n"] / n) ** cfg["a_hit"]

    results: list[dict] = []
    for idx, p in enumerate(players):
        rating_i = float(p["rating"])

        # (a) Placement core — sum of (actual − expected) over every opponent.
        core = 0.0
        for jdx, q in enumerate(players):
            if jdx == idx:
                continue
            expected = _expected(rating_i, float(q["rating"]), d)
            if p["rank"] < q["rank"]:
                actual = 1.0
            elif p["rank"] == q["rank"]:
                actual = 0.5
            else:
                actual = 0.0
            core += actual - expected

        # (f) Reliability: provisional players move faster.
        k_i = cfg["k_base"] * (
            cfg["provisional_mult"]
            if int(p["games"]) < cfg["provisional_games"]
            else 1.0
        )
        placement = k_i * core * m_n

        # (c) Hit-rate bonus — one-sided: only players ABOVE the table mean
        # gain. Below-mean players contribute nothing (no penalty).
        hit_excess = hit_rates[idx] - mean_hr
        hit_term = max(0.0, hit_excess) * cfg["w_hit"] * hit_damp

        # (d) Points-per-round bonus — one-sided around the table mean.
        ppr_excess = (pprs[idx] - mean_ppr) / cfg["ppr_scale"]
        ppr_term = max(0.0, ppr_excess) * cfg["w_ppr"]

        # (e) Win-streak bonus — only for winners, only the inflationary term.
        won = p["rank"] == 1
        streak_after = (int(p["streak"]) + 1) if won else 0
        if won:
            steps = min(max(streak_after - 1, 0), cfg["streak_cap"])
            streak_term = cfg["w_streak"] * steps
        else:
            streak_term = 0.0

        delta = placement + hit_term + ppr_term + streak_term
        rating_after = rating_i + delta
        if rating_after < floor:
            rating_after = floor
            delta = rating_after - rating_i  # honour the floor in the reported delta

        results.append(
            {
                "player_id": p["player_id"],
                "rating_before": rating_i,
                "delta": delta,
                "rating_after": rating_after,
                "games_after": int(p["games"]) + 1,
                "streak_after": streak_after,
            }
        )
    return results


def replay_pool(games_sorted: list[dict], config: dict) -> tuple[dict, list[dict]]:
    """Replay every game in a single pool (one group + one mode), in order.

    ``games_sorted`` must already be sorted chronologically (played_at, then id).
    Each game is::

        {"game_id": int, "players": [ {player_id, rank, correct_bids,
                                       total_rounds, final_score}, ... ]}

    Returns ``(ratings, deltas)`` where:
      - ``ratings`` maps player_id -> {"rating", "games", "streak"} (final state)
      - ``deltas``  is a flat list of per-game, per-player change records:
            {"game_id", "player_id", "rating_before", "rating_after", "delta"}
    """
    cfg = config
    ratings: dict[int, dict] = {}
    deltas: list[dict] = []

    for game in games_sorted:
        players: list[dict] = []
        for pr in game["players"]:
            pid = pr["player_id"]
            state = ratings.get(pid)
            if state is None:
                state = {"rating": cfg["start_elo"], "games": 0, "streak": 0}
            players.append(
                {
                    "player_id": pid,
                    "rank": pr["rank"],
                    "correct_bids": pr["correct_bids"],
                    "total_rounds": pr["total_rounds"],
                    "final_score": pr["final_score"],
                    "rating": state["rating"],
                    "games": state["games"],
                    "streak": state["streak"],
                }
            )

        for r in compute_game_deltas(players, cfg):
            ratings[r["player_id"]] = {
                "rating": r["rating_after"],
                "games": r["games_after"],
                "streak": r["streak_after"],
            }
            deltas.append(
                {
                    "game_id": game["game_id"],
                    "player_id": r["player_id"],
                    "rating_before": r["rating_before"],
                    "rating_after": r["rating_after"],
                    "delta": r["delta"],
                }
            )

    return ratings, deltas
