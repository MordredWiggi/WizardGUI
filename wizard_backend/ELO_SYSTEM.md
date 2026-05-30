# Wizard ELO System

This document explains the Wizard leaderboard's ELO rating system **in
detail**: the formula, each individual factor, the default parameters, and the
end-to-end technical implementation. It is the reference for anyone who wants
to understand or tune the calculation.

> All the maths lives in **one single place**: the module
> [`elo.py`](elo.py). The live server (on every submitted game) **and** the
> Admin Tool (when doing a full recompute) both call into the same functions —
> the two paths can never diverge.

---

## 1. Core idea & scope

- **ELO is the headline statistic** for a player. Every other value (average
  score, hit rate, highscore, win streak) is "just for fun".
- **ELO is always group-internal.** There is **no** cross-group / global pool;
  players only ever compete against the rest of their own group.
- **ELO is tracked separately per game mode** (`standard` vs `multiplicative`).

A rating is therefore keyed by the triple **(player, group, game_mode)**.
Games without a group (`group_id = NULL`) get no ELO at all (the app does not
upload those anyway — they are only saved locally).

### Key properties

| Property | How it is achieved |
|---|---|
| Win ≈ **+100** (with 4 players) | `k_base` tuned accordingly |
| Beating stronger opponents pays more | Pairwise ELO expectation `E_ij` |
| More players → 2nd / 3rd place worth more | Sum over all duels + `gamma` scaling |
| You can **lose** ELO | Placement core is **zero-sum** |
| No "farming" by playing a lot | Zero-sum core: against equal opponents ≈ 0 |
| Hit-rate / points are one-sided **bonuses** | Above-mean players gain; nobody is penalised |
| New players settle quickly | Provisional phase with higher K |
| Never below 0 | Lower clamp `floor` |

---

## 2. The formula

For **one finished game** with `n` players, every player `i` receives a rating
change `Δ_i`. All quantities are scoped to the game's pool (group + mode).

```
Δ_i = K_i · Core_i · M(n)   +   Hit_i   +   Ppr_i   +   Streak_i
R_i' = max(floor, R_i + Δ_i)
```

The four summands in detail:

### (a) Placement core `Core_i` — the heart of the system

Every player faces **every** other player `j` in a pairwise duel:

```
E_ij = 1 / (1 + 10^((R_j − R_i) / d))      ← expected probability that i
                                              finishes above j
S_ij = 1.0   if rank_i < rank_j   (i beat j)
       0.5   if rank_i = rank_j   (tie)
       0.0   if rank_i > rank_j   (i lost to j)

Core_i = Σ_{j≠i} (S_ij − E_ij)
```

- Beating a **higher-rated** player (small `E_ij`) earns close to the full
  point → bigger reward.
- **Important:** `Σ_i Core_i = 0` exactly — across the whole table the core
  sums to zero. What the winners gain, the losers lose. This is the
  structural anti-inflation guarantee: playing average against equal opponents
  nets ≈ 0, no matter how often.

### (b) Player-count modifier `M(n)`

```
M(n) = (n − 1)^(gamma − 1)
```

| `gamma` | Effect |
|---|---|
| `1.0` | `M(n) = 1` → raw sum effect: big games swing hard |
| `0.0` | `M(n) = 1/(n−1)` → fully normalised: player count irrelevant |
| `0.5` (default) | Swing grows ~ √player count |

At `gamma = 0.5` a win in a 6-player game is worth more than a win in a
3-player game, and finishing 2nd of 6 is clearly positive while 2nd of 3 is
≈ neutral. This matches the intended behaviour.

### (c) Hit-rate bonus `Hit_i` (one-sided, dampened by player count)

```
hr_i  = correct_bids_i / total_rounds_i
Hit_i = max(0, hr_i − Ø hr at the table) · w_hit · (ref_n / n)^a_hit
```

- **One-sided**: only players **above** the table mean receive a positive
  bonus; at-or-below-mean players contribute exactly **0** (they are never
  penalised for these stats).
- `(ref_n / n)^a_hit` dampens the bonus as the player count grows — hit rate
  becomes less important the more players are at the table.

### (d) Points-per-round bonus `Ppr_i` (one-sided, self-normalising)

```
ppr_i = final_score_i / total_rounds_i
Ppr_i = max(0, (ppr_i − Ø ppr at the table) / ppr_scale) · w_ppr
```

- In Standard mode, `final_score` is exactly the trick reward (a correct bid
  of `k` tricks = `20 + 10·k`), so "points per round" is the correct proxy
  for "tricks per round".
- Comparing **inside the same game** automatically neutralises the
  player-count effect: everyone at the table played under the same conditions.
- Same as hit rate: only above-mean players gain, no one is ever penalised.
- `ppr_scale` is the points-per-round difference that corresponds to one
  bonus unit.

### (e) Win-streak bonus `Streak_i`

```
streak_i' = streak_i + 1            (on a win, rank_i = 1)
Streak_i  = w_streak · min(max(streak_i' − 1, 0), streak_cap)   only for winners
```

- Kicks in from the **second consecutive win** (the first win still earns no
  streak bonus), grows up to `streak_cap`, then stops.

### (f) Reliability K `K_i`

```
K_i = k_base · (provisional_mult   if games_i < provisional_games
                1.0                otherwise)
```

New players (`games_i < provisional_games`) move faster with a larger K, so
their rating finds its true level quickly; afterwards it stabilises.

### Lower clamp

`R_i'` is clamped to `floor` (default 0). When the clamp triggers, the
reported `Δ_i` is shortened accordingly so the displayed delta and the new
rating always match.

> **Note on inflation.** The placement core (a) is exactly zero-sum across the
> table. The hit-rate bonus (c), the points-per-round bonus (d), and the
> streak bonus (e) are all **additive injections** into the pool. So the
> overall pool will slowly drift upward over time when there are above-mean
> performances or win streaks — by design: the player who actually performed
> above the table is rewarded, and below-mean players don't have to "pay" for
> it. The placement core remains the dominant term, so ranks across the group
> still order players correctly.

---

## 3. Default parameters

Every value is editable in the **Admin Tool → ELO tab** and persisted as a
JSON blob in the `elo_config` table.

| Parameter | Default | Meaning |
|---|---:|---|
| `start_elo` | 1000 | Starting rating for a brand-new player |
| `floor` | 0 | Rating can never fall below this |
| `k_base` | 115 | Base step size (≈ +100 for a 4-player win) |
| `d` | 400 | ELO logistic divisor (classic) |
| `gamma` | 0.5 | Player-count weight of placement |
| `w_hit` | 30 | Weight of the hit-rate bonus |
| `a_hit` | 1.0 | How strongly the hit-rate bonus shrinks with more players |
| `ref_n` | 4 | Reference player count for the dampening |
| `w_ppr` | 12 | Weight of the points-per-round bonus |
| `ppr_scale` | 20 | Points-per-round difference equal to one bonus unit |
| `w_streak` | 8 | ELO awarded per consecutive win (from the 2nd onwards) |
| `streak_cap` | 5 | Streak length at which the bonus stops growing |
| `provisional_games` | 5 | Games until a rating is considered settled |
| `provisional_mult` | 1.5 | K multiplier during the provisional phase |

### Sample magnitudes (4 equal settled players, defaults)

With `gamma = 0.5`, `k_base = 115`: `M(4) = 3^(−0.5) ≈ 0.577`.

- **Winner** (beats 3 opponents): `Core = 3·0.5 = 1.5` → `115 · 1.5 · 0.577 ≈ +100`
  plus the (always non-negative) hit/ppr/streak bonuses.
- **Last place**: pure placement only (no bonus, no penalty) ≈ **−100**.
- In **6-player** games the placement swings are larger (~ +130 for 1st);
  in **3-player** games smaller (~ +81).

---

## 4. Technical implementation

### 4.1 Database schema (new tables)

Created idempotently inside [`database.py → init_db()`](database.py):

```sql
-- Single editable configuration row (id is always 1)
CREATE TABLE elo_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    params TEXT NOT NULL,            -- JSON of all parameters
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

-- Current rating per (player, group, mode). No global pool.
CREATE TABLE player_ratings (
    player_id INTEGER NOT NULL REFERENCES players(id),
    group_id  INTEGER NOT NULL REFERENCES groups(id),
    game_mode TEXT NOT NULL,
    rating REAL NOT NULL,
    games INTEGER NOT NULL DEFAULT 0,
    streak INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (player_id, group_id, game_mode)
);

-- Per-game, per-player rating change (audit trail + app display)
CREATE TABLE game_elo_deltas (
    game_id INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    rating_before REAL NOT NULL,
    rating_after  REAL NOT NULL,
    delta REAL NOT NULL,
    PRIMARY KEY (game_id, player_id)
);
```

On first start, `elo_config` is seeded with the defaults from
`elo.DEFAULT_CONFIG`. Existing data is preserved.

### 4.2 Live calculation on game submission

In [`database.py → submit_game()`](database.py):

1. The game + its results are inserted.
2. If the game has a group, the **entire pool is recomputed**
   (`_recompute_pool`): every game of this (group, mode) is replayed in
   chronological order (`played_at`, then `id`); `player_ratings` and
   `game_elo_deltas` for the pool are rewritten.
3. The deltas for this game are returned in the API response.

> **Why recompute the whole pool on every submit instead of an incremental
> update?** It keeps ratings exact even when a game arrives out of
> chronological order (e.g. a "pending-sync" game that was queued offline and
> uploaded days later). Pools are small (one group, one mode) so this is
> cheap. Everything runs inside one transaction → atomic.

Response shape of `POST /api/games`:

```json
{
  "status": "created",
  "elo": [
    {"name": "Alice", "delta": 102.3, "rating": 1102, "rank": 1},
    {"name": "Bob",   "delta": -40.1, "rating":  960, "rank": 2}
  ]
}
```

`elo` is also filled when `"status": "duplicate"` (stored deltas) and empty
for games without a group.

### 4.3 Leaderboards

[`get_group_player_leaderboard()`](database.py) `LEFT JOIN`s
`player_ratings` and adds an `elo` field (rounded). The global leaderboards
(`/api/leaderboard`, `/api/leaderboard/groups`) deliberately have **no** ELO,
because ELO is only defined inside a single group.

**Per-player ELO history (website).** The public group leaderboard page
([`templates/group_leaderboard.html`](templates/group_leaderboard.html)) lets a
visitor click any player row to open an ELO-history modal — the read-only,
public counterpart of the Admin Tool dialog described in §4.6. It is backed by

```
GET /api/leaderboard/group/{code}/player/elo?name=<player>&mode=<standard|multiplicative>
```

→ [`get_player_elo_history()`](database.py), which returns the player's current
rating snapshot (`rating`, `games`, `streak`) plus one entry per rated game
(`played_at`, `rank`, `rating_before`, `delta`, `rating_after`), ordered
newest-first, read from `player_ratings` and `game_elo_deltas`. The endpoint is purely
read-only — it never writes ratings. Like every other group endpoint it
requires the group's 4-digit `code`, and the player `name` travels in the query
string so names with URL-significant characters are handled cleanly.

### 4.4 In-app display

- **Leaderboard:** In the per-group leaderboard (Flutter and Desktop), **ELO**
  is the first, most prominent stat column and the default sort key
  (descending).
- **End of game:** The podium shows a coloured `ELO +12` / `ELO −8` badge
  next to each player. The deltas come from the submit response.

### 4.5 Tuning the formula (Admin Tool)

The **ELO** tab ([`admin_tool/elo_view.py`](admin_tool/elo_view.py)) offers:

- A **form** with every parameter (each with an inline explanation).
- **Save configuration** → writes the row in `elo_config`. Applies **only to
  future games** — existing ratings are left alone. Players keep their level
  and start using the adjusted values from their next game onwards.
- **Recompute ALL ratings from scratch** → replays **every** game of **every**
  group with the saved formula. Intended for the **very first introduction**
  of the ELO system (or a deliberate reset).

The recompute runs locally in the Admin Tool (which imports the same
`elo.py`) and writes the result back as **one batched SQL script** — this
works against the local SQLite file just as well as against the remote
production DB over SSH, without needing any extra HTTP endpoint.

### 4.6 Inspecting ratings (Admin Tool)

Beyond the ELO tab, ratings are surfaced wherever they are relevant:

- **Group → Players tab**: each row shows the player's current
  `ELO (Std)` and `ELO (Mult)` next to the regular stats.
- **Group → Games tab**: the per-game **results panel** has an `ELO Δ`
  column showing exactly how much each player's rating moved on that game
  (joined from `game_elo_deltas`).
- **Per-player ELO history**: select a player in the Players tab and click
  **📈 ELO history** (or double-click the row) to open a timeline of that
  player's rating in the group (newest game first): played-at, rank, ELO
  before, signed delta, ELO after — switchable between Standard and
  Multiplicative.

All these views call the shared `ensure_elo_schema()` helper before they
join the ELO tables, so the admin tool also works against a DB that
pre-dates the ELO release.

---

## 5. First-time rollout

1. Roll out the backend code (with `elo.py` and the schema migrations) to the
   VM and restart the service. The new tables are created automatically at
   startup; `elo_config` is seeded with the defaults. **No existing data is
   modified.**
2. Open the Admin Tool → **ELO** tab → (optionally adjust parameters →)
   **Save configuration**.
3. Click **Recompute ALL ratings from scratch** → all historical games are
   replayed; every player gets an ELO in every group they have played in.
4. Rebuild and release the apps so the ELO column and end-of-game badge go
   live.
5. Done. From here on every submitted game updates its pool automatically.

> Later changes to the formula need **no** recompute — just click *Save*, and
> all future games will use the updated formula. (Recompute is only needed
> when you want to re-evaluate the whole history.)
